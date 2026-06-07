"""네이버 채용 스크래퍼 - recruit.naver.com."""
from __future__ import annotations
import httpx
from typing import Optional
from ..models import JobListing, SearchResult
from ..utils.cache import cache

RECRUIT_URL = "https://recruit.naver.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://recruit.naver.com/",
    "Accept": "application/json, text/html, */*",
}


async def search_jobs(
    keyword: Optional[str] = None,
    limit: int = 20,
) -> SearchResult:
    """네이버 채용공고 검색."""
    cache_key = f"naver:{keyword}:{limit}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    jobs = []

    async with httpx.AsyncClient(headers=HEADERS, timeout=15, follow_redirects=True) as client:
        # 네이버 채용 내부 API 시도
        jobs = await _try_api(client, keyword, limit)
        if not jobs:
            jobs = await _scrape_html(client, keyword, limit)

    result = SearchResult(total=len(jobs), jobs=jobs, source="naver", keyword=keyword)
    cache.set(cache_key, result)
    return result


async def _try_api(
    client: httpx.AsyncClient, keyword: Optional[str], limit: int
) -> list[JobListing]:
    """네이버 내부 API 탐색."""
    endpoints = [
        f"{RECRUIT_URL}/api/jobs",
        f"{RECRUIT_URL}/api/v1/jobs",
        "https://api.recruit.naver.com/v1/jobs",
    ]
    params = {"limit": limit}
    if keyword:
        params["query"] = keyword

    for endpoint in endpoints:
        try:
            resp = await client.get(endpoint, params=params)
            if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("application/json"):
                data = resp.json()
                jobs = data.get("jobs", data.get("data", data.get("list", [])))
                if jobs:
                    return [_parse_job(j) for j in jobs[:limit]]
        except Exception:
            continue
    return []


async def _scrape_html(
    client: httpx.AsyncClient, keyword: Optional[str], limit: int
) -> list[JobListing]:
    """HTML 스크래핑으로 네이버 채용 공고 파싱."""
    from bs4 import BeautifulSoup
    import json

    url = f"{RECRUIT_URL}/naver"
    try:
        resp = await client.get(url)
        soup = BeautifulSoup(resp.text, "html.parser")

        # Next.js data 탐색
        script = soup.find("script", id="__NEXT_DATA__")
        if script:
            data = json.loads(script.string)
            jobs_data = (
                data.get("props", {}).get("pageProps", {}).get("jobs", [])
                or data.get("props", {}).get("pageProps", {}).get("jobList", [])
            )
            if jobs_data:
                return [_parse_job(j) for j in jobs_data[:limit]]

        jobs = []
        selectors = [".job_item", ".recruit_item", "li[data-job-id]", ".position-item"]
        for sel in selectors:
            cards = soup.select(sel)
            if cards:
                for card in cards[:limit]:
                    title_el = card.select_one("h3, h4, .title, .position, strong")
                    title = title_el.get_text(strip=True) if title_el else ""
                    link = card.select_one("a[href]")
                    href = link.get("href", "") if link else ""
                    full_url = f"{RECRUIT_URL}{href}" if href.startswith("/") else href
                    if title:
                        jobs.append(
                            JobListing(
                                title=title,
                                company="네이버",
                                url=full_url or RECRUIT_URL,
                                source="naver",
                            )
                        )
                break
        return jobs
    except Exception:
        return []


def _parse_job(item: dict) -> JobListing:
    job_id = str(item.get("id", item.get("jobId", "")))
    return JobListing(
        id=job_id,
        title=item.get("title", item.get("jobTitle", item.get("position", ""))),
        company="네이버",
        location=item.get("location", item.get("workPlace", "성남")),
        description=item.get("description", item.get("summary", "")),
        url=item.get("url", f"{RECRUIT_URL}/naver#{job_id}"),
        deadline=item.get("deadline", item.get("endDate", "")),
        experience=item.get("career", item.get("experienceLevel", "")),
        source="naver",
    )
