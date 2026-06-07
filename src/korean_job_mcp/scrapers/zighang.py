"""zighang.com/it IT 채용 스크래퍼 - 실제 API 활용."""
from __future__ import annotations
import httpx
from typing import Optional
from ..models import JobListing, SearchResult
from ..utils.cache import cache

# Playwright 인터셉트로 발견한 실제 API
API_BASE = "https://api.zighang.com/api/recruitments/v3"
CATEGORIES_URL = "https://api.zighang.com/api/recruitments/job-categories"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120",
    "Referer": "https://zighang.com/it",
    "Accept": "application/json, text/plain, */*",
    "Origin": "https://zighang.com",
}

# IT 직군 카테고리 (depthTwos 파라미터)
DEPTH_TWO_CATEGORIES: dict[str, str] = {
    "백엔드": "서버_백엔드",
    "backend": "서버_백엔드",
    "서버": "서버_백엔드",
    "프론트엔드": "프론트엔드",
    "frontend": "프론트엔드",
    "풀스택": "웹풀스택",
    "fullstack": "웹풀스택",
    "android": "안드로이드",
    "안드로이드": "안드로이드",
    "ios": "iOS",
    "flutter": "크로스플랫폼",
    "크로스플랫폼": "크로스플랫폼",
    "dba": "DBA",
    "devops": "DevOps_SRE",
    "sre": "DevOps_SRE",
    "qa": "QA_테스트",
    "ai": "소프트웨어엔지니어",
    "보안": "정보보호_보안",
    "security": "정보보호_보안",
}


async def search_jobs(
    keyword: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 20,
    page: int = 1,
    sort: str = "ZIGHANG_SCORE",
) -> SearchResult:
    """zighang.com/it IT 채용공고 검색."""
    cache_key = f"zighang:{keyword}:{category}:{limit}:{page}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    # API는 0-based 페이지
    params: dict = {
        "page": page - 1,
        "size": min(limit, 50),
        "includeCareerOpen": "true",
        "sortCondition": sort,
        "orderCondition": "DESC",
    }

    if keyword:
        params["keyword"] = keyword

    # 직군 카테고리 필터
    depth_two = DEPTH_TWO_CATEGORIES.get(category.lower()) if category else None
    if depth_two:
        params["depthTwos"] = depth_two

    jobs = []
    total = 0

    async with httpx.AsyncClient(headers=HEADERS, timeout=15, follow_redirects=True) as client:
        try:
            resp = await client.get(API_BASE, params=params)
            resp.raise_for_status()
            envelope = resp.json()
            # 응답 구조: { success, data: { content, totalElements, ... } }
            data = envelope.get("data", envelope)
            total = data.get("totalElements", data.get("total", 0))
            items = data.get("content", data.get("recruitments", []))
            for item in items[:limit]:
                jobs.append(_parse_job(item))
        except Exception:
            pass

    result = SearchResult(total=total, jobs=jobs, source="zighang", keyword=keyword)
    cache.set(cache_key, result)
    return result


async def get_job_categories() -> list[dict]:
    """zighang 직군 카테고리 목록 조회."""
    async with httpx.AsyncClient(headers=HEADERS, timeout=10) as client:
        try:
            resp = await client.get(CATEGORIES_URL)
            return resp.json()
        except Exception:
            return []


def _parse_job(item: dict) -> JobListing:
    # 실제 API 응답 구조 기반 파싱
    # id, title, company{id,name,image}, createdAt, endDate,
    # regions[], careerMin, careerMax, tags[], badges[]
    job_id = str(item.get("id", ""))
    company = item.get("company", {}) or {}
    company_name = company.get("name", "") if isinstance(company, dict) else str(company)

    tags = item.get("tags", []) or []
    tag_names = [t.get("name", t) if isinstance(t, dict) else str(t) for t in tags]

    regions = item.get("regions", []) or []
    location = ""
    if regions:
        first = regions[0]
        location = first.get("name", str(first)) if isinstance(first, dict) else str(first)

    career_min = item.get("careerMin")
    career_max = item.get("careerMax")
    experience = ""
    if career_min is not None:
        if career_max:
            experience = f"{career_min}~{career_max}년"
        else:
            experience = f"{career_min}년 이상"
    elif career_min == 0:
        experience = "신입"

    return JobListing(
        id=job_id,
        title=item.get("title", ""),
        company=company_name,
        location=location,
        description=item.get("summary", ""),
        url=f"https://zighang.com/recruitment/{job_id}" if job_id else "https://zighang.com/it",
        posted_date=item.get("createdAt", ""),
        deadline=item.get("endDate", ""),
        tech_stack=tag_names if tag_names else None,
        experience=experience or None,
        source="zighang",
    )
