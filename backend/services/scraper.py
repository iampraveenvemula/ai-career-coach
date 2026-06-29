"""
Job scraper service that fetches real listings from external sources
and normalizes them for ingestion into the local DB + vector store.
"""

import httpx
import uuid
import re
from bs4 import BeautifulSoup
from typing import Optional


async def scrape_remotive(query: str, limit: int = 10) -> list[dict]:
    """
    Fetches jobs from the Remotive API (free, no auth required).
    Great for remote AI/ML/engineering roles.
    """
    url = "https://remotive.com/api/remote-jobs"
    params = {"search": query, "limit": limit}

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

            jobs.append({
                "id": str(uuid.uuid4()),
                "title": item.get("title", "Unknown"),
                "company": item.get("company_name", "Unknown"),
                "location": item.get("candidate_required_location", "Remote"),
                "description_text": desc_text,
                "url": item.get("url", ""),
                "salary_range": salary,
                "source": "Remotive",
            })
        return jobs
    except Exception as e:
        print(f"[Remotive] Scrape failed: {e}")
        return []


async def scrape_linkedin_guest(query: str, limit: int = 10) -> list[dict]:
    """
    Fetches jobs from LinkedIn's public guest job search page.
    No authentication required — uses the public guest API.
    """
    url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
    params = {"keywords": query, "location": "", "start": 0}
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
            location = location_el.get_text(strip=True) if location_el else "Unknown"
            job_url = link_el["href"] if link_el and link_el.get("href") else ""

            # LinkedIn guest page doesn't provide full descriptions
            desc = f"{title} at {company}. Location: {location}."

            jobs.append({
                "id": str(uuid.uuid4()),
                "title": title,
                "company": company,
                "location": location,
                "description_text": desc,
                "url": job_url.split("?")[0] if job_url else "",
                "salary_range": "Not disclosed",
                "source": "LinkedIn",
            })
        return jobs
    except Exception as e:
        print(f"[LinkedIn] Scrape failed: {e}")
        return []


async def scrape_google_jobs(query: str, limit: int = 10) -> list[dict]:
    """
    Scrapes job listings from Google search results.
    Uses standard web search with job-related queries.
    """
    search_query = f"{query} jobs hiring"
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
                    "location": "See listing",
                    "description_text": title_el.get_text(strip=True),
                    "url": f"https://www.google.com/search?q={query}+jobs&ibp=htl;jobs",
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
                            "location": "See listing",
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
    """
    import asyncio
    results = await asyncio.gather(
        scrape_remotive(query, limit_per_source),
        scrape_linkedin_guest(query, limit_per_source),
        scrape_google_jobs(query, limit_per_source),
        return_exceptions=True,
    )

    all_jobs = []
    for result in results:
        if isinstance(result, list):
            all_jobs.extend(result)

    return all_jobs
