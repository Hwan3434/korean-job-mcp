"""카카오 채용 스크래퍼 - careers.kakao.com 내부 API 활용."""
from __future__ import annotations
import httpx
from typing import Optional
from ..models import JobListing, SearchResult
from ..utils.cache import cache

# Playwright 인터셉트로 발견한 실제 API 엔드포인트
API_BASE = "https://careers.kakao.com/public/api/job-list"
JOB_DETAIL_URL = "https://careers.kakao.com/public/api/job"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120",
    "Referer": "https://careers.kakao.com/jobs",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

# 직군 파트 매핑
PARTS: dict[str, str] = {
    "기술": "TECHNOLOGY",
    "technology": "TECHNOLOGY",
    "개발": "TECHNOLOGY",
    "비즈니스": "BUSINESS",
    "business": "BUSINESS",
    "크리에이티브": "CREATIVE",
    "creative": "CREATIVE",
    "전체": "",
}

# 카카오 계열사
COMPANIES: dict[str, str] = {
    "카카오": "KAKAO",
    "kakao": "KAKAO",
    "카카오게임즈": "KAKAOGAMES",
    "카카오엔터": "KAKAOENTERTAINMENT",
    "카카오뱅크": "KAKAOBANK",
    "카카오페이": "KAKAOPAY",
    "카카오모빌리티": "KAKAOMOBILITY",
    "전체": "ALL",
}


async def search_jobs(
    keyword: Optional[str] = None,
    part: str = "기술",
    company: str = "카카오",
    limit: int = 20,
    page: int = 1,
) -> SearchResult:
    """카카오 채용공고 검색."""
    cache_key = f"kakao:{keyword}:{part}:{company}:{limit}:{page}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    params: dict = {
        "skillSet": "",
        "part": PARTS.get(part.lower(), "TECHNOLOGY"),
        "company": COMPANIES.get(company, "KAKAO"),
        "employeeType": "",
        "page": page,
    }
    if keyword:
        params["keyword"] = keyword

    jobs = []
    total = 0

    async with httpx.AsyncClient(headers=HEADERS, timeout=15, follow_redirects=True) as client:
        try:
            resp = await client.get(API_BASE, params=params)
            resp.raise_for_status()
            data = resp.json()
            total = data.get("totalJobCount", data.get("totalCount", 0))
            for item in data.get("jobList", [])[:limit]:
                jobs.append(_parse_job(item))
        except Exception:
            pass

    result = SearchResult(total=total, jobs=jobs, source="kakao", keyword=keyword)
    cache.set(cache_key, result)
    return result


def _parse_job(item: dict) -> JobListing:
    job_id = str(item.get("jobOfferId", item.get("id", "")))
    real_id = item.get("realId", job_id)
    company_name = item.get("companyName", "카카오")

    skills = [s.get("skillSetName", "") for s in item.get("skillSetList", [])]

    return JobListing(
        id=job_id,
        title=item.get("jobOfferTitle", item.get("title", "")),
        company=company_name,
        location=item.get("locationName", "판교"),
        description=item.get("introduction", item.get("summary", "")),
        url=f"https://careers.kakao.com/jobs/{real_id}" if real_id else "https://careers.kakao.com/jobs",
        posted_date=item.get("regDate", ""),
        deadline=item.get("endDate", ""),
        job_type=item.get("employeeTypeName", "정규직"),
        experience=item.get("experienceLevel", ""),
        tech_stack=skills if skills else None,
        source="kakao",
    )
