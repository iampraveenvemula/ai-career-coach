"""
Job scraper service that fetches real listings from external sources
and normalizes them for ingestion into the local DB + vector store.
"""

import httpx
import uuid
import re
from bs4 import BeautifulSoup
from typing import Optional  # noqa: F401


async def scrape_remotive(query: str, location: str = "", limit: int = 10) -> list[dict]:
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
            # If the user searched for a specific location, filter or label accordingly
            if location and location.lower() not in loc.lower() and loc.lower() != "worldwide":
                # Skip if it doesn't match location criteria
                continue

            jobs.append({
                "id": str(uuid.uuid4()),
                "title": item.get("title", "Unknown"),
                "company": item.get("company_name", "Unknown"),
                "location": loc,
                "description_text": desc_text,
                "url": item.get("url", ""),
                "salary_range": salary,
                "source": "Remotive",
            })
        return jobs
    except Exception as e:
        print(f"[Remotive] Scrape failed: {e}")
        return []


async def scrape_linkedin_guest(query: str, location: str = "", limit: int = 10) -> list[dict]:
    """
    Fetches jobs from LinkedIn's public guest job search page.
    No authentication required — uses the public guest API.
    """
    url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    params = {"keywords": query, "location": location or "", "start": 0}
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.find_all("div", class_="base-card")

        jobs = []
        for card in cards[:limit]:
            title_el = card.find("h3", class_="base-search-card__title")
            company_el = card.find("h4", class_="base-search-card__subtitle")
            location_el = card.find("span", class_="job-search-card__location")
            link_el = card.find("a", class_="base-card__full-link")

            title = title_el.get_text(strip=True) if title_el else "Unknown"
            company = company_el.get_text(strip=True) if company_el else "Unknown"
            loc = location_el.get_text(strip=True) if location_el else (location or "Unknown")
            job_url = link_el["href"] if link_el and link_el.get("href") else ""

            # LinkedIn guest page doesn't provide full descriptions
            desc = f"{title} at {company}. Location: {loc}."

            jobs.append({
                "id": str(uuid.uuid4()),
                "title": title,
                "company": company,
                "location": loc,
                "description_text": desc,
                "url": job_url.split("?")[0] if job_url else "",
                "salary_range": "Not disclosed",
                "source": "LinkedIn",
            })
        return jobs
    except Exception as e:
        print(f"[LinkedIn] Scrape failed: {e}")
        return []


async def scrape_google_jobs(query: str, location: str = "", limit: int = 10) -> list[dict]:
    """
    Scrapes job listings from Google search results.
    Uses standard web search with job-related queries.
    """
    search_query = f"{query} jobs hiring"
    if location:
        search_query = f"{query} jobs hiring in {location}"

    url = "https://www.google.com/search"
    params = {"q": search_query, "num": 20}
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }

    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # Try to find structured job cards from Google's job panel
        jobs = []

        # Look for job listing structured data
        for item in soup.find_all("div", class_="BjJfJf"):  # Google job card class
            title_el = item.find("div", class_="BjJfJf")
            if title_el:
                jobs.append({
                    "id": str(uuid.uuid4()),
                    "title": title_el.get_text(strip=True),
                    "company": "Via Google",
                    "location": location or "See listing",
                    "description_text": title_el.get_text(strip=True),
                    "url": f"https://www.google.com/search?q={query}+{location}+jobs&ibp=htl;jobs",
                    "salary_range": "Not disclosed",
                    "source": "Google",
                })

        # Fallback: extract from search result snippets
        if not jobs:
            for result in soup.find_all("div", class_="g")[:limit]:
                title_el = result.find("h3")
                snippet_el = result.find("span", class_="aCOpRe") or result.find("div", class_="VwiC3b")
                link_el = result.find("a")

                if title_el:
                    title_text = title_el.get_text(strip=True)
                    # Filter to only job-related results
                    if any(kw in title_text.lower() for kw in ["job", "hiring", "career", "engineer", "scientist", "developer", "position"]):
                        snippet = snippet_el.get_text(strip=True) if snippet_el else title_text
                        href = link_el["href"] if link_el and link_el.get("href") else ""

                        jobs.append({
                            "id": str(uuid.uuid4()),
                            "title": title_text,
                            "company": "Via Google Search",
                            "location": location or "See listing",
                            "description_text": snippet[:500],
                            "url": href,
                            "salary_range": "Not disclosed",
                            "source": "Google",
                        })

        return jobs[:limit]
    except Exception as e:
        print(f"[Google] Scrape failed: {e}")
        return []


async def scrape_all(query: str, limit_per_source: int = 5) -> list[dict]:
    """
    Runs all scrapers in parallel and returns combined results.
    Intelligently extracts location from the search query (e.g. "in uae")
    to pass as a location filter to external APIs.
    """
    location = ""
    keywords = query

    # Parse location from queries like "ai engineer in uae" or "software engineer at dubai"
    match = re.search(r"\s+(?:in|at|near)\s+([a-zA-Z\s,]+)$", query, re.IGNORECASE)
    if match:
        location = match.group(1).strip()
        keywords = query[:match.start()].strip()

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
