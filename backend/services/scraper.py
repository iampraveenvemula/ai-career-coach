"""
Job scraper service that fetches real listings from external sources
and normalizes them for ingestion into the local DB + vector store.
Uses LLM to intelligently parse search queries into core keywords and location.
Uses direct ATS searches on Google, and fails over to Mojeek Search (which has
zero bot CAPTCHA blocks) to guarantee individual direct job postings are retrieved.
Resolves full job descriptions from target ATS pages.
"""

import httpx
import uuid
import re
import os
import json
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from urllib.parse import urlparse, parse_qs

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

QUERY_PARSE_PROMPT = """You are a search query parsing agent. Given a user's job search query, extract the target job title/keywords and the target geographic location (city, country, region, or 'remote').
Return ONLY a valid JSON object. Do not include markdown fences (```), commentary, or extra text.

Return exactly this JSON schema:
{
  "keywords": "<core job role, title, or skills, e.g. 'AI Engineer'>",
  "location": "<target location, e.g. 'United Arab Emirates' or 'Dubai' or 'Remote'. If none specified, return ''>"
}

Examples:
Query: "ai engineer in uae" -> {"keywords": "ai engineer", "location": "uae"}
Query: "senior python developer looking for dubai work" -> {"keywords": "senior python developer", "location": "dubai"}
Query: "data science positions near london" -> {"keywords": "data science", "location": "london"}
Query: "ml engineering remote" -> {"keywords": "ml engineering", "location": "remote"}
"""


def parse_relative_time(time_str: str) -> datetime:
    """
    Parses absolute or relative job posting dates into a datetime object.
    Supports formats like: '2026-06-28', '2 hours ago', '3 days ago', '1 week ago'.
    """
    now = datetime.utcnow()
    val_str = time_str.lower().strip()
    try:
        # Absolute ISO format e.g. "2026-06-29"
        if re.match(r"^\d{4}-\d{2}-\d{2}$", val_str):
            return datetime.strptime(val_str, "%Y-%m-%d")
        
        # Relative strings
        match = re.search(r"(\d+)\s+(hour|day|week|month|year)", val_str)
        if match:
            val = int(match.group(1))
            unit = match.group(2)
            if "hour" in unit:
                return now - timedelta(hours=val)
            elif "day" in unit:
                return now - timedelta(days=val)
            elif "week" in unit:
                return now - timedelta(weeks=val)
            elif "month" in unit:
                return now - timedelta(days=val * 30)
            elif "year" in unit:
                return now - timedelta(days=val * 365)
    except Exception:
        pass
    return now


def extract_company_and_title(title: str, url: str) -> tuple[str, str]:
    """
    Parses clean company name and job title from ATS urls and title tags.
    """
    company = "Unknown"
    parsed = urlparse(url)
    netloc = parsed.netloc.lower()
    path_parts = [p for p in parsed.path.split("/") if p]
    
    if "lever.co" in netloc and len(path_parts) >= 1:
        company = path_parts[0]
    elif "greenhouse.io" in netloc and len(path_parts) >= 1:
        company = path_parts[0]
    elif "workable.com" in netloc and len(path_parts) >= 1:
        company = path_parts[0]
    elif "ashby.co" in netloc and len(path_parts) >= 1:
        company = path_parts[0]
        
    company = company.replace("-", " ").title()
    
    clean_title = title
    for prefix in ["Job Application for ", "Job Application - ", "Job Application: ", "Jobs at ", "Hiring: "]:
        if clean_title.lower().startswith(prefix.lower()):
            clean_title = clean_title[len(prefix):]
            
    if " at " in clean_title:
        parts = clean_title.split(" at ")
        clean_title = parts[0]
        company = parts[1]
            
    return company.strip(), clean_title.strip()


