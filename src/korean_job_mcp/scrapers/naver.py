"""네이버 채용 스크래퍼 - recruit.navercorp.com (CSRF 세션 처리)."""
from __future__ import annotations
import httpx
import re
from typing import Optional
from ..models import JobListing, SearchResult
from ..utils.cache import cache

BASE_URL = "https://recruit.navercorp.com"
LIST_URL = f"{BASE_URL}/rcrt/list.do"
API_URL = f"{BASE_URL}/rcrt/loadJobList.do"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
}

COMPANY_CODES: dict[str, str] = {
    "네이버": "NV",
    "naver": "NV",
    "라인": "LN",
    "line": "LN",
    "웹툰": "WT",
    "webtoon": "WT",
    "전체": "",
}


async def search_jobs(
    keyword: Optional[str] = None,
    company: str = "전체",
    job_type: Optional[str] = None,
    limit: int = 20,
) -> SearchResult:
    """네이버 채용공고 검색 (CSRF 세션 자동 처리)."""
    cache_key = f"naver:{keyword}:{company}:{job_type}:{limit}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    jobs = []
    total = 0

    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        client.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120",
        })

        try:
            # 1단계: 목록 페이지 방문 → 세션 쿠키 + CSRF 토큰 획득
            r_main = await client.get(LIST_URL)
            csrf_matches = re.findall(r"_csrf=([a-f0-9-]+)", r_main.text)
            csrf = csrf_matches[0] if csrf_matches else ""

            if not csrf:
                return SearchResult(total=0, jobs=[], source="naver", keyword=keyword)

            # 2단계: AJAX POST로 채용 목록 로드
            company_cd = COMPANY_CODES.get(company.lower(), "")
            payload = {
                "entTypeCd": "",
                "workTypeCd": "",
                "searchWord": keyword or "",
                "sysCompanyCd": company_cd,
                "classId": "",
                "srchClassCd": "",
                "_csrf": csrf,
            }
            if job_type == "경력":
                payload["entTypeCd"] = "0020"
            elif job_type == "신입":
                payload["entTypeCd"] = "0010"

            client.headers.update({
                **HEADERS,
                "Referer": LIST_URL,
            })

            resp = await client.post(API_URL, data=payload)
            data = resp.json()
            all_jobs = data.get("list", [])
            total = data.get("totalSize", len(all_jobs))

            for item in all_jobs[:limit]:
                jobs.append(_parse_job(item))
        except Exception:
            pass

    result = SearchResult(total=total, jobs=jobs, source="naver", keyword=keyword)
    cache.set(cache_key, result)
    return result


def _parse_job(item: dict) -> JobListing:
    anno_id = str(item.get("annoId", ""))
    company_name = item.get("sysCompanyCdNm", "네이버")
    end_ymd = item.get("endYmd", "")
    deadline = f"{end_ymd[:4]}.{end_ymd[4:6]}.{end_ymd[6:]}" if len(end_ymd) == 8 else end_ymd
    start_ymd = item.get("staYmd", "")
    posted = f"{start_ymd[:4]}.{start_ymd[4:6]}.{start_ymd[6:]}" if len(start_ymd) == 8 else start_ymd

    return JobListing(
        id=anno_id,
        title=item.get("annoSubject", ""),
        company=company_name,
        location="성남",
        url=f"{BASE_URL}/rcrt/view.do?annoId={anno_id}" if anno_id else BASE_URL,
        posted_date=posted,
        deadline=deadline,
        job_type=item.get("entTypeCdNm", ""),
        source="naver",
    )
