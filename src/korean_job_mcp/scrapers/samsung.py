"""삼성 채용 스크래퍼 - www.samsungcareers.com."""
from __future__ import annotations
import httpx
from typing import Optional
from ..models import JobListing, SearchResult
from ..utils.cache import cache

SAMSUNG_CAREERS_URL = "https://www.samsungcareers.com"
SAMSUNG_ELECTONICS_API = "https://www.samsung.com/sec/careers"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://www.samsungcareers.com/",
    "Accept": "application/json, text/html, */*",
}

# 삼성 계열사별 채용 URL
SUBSIDIARIES: dict[str, str] = {
    "삼성전자": "https://www.samsungcareers.com/",
    "삼성SDS": "https://www.samsungsds.com/kr/recruit/",
    "삼성리서치": "https://research.samsung.com/careers",
    "삼성반도체": "https://semiconductor.samsung.com/about-us/careers/",
}


async def search_jobs(
    keyword: Optional[str] = None,
    subsidiary: Optional[str] = None,
    limit: int = 20,
) -> SearchResult:
    """삼성 채용공고 검색."""
    cache_key = f"samsung:{keyword}:{subsidiary}:{limit}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    jobs = []
    async with httpx.AsyncClient(headers=HEADERS, timeout=20, follow_redirects=True) as client:
        jobs = await _fetch_samsung_careers(client, keyword, limit)

    result = SearchResult(total=len(jobs), jobs=jobs, source="samsung", keyword=keyword)
    cache.set(cache_key, result)
    return result


async def _fetch_samsung_careers(
    client: httpx.AsyncClient, keyword: Optional[str], limit: int
) -> list[JobListing]:
    """삼성 채용 메인 페이지 파싱."""
    from bs4 import BeautifulSoup
    import json

    # API 엔드포인트 시도
    api_endpoints = [
        f"{SAMSUNG_CAREERS_URL}/api/job-postings",
        f"{SAMSUNG_CAREERS_URL}/careers/api/jobs",
    ]
    params = {"limit": limit, "lang": "ko"}
    if keyword:
        params["keyword"] = keyword

    for endpoint in api_endpoints:
        try:
            resp = await client.get(endpoint, params=params)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("jobs", data.get("postings", data.get("data", [])))
                if items:
                    return [_parse_job(j, "삼성전자") for j in items[:limit]]
        except Exception:
            continue

    # 메인 페이지 HTML 파싱 fallback
    try:
        resp = await client.get(SAMSUNG_CAREERS_URL)
        soup = BeautifulSoup(resp.text, "html.parser")

        # JSON-LD 데이터 탐색
        json_ld = soup.find("script", type="application/ld+json")
        if json_ld:
            data = json.loads(json_ld.string)
            if isinstance(data, list):
                data = data[0]
            items = data.get("jobPosting", data.get("jobs", []))
            if items:
                return [_parse_jsonld_job(j) for j in items[:limit]]

        # CSS 셀렉터로 공고 카드 파싱
        jobs = []
        cards = soup.select(".job-card, .position-card, .recruit-item, [data-job-id]")
        for card in cards[:limit]:
            title = card.select_one("h3, h4, .job-title, .position")
            link = card.select_one("a[href]")
            company_el = card.select_one(".company, .entity")

            title_text = title.get_text(strip=True) if title else ""
            href = link.get("href", "") if link else ""
            full_url = f"{SAMSUNG_CAREERS_URL}{href}" if href.startswith("/") else (href or SAMSUNG_CAREERS_URL)
            company_name = company_el.get_text(strip=True) if company_el else "삼성전자"

            if title_text:
                jobs.append(
                    JobListing(
                        title=title_text,
                        company=company_name,
                        url=full_url,
                        source="samsung",
                    )
                )
        return jobs
    except Exception:
        return []


def _parse_job(item: dict, company: str = "삼성전자") -> JobListing:
    job_id = str(item.get("id", item.get("jobId", "")))
    return JobListing(
        id=job_id,
        title=item.get("title", item.get("jobTitle", item.get("position", ""))),
        company=item.get("company", company),
        location=item.get("location", item.get("workLocation", "수원")),
        description=item.get("description", ""),
        url=item.get("url", item.get("applyUrl", f"{SAMSUNG_CAREERS_URL}/jobs/{job_id}")),
        deadline=item.get("deadline", item.get("closingDate", "")),
        source="samsung",
    )


def _parse_jsonld_job(item: dict) -> JobListing:
    """JSON-LD JobPosting 스키마 파싱."""
    return JobListing(
        title=item.get("title", ""),
        company=item.get("hiringOrganization", {}).get("name", "삼성"),
        location=item.get("jobLocation", {}).get("address", {}).get("addressLocality", ""),
        description=item.get("description", ""),
        url=item.get("url", SAMSUNG_CAREERS_URL),
        posted_date=item.get("datePosted", ""),
        deadline=item.get("validThrough", ""),
        source="samsung",
    )
