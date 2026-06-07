"""토스 채용 스크래퍼 - 토스 자체 API 활용."""
from __future__ import annotations
import httpx
from typing import Optional
from ..models import JobListing, SearchResult
from ..utils.cache import cache

# Playwright 인터셉트로 발견한 토스 채용 API
JOB_GROUPS_URL = "https://api-public.toss.im/api/v3/ipd-eggnog/career/job-groups"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120",
    "Referer": "https://toss.im/career/jobs",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://toss.im",
}

# 토스 계열사 목록
SUBSIDIARIES = ["토스", "토스뱅크", "토스증권", "토스페이먼츠", "토스플레이스", "토스씨엑스"]


async def search_jobs(
    keyword: Optional[str] = None,
    subsidiary: Optional[str] = None,
    limit: int = 20,
) -> SearchResult:
    """토스 채용공고 검색."""
    cache_key = f"toss:{keyword}:{subsidiary}:{limit}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    jobs = []
    total = 0

    async with httpx.AsyncClient(headers=HEADERS, timeout=15, follow_redirects=True) as client:
        try:
            resp = await client.get(JOB_GROUPS_URL)
            resp.raise_for_status()
            data = resp.json()
            all_groups = data.get("success", [])
            total = len(all_groups)

            filtered = all_groups
            if keyword:
                kw = keyword.lower()
                filtered = [
                    g for g in filtered
                    if kw in g.get("title", "").lower()
                ]
            if subsidiary:
                filtered = [
                    g for g in filtered
                    if subsidiary in _get_subsidiary(g)
                ]

            for group in filtered[:limit]:
                jobs.append(_parse_job(group))
        except Exception:
            pass

    result = SearchResult(total=total, jobs=jobs, source="toss", keyword=keyword)
    cache.set(cache_key, result)
    return result


def _get_subsidiary(group: dict) -> str:
    primary = group.get("primary_job", {}) or {}
    metadata = primary.get("metadata", []) or []
    for m in metadata:
        if "자회사" in m.get("name", "") or "subsidiary" in m.get("name", "").lower():
            return m.get("value", "")
    return ""


def _parse_job(group: dict) -> JobListing:
    job_id = str(group.get("id", ""))
    primary = group.get("primary_job", {}) or {}
    location = primary.get("location", {}).get("name", "서울") if primary.get("location") else "서울"

    metadata = primary.get("metadata", []) or []
    employment_type = ""
    subsidiary = ""
    for m in metadata:
        name = m.get("name", "")
        if "Employment_Type" in name or "고용형태" in name:
            employment_type = m.get("value", "")
        if "자회사" in name or "subsidiary" in name.lower():
            subsidiary = m.get("value", "")

    company_name = subsidiary if subsidiary else "토스"
    url = primary.get("absolute_url", f"https://toss.im/career/job-detail?gh_jid={job_id}")

    return JobListing(
        id=job_id,
        title=group.get("title", ""),
        company=company_name,
        location=location,
        url=url,
        job_type=employment_type or "정규직",
        source="toss",
    )
