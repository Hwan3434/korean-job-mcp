"""원티드 채용 스크래퍼 - 내부 API 활용 (인증 불필요)."""
from __future__ import annotations
import httpx
from typing import Optional
from ..models import JobListing, SearchResult
from ..utils.cache import cache

BASE_URL = "https://www.wanted.co.kr/api/v4/jobs"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://www.wanted.co.kr/",
    "wanted-user-agent": "user-agent",
}

# 주요 직군 태그 ID 매핑 (원티드 내부 태그)
JOB_TAG_IDS: dict[str, list[int]] = {
    "개발": [518],
    "백엔드": [518, 672, 669],
    "프론트엔드": [518, 660, 661],
    "풀스택": [518],
    "android": [677],
    "ios": [655],
    "flutter": [10110],
    "python": [669],
    "java": [672],
    "javascript": [660],
    "react": [661],
    "데이터": [1024],
    "ai": [1025],
    "devops": [1026],
    "디자인": [10],
    "기획": [7],
    "마케팅": [8],
}

LOCATION_IDS: dict[str, str] = {
    "서울": "seoul",
    "경기": "gyeonggi",
    "부산": "busan",
    "대구": "daegu",
    "인천": "incheon",
    "광주": "gwangju",
    "대전": "daejeon",
    "전체": "all",
    "원격": "remote",
}


async def search_jobs(
    keyword: Optional[str] = None,
    job_category: Optional[str] = None,
    location: str = "전체",
    years: int = -1,
    limit: int = 20,
) -> SearchResult:
    """원티드에서 채용공고 검색."""
    cache_key = f"wanted:{keyword}:{job_category}:{location}:{years}:{limit}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    params: dict = {
        "country": "kr",
        "job_sort": "job.latest_order",
        "locations": LOCATION_IDS.get(location, "all"),
        "years": years,
        "limit": min(limit, 100),
    }

    if keyword:
        params["query"] = keyword

    # 직군 카테고리로 태그 ID 매핑
    if job_category:
        key = job_category.lower()
        tag_ids = JOB_TAG_IDS.get(key, JOB_TAG_IDS.get("개발", [518]))
        params["tag_type_ids"] = tag_ids

    async with httpx.AsyncClient(headers=HEADERS, timeout=15) as client:
        resp = await client.get(BASE_URL, params=params)
        resp.raise_for_status()
        data = resp.json()

    jobs_raw = data.get("data", [])
    jobs = []
    for job in jobs_raw:
        company_tags = job.get("company_tags", [])
        tech_stack = [t.get("title", "") for t in company_tags if t.get("title")]
        address = job.get("address", {}) or {}
        loc = address.get("location", "") or ""

        jobs.append(
            JobListing(
                id=str(job.get("id", "")),
                title=job.get("position", ""),
                company=job.get("company", {}).get("name", ""),
                location=loc,
                url=f"https://www.wanted.co.kr/wd/{job.get('id')}",
                reward=job.get("reward", {}).get("formatted_total"),
                tech_stack=tech_stack if tech_stack else None,
                experience=_parse_experience(job.get("experience_level", {})),
                source="wanted",
            )
        )

    result = SearchResult(
        total=data.get("links", {}).get("total", len(jobs)),
        jobs=jobs,
        source="wanted",
        keyword=keyword,
    )
    cache.set(cache_key, result)
    return result


async def get_job_detail(job_id: str) -> Optional[JobListing]:
    """원티드 채용공고 상세 조회."""
    cache_key = f"wanted:detail:{job_id}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    url = f"https://www.wanted.co.kr/api/v4/jobs/{job_id}"
    async with httpx.AsyncClient(headers=HEADERS, timeout=15) as client:
        resp = await client.get(url)
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json().get("job", {})

    detail = data.get("detail", {})
    skill_tags = [t.get("title", "") for t in data.get("skill_tags", [])]

    result = JobListing(
        id=str(data.get("id", "")),
        title=data.get("position", ""),
        company=data.get("company", {}).get("name", ""),
        location=data.get("address", {}).get("location", ""),
        description=detail.get("intro", ""),
        requirements=[detail.get("requirements", "")] if detail.get("requirements") else None,
        url=f"https://www.wanted.co.kr/wd/{data.get('id')}",
        deadline=data.get("deadline"),
        reward=data.get("reward", {}).get("formatted_total"),
        tech_stack=skill_tags if skill_tags else None,
        experience=_parse_experience(data.get("experience_level", {})),
        source="wanted",
    )
    cache.set(cache_key, result)
    return result


def _parse_experience(exp_level: dict) -> Optional[str]:
    if not exp_level:
        return None
    min_y = exp_level.get("min")
    max_y = exp_level.get("max")
    if min_y is None:
        return "경력무관"
    if max_y is None or max_y == 0:
        return f"{min_y}년 이상"
    return f"{min_y}~{max_y}년"
