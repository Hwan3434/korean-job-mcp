"""Greenhouse ATS 공개 API 스크래퍼 - 쿠팡, 당근마켓 등."""
from __future__ import annotations
import httpx
from typing import Optional
from ..models import JobListing, SearchResult
from ..utils.cache import cache

# Greenhouse 공개 boards API (인증 불필요)
BOARDS_API = "https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"

# 한국 주요 기업 Greenhouse board 토큰
GREENHOUSE_BOARDS: dict[str, dict] = {
    "coupang": {"name": "쿠팡", "token": "coupang"},
    "daangn": {"name": "당근마켓", "token": "daangn"},
    "당근": {"name": "당근마켓", "token": "daangn"},
    "karrot": {"name": "당근마켓 (글로벌)", "token": "daangn"},
    "sk": {"name": "SK하이닉스 (미국)", "token": "skhynixamerica"},
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json",
}


async def search_jobs(
    board_token: str,
    keyword: Optional[str] = None,
    limit: int = 20,
) -> SearchResult:
    """Greenhouse ATS 채용공고 검색."""
    company_info = GREENHOUSE_BOARDS.get(board_token.lower(), {"name": board_token, "token": board_token})
    actual_token = company_info["token"]
    company_name = company_info["name"]

    cache_key = f"greenhouse:{actual_token}:{keyword}:{limit}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    url = BOARDS_API.format(board_token=actual_token)
    jobs = []
    total = 0

    async with httpx.AsyncClient(headers=HEADERS, timeout=20, follow_redirects=True) as client:
        try:
            resp = await client.get(url, params={"content": "true"})
            resp.raise_for_status()
            data = resp.json()
            all_jobs = data.get("jobs", [])
            total = len(all_jobs)

            # 키워드 필터링 (API 레벨 필터 없으므로 클라이언트 사이드)
            if keyword:
                kw = keyword.lower()
                all_jobs = [
                    j for j in all_jobs
                    if kw in j.get("title", "").lower()
                    or kw in (j.get("departments", [{}]) or [{}])[0].get("name", "").lower()
                ]

            for job in all_jobs[:limit]:
                jobs.append(_parse_job(job, company_name))
        except Exception:
            pass

    result = SearchResult(total=total, jobs=jobs, source=f"greenhouse_{actual_token}", keyword=keyword)
    cache.set(cache_key, result)
    return result


async def search_coupang(keyword: Optional[str] = None, limit: int = 20) -> SearchResult:
    return await search_jobs("coupang", keyword=keyword, limit=limit)


async def search_daangn(keyword: Optional[str] = None, limit: int = 20) -> SearchResult:
    return await search_jobs("daangn", keyword=keyword, limit=limit)


def _parse_job(item: dict, company_name: str) -> JobListing:
    job_id = str(item.get("id", ""))
    url = item.get("absolute_url", "")

    departments = item.get("departments", []) or []
    dept_name = departments[0].get("name", "") if departments else ""

    offices = item.get("offices", []) or []
    location = offices[0].get("name", "") if offices else item.get("location", {}).get("name", "")

    metadata = item.get("metadata", []) or []
    employment_type = ""
    for m in metadata:
        if m.get("name") in ("Employment_Type", "employment_type", "고용형태"):
            employment_type = m.get("value", "")

    return JobListing(
        id=job_id,
        title=item.get("title", ""),
        company=company_name,
        location=location,
        description=dept_name,
        url=url,
        posted_date=item.get("updated_at", ""),
        job_type=employment_type or "정규직",
        source=f"greenhouse",
    )
