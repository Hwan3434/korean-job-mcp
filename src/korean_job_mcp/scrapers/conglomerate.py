"""한국 대기업/IT기업 채용 통합 스크래퍼."""
from __future__ import annotations
import asyncio
import httpx
from typing import Optional
from ..models import JobListing, SearchResult
from ..utils.cache import cache

COMPANIES: dict[str, dict] = {
    "lg": {
        "name": "LG전자",
        "url": "https://recruit.lg.com",
        "api": "https://recruit.lg.com/api/jobs",
    },
    "hyundai": {
        "name": "현대자동차",
        "url": "https://talent.hyundai.com",
        "api": "https://talent.hyundai.com/api/v1/jobs",
    },
    "sk": {
        "name": "SK하이닉스",
        "url": "https://careers.skhynix.com",
        "api": "https://careers.skhynix.com/api/jobs",
    },
    "coupang": {
        "name": "쿠팡",
        "url": "https://www.coupang.jobs/ko",
        "api": "https://www.coupang.jobs/api/jobs",
    },
    "line": {
        "name": "라인",
        "url": "https://linecorp.com/ko/career/",
        "api": None,
    },
    "krafton": {
        "name": "크래프톤",
        "url": "https://careers.krafton.com",
        "api": "https://careers.krafton.com/api/jobs",
    },
    "ncsoft": {
        "name": "엔씨소프트",
        "url": "https://careers.ncsoft.com",
        "api": None,
    },
    "nexon": {
        "name": "넥슨",
        "url": "https://career.nexon.com",
        "api": None,
    },
    "kakaobank": {
        "name": "카카오뱅크",
        "url": "https://kakaobank.career.greetinghr.com/",
        "api": None,
    },
    "toss": {
        "name": "토스",
        "url": "https://toss.im/career",
        "api": "https://toss.im/api/career/jobs",
    },
    "당근": {
        "name": "당근마켓",
        "url": "https://about.daangn.com/jobs/",
        "api": "https://about.daangn.com/api/jobs",
    },
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json, text/html, */*",
}


async def search_company_jobs(
    company_key: str,
    keyword: Optional[str] = None,
    limit: int = 20,
) -> SearchResult:
    """특정 기업 채용공고 검색."""
    cache_key = f"conglomerate:{company_key}:{keyword}:{limit}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    company = COMPANIES.get(company_key.lower())
    if not company:
        return SearchResult(total=0, jobs=[], source=company_key, keyword=keyword)

    jobs = []
    async with httpx.AsyncClient(headers={**HEADERS, "Referer": company["url"]}, timeout=20, follow_redirects=True) as client:
        if company.get("api"):
            jobs = await _try_api(client, company, keyword, limit)
        if not jobs:
            jobs = await _scrape_company(client, company, keyword, limit)

    result = SearchResult(total=len(jobs), jobs=jobs, source=company_key, keyword=keyword)
    cache.set(cache_key, result)
    return result


async def list_companies() -> dict[str, str]:
    """지원하는 기업 목록 반환."""
    return {key: info["name"] for key, info in COMPANIES.items()}


async def search_all_companies(
    keyword: Optional[str] = None,
    company_keys: Optional[list[str]] = None,
    limit_per_company: int = 10,
) -> SearchResult:
    """여러 기업 동시 검색 (병렬)."""
    keys = company_keys or list(COMPANIES.keys())
    tasks = [search_company_jobs(k, keyword, limit_per_company) for k in keys]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_jobs = []
    for r in results:
        if isinstance(r, SearchResult):
            all_jobs.extend(r.jobs)

    return SearchResult(
        total=len(all_jobs),
        jobs=all_jobs,
        source="conglomerate_all",
        keyword=keyword,
    )


async def _try_api(
    client: httpx.AsyncClient, company: dict, keyword: Optional[str], limit: int
) -> list[JobListing]:
    params = {"limit": limit}
    if keyword:
        params["keyword"] = keyword

    try:
        resp = await client.get(company["api"], params=params)
        if resp.status_code == 200:
            data = resp.json()
            items = data.get("jobs", data.get("data", data.get("results", [])))
            return [_parse_generic(j, company["name"]) for j in items[:limit]]
    except Exception:
        pass
    return []


async def _scrape_company(
    client: httpx.AsyncClient, company: dict, keyword: Optional[str], limit: int
) -> list[JobListing]:
    """HTML/Next.js JSON 스크래핑."""
    from bs4 import BeautifulSoup
    import json

    try:
        resp = await client.get(company["url"])
        soup = BeautifulSoup(resp.text, "html.parser")

        # __NEXT_DATA__ 탐색
        script = soup.find("script", id="__NEXT_DATA__")
        if script:
            data = json.loads(script.string)
            props = data.get("props", {}).get("pageProps", {})
            items = props.get("jobs", props.get("positions", props.get("careers", [])))
            if items:
                return [_parse_generic(j, company["name"]) for j in items[:limit]]

        # JSON-LD 탐색
        json_ld = soup.find("script", type="application/ld+json")
        if json_ld:
            try:
                data = json.loads(json_ld.string)
                if isinstance(data, list):
                    data = data[0]
                items = data.get("jobPosting", [])
                if items:
                    return [_parse_jsonld(j, company["name"]) for j in items[:limit]]
            except Exception:
                pass

        # 일반 카드 파싱
        jobs = []
        selectors = [
            ".job-item", ".position-item", ".career-item",
            "li[data-id]", "article.job", ".opening-item",
        ]
        for sel in selectors:
            cards = soup.select(sel)
            if cards:
                for card in cards[:limit]:
                    title_el = card.select_one("h3, h4, .title, strong")
                    link_el = card.select_one("a[href]")
                    title = title_el.get_text(strip=True) if title_el else ""
                    href = link_el.get("href", "") if link_el else ""
                    full_url = (
                        f"{company['url'].rstrip('/')}{href}"
                        if href.startswith("/")
                        else href or company["url"]
                    )
                    if title:
                        jobs.append(
                            JobListing(
                                title=title,
                                company=company["name"],
                                url=full_url,
                                source=company["name"],
                            )
                        )
                break
        return jobs
    except Exception:
        return []


def _parse_generic(item: dict, company_name: str) -> JobListing:
    job_id = str(item.get("id", item.get("_id", "")))
    return JobListing(
        id=job_id,
        title=item.get("title", item.get("position", item.get("name", ""))),
        company=item.get("company", company_name),
        location=item.get("location", item.get("workLocation", item.get("address", ""))),
        description=item.get("description", item.get("summary", "")),
        url=item.get("url", item.get("applyUrl", item.get("link", ""))),
        deadline=item.get("deadline", item.get("endDate", "")),
        experience=item.get("career", item.get("experienceLevel", "")),
        tech_stack=item.get("skills", item.get("tech_stack", [])) or None,
        source=company_name,
    )


def _parse_jsonld(item: dict, company_name: str) -> JobListing:
    return JobListing(
        title=item.get("title", ""),
        company=item.get("hiringOrganization", {}).get("name", company_name),
        location=item.get("jobLocation", {}).get("address", {}).get("addressLocality", ""),
        description=item.get("description", ""),
        url=item.get("url", ""),
        posted_date=item.get("datePosted", ""),
        deadline=item.get("validThrough", ""),
        source=company_name,
    )