async def fetch_ats_job_description(url: str, default_desc: str = "") -> str:
    """
    Fetches the actual job description text directly from Greenhouse, Lever, Workable, etc.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                
                # Check for standard ATS layout tags
                main_content = None
                if "lever.co" in url:
                    main_content = soup.find("div", class_="section-wrapper") or soup.find("div", class_="content")
                elif "greenhouse.io" in url:
                    main_content = soup.find("div", id="main") or soup.find("div", id="content")
                elif "workable.com" in url:
                    main_content = soup.find("main") or soup.find("div", class_="job-section")
                
                target = main_content if main_content else soup.body
                
                if target:
                    # Clean tags
                    for el in target(["script", "style", "nav", "footer", "header"]):
                        el.decompose()
                    
                    text = target.get_text(separator=" ")
                    lines = (line.strip() for line in text.splitlines())
                    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                    clean_text = "\n".join(chunk for chunk in chunks if chunk)
                    
                    # Remove excessive headers/footers
                    clean_text = re.sub(r"\n{3,}", "\n\n", clean_text)
                    if len(clean_text) > 100:
                        return clean_text[:4000]
    except Exception as e:
        print(f"[ATS Scraper] Failed to fetch full description from {url}: {e}")
    return default_desc


async def scrape_remotive(query: str, location: str = "", limit: int = 30) -> list[dict]:
    """
    Fetches jobs from the Remotive API (free, no auth required).
    Great for remote AI/ML/engineering roles.
    """
    search_term = query
    if location:
        search_term = f"{query} {location}".strip()
        
    url = "https://remotive.com/api/remote-jobs"
    params = {"search": search_term, "limit": limit}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        jobs = []
        for item in data.get("jobs", [])[:limit]:
            # Clean HTML from description
            desc_html = item.get("description", "")
            desc_text = BeautifulSoup(desc_html, "html.parser").get_text(separator=" ", strip=True)
            # Truncate for storage
            desc_text = desc_text[:1000]

            salary = item.get("salary", "")
            if not salary:
                salary = "Not disclosed"

            loc = item.get("candidate_required_location", "Remote")
            if location and location.lower() not in loc.lower() and loc.lower() != "worldwide":
                # Skip if it doesn't match location criteria
                continue

            # Parse posted_at date
            pub_date_str = item.get("publication_date", "")
            posted_time = datetime.utcnow()
            if pub_date_str:
                try:
                    posted_time = datetime.fromisoformat(pub_date_str.replace("Z", "+00:00"))
                except Exception:
                    pass

            jobs.append({
                "id": str(uuid.uuid4()),
                "title": item.get("title", "Unknown"),
                "company": item.get("company_name", "Unknown"),
                "location": loc,
                "description_text": desc_text,
                "url": item.get("url", ""),
                "salary_range": salary,
                "source": "Remotive",
                "posted_at": posted_time
            })
        return jobs
    except Exception as e:
        print(f"[Remotive] Scrape failed: {e}")
        return []


async def scrape_linkedin_guest(query: str, location: str = "", limit: int = 40) -> list[dict]:
    """
    Fetches jobs from LinkedIn's public guest job search page.
    Utilizes concurrent page queries to paginate and maximize search results.
    """
    # LinkedIn returns up to 25 items per page. Calculate number of pages needed.
    pages = (limit + 24) // 25
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    async def fetch_page(page_idx: int) -> list[dict]:
        start = page_idx * 25
        url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
        params = {"keywords": query, "location": location or "", "start": start}
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                resp = await client.get(url, params=params, headers=headers)
                if resp.status_code != 200:
                    return []
            
            soup = BeautifulSoup(resp.text, "html.parser")
            cards = soup.find_all("div", class_="base-card")
            
            page_jobs = []
            for card in cards:
                title_el = card.find("h3", class_="base-search-card__title")
                company_el = card.find("h4", class_="base-search-card__subtitle")
                location_el = card.find("span", class_="job-search-card__location")
                link_el = card.find("a", class_="base-card__full-link")
                time_el = card.find("time")
                
                title = title_el.get_text(strip=True) if title_el else "Unknown"
                company = company_el.get_text(strip=True) if company_el else "Unknown"
                loc = location_el.get_text(strip=True) if location_el else (location or "Unknown")
                job_url = link_el["href"] if link_el and link_el.get("href") else ""
                
                # Parse posted date
                posted_time = datetime.utcnow()
                if time_el:
                    dt_attr = time_el.get("datetime")
                    if dt_attr:
                        posted_time = parse_relative_time(dt_attr)
                    else:
                        posted_time = parse_relative_time(time_el.text)
                
                desc = f"{title} at {company}. Location: {loc}."
                
                page_jobs.append({
                    "id": str(uuid.uuid4()),
                    "title": title,
                    "company": company,
                    "location": loc,
                    "description_text": desc,
                    "url": job_url.split("?")[0] if job_url else "",
                    "salary_range": "Not disclosed",
                    "source": "LinkedIn",
                    "posted_at": posted_time
                })
            return page_jobs
        except Exception as e:
            print(f"[LinkedIn Page {page_idx}] Fetch failed: {e}")
            return []

    import asyncio
    tasks = [fetch_page(i) for i in range(pages)]
    page_results = await asyncio.gather(*tasks)
    
    jobs = []
    for r in page_results:
        jobs.extend(r)
        
    return jobs[:limit]


async def scrape_google_jobs(query: str, location: str = "", limit: int = 30) -> list[dict]:
    """
    Scrapes individual direct job postings (ATS links on Greenhouse, Lever, Workable, etc.)
    using Google search with a failover to Mojeek Search (which has zero bot blocks).
    """
    # X-ray query for direct ATS listings
    search_query = f'"{query}"'
    if location:
        search_query = f'"{query}" {location}'
    search_query = f"{search_query} (site:greenhouse.io OR site:lever.co OR site:workable.com OR site:ashby.co)"

    url = "https://www.google.com/search"
    params = {"q": search_query, "num": limit + 10}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5"
    }

    is_blocked = False
    jobs_raw = []

    try:
        # Fast 4-second timeout to avoid hanging on Google's consent wall
        async with httpx.AsyncClient(timeout=4, follow_redirects=True) as client:
            resp = await client.get(url, params=params, headers=headers)
            
        is_blocked = "captcha" in resp.text.lower() or "unusual traffic" in resp.text.lower() or resp.status_code != 200
        
        if not is_blocked:
            soup = BeautifulSoup(resp.text, "html.parser")
            h3s = soup.find_all("h3")
            for h3 in h3s:
                title_text = h3.get_text(strip=True)
                parent_a = h3.find_parent("a")
                if not parent_a:
                    parent = h3.parent
                    while parent and parent.name != "html":
                        a_el = parent.find("a")
                        if a_el and a_el.get("href"):
                            parent_a = a_el
                            break
                        parent = parent.parent
                href = parent_a.get("href") if parent_a else ""
                if not href or not href.startswith("http") or "google.com" in href:
                    continue
                
                # Fetch snippets
                snippet = ""
                parent = h3.parent
                for _ in range(4):
                    if parent:
                        spans = parent.find_all("span")
                        for s in spans:
                            t = s.get_text(strip=True)
                            if len(t) > 45 and t != title_text:
                                snippet = t
                                break
                        if snippet:
                            break
                        parent = parent.parent
                        
                jobs_raw.append({
                    "title": title_text,
                    "url": href,
                    "snippet": snippet
                })
    except Exception as e:
        print(f"[Google Scraper] Google search failed or timed out: {e}")
        is_blocked = True

    # FAILOVER: If Google blocks, query Mojeek Search (which has zero bot blocks)
    if not jobs_raw or is_blocked:
        print("[Google Scraper] Google search blocked/empty. Failing over to Mojeek...")
        try:
            # We run simple natural keywords search per domain to get targeted results
            mojeek_url = "https://www.mojeek.com/search"
            
            async def run_mojeek_query(domain: str):
                q_str = f"{query} {location} {domain}"
                try:
                    async with httpx.AsyncClient(timeout=8, follow_redirects=True) as client:
                        r = await client.get(mojeek_url, params={"q": q_str}, headers=headers)
                    if r.status_code == 200:
                        s = BeautifulSoup(r.text, "html.parser")
                        links = s.find_all("a")
                        for l in links:
                            href = l.get("href") or ""
                            title_text = l.get_text(strip=True)
                            
                            parsed_link = urlparse(href)
                            netloc = parsed_link.netloc.lower()
                            
                            if any(d in netloc for d in ["greenhouse.io", "lever.co", "workable.com", "ashby.co"]):
                                path_parts = [p for p in parsed_link.path.split("/") if p]
                                if len(path_parts) < 1:
                                    continue # Skip empty home domains
                                
                                jobs_raw.append({
                                    "title": title_text or "Job Opportunity",
                                    "url": href,
                                    "snippet": title_text
                                })
                except Exception as ex:
                    print(f"[Mojeek Scraper] Query {q_str} failed: {ex}")

            import asyncio
            domains = ["greenhouse.io", "lever.co", "workable.com"]
            await asyncio.gather(*(run_mojeek_query(d) for d in domains))
        except Exception as e:
            print(f"[Google Scraper Failover] Mojeek query failed: {e}")

    # Now, parse targets and fetch descriptions in parallel
    import asyncio
    
    async def process_job(raw_job: dict) -> dict | None:
        url = raw_job["url"]
        comp, tit = extract_company_and_title(raw_job["title"], url)
        
        if comp == "Unknown" and tit == "Unknown":
            return None
            
        # Retrieve full job description from Greenhouse/Lever/Workable
        full_desc = await fetch_ats_job_description(url, raw_job["snippet"])
        
        return {
            "id": str(uuid.uuid4()),
            "title": tit,
            "company": comp,
            "location": location or "See listing",
            "description_text": full_desc,
            "url": url,
            "salary_range": "Not disclosed",
            "source": "Google",
            "posted_at": datetime.utcnow()
        }

    # Remove duplicates from jobs_raw before querying details
    seen_urls = set()
    unique_raw = []
    for rj in jobs_raw:
        if rj["url"] not in seen_urls:
            unique_raw.append(rj)
            seen_urls.add(rj["url"])

    tasks = [process_job(rj) for rj in unique_raw[:limit]]
    processed = await asyncio.gather(*tasks)
    
    final_jobs = [j for j in processed if j is not None]
    return final_jobs


async def _llm_parse_query(query: str) -> dict:
    """
    Uses the Ollama LLM to parse the user's search query into keywords and location.
    Falls back to a basic regex parser if Ollama fails.
    """
    try:
        payload = {
            "model": OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": QUERY_PARSE_PROMPT},
                {"role": "user", "content": f"Query: \"{query}\""}
            ],
            "stream": False,
            "format": "json"
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(f"{OLLAMA_URL}/api/chat", json=payload)
            resp.raise_for_status()
            content = resp.json().get("message", {}).get("content", "").strip()
            # Clean markdown code block wraps
            content = re.sub(r"^```(?:json)?|```$", "", content, flags=re.MULTILINE).strip()
            parsed = json.loads(content)
            return {
                "keywords": parsed.get("keywords", query).strip(),
                "location": parsed.get("location", "").strip()
            }
    except Exception as e:
        print(f"[Query Parser] LLM parsing failed ({e}), falling back to regex parser.")
        location = ""
        keywords = query
        match = re.search(r"\s+(?:in|at|near)\s+([a-zA-Z\s,]+)$", query, re.IGNORECASE)
        if match:
            location = match.group(1).strip()
            keywords = query[:match.start()].strip()
        return {"keywords": keywords, "location": location}


async def scrape_all(query: str, limit_per_source: int = 40) -> list[dict]:
    """
    Runs all scrapers in parallel and returns combined results.
    Intelligently extracts location from search queries using Ollama LLM.
    """
    parsed = await _llm_parse_query(query)
    keywords = parsed.get("keywords", query)
    location = parsed.get("location", "")

    print(f"[Scraper] Query parsed: keywords='{keywords}', location='{location}'")

    import asyncio
    results = await asyncio.gather(
        scrape_remotive(keywords, location, limit_per_source),
        scrape_linkedin_guest(keywords, location, limit_per_source),
        scrape_google_jobs(keywords, location, limit_per_source),
        return_exceptions=True,
    )

    all_jobs = []
    for result in results:
        if isinstance(result, list):
            all_jobs.extend(result)

    return all_jobs
