"""한국 채용 MCP 서버 - 원티드, 직장인, 대기업 통합 채용 조회."""
from __future__ import annotations
import asyncio
from typing import Optional, Annotated
from fastmcp import FastMCP
from .models import JobListing, SearchResult
from . import scrapers

mcp = FastMCP(
    name="korean-job-mcp",
    instructions=(
        "한국 채용 정보를 원티드, zighang.com/it, 카카오, 네이버, 삼성 등에서 통합 조회하는 MCP 서버입니다. "
        "인증 없이 무료로 사용 가능합니다."
    ),
)


@mcp.tool(description="원티드(wanted.co.kr)에서 채용공고를 검색합니다.")
async def search_wanted_jobs(
    keyword: Annotated[Optional[str], "검색 키워드 (예: 백엔드, Python, AI)"] = None,
    job_category: Annotated[
        Optional[str],
        "직군 카테고리 (개발/백엔드/프론트엔드/android/ios/flutter/python/java/javascript/react/데이터/ai/devops/디자인/기획/마케팅)",
    ] = None,
    location: Annotated[str, "지역 (서울/경기/부산/대구/인천/광주/대전/전체/원격)"] = "전체",
    years: Annotated[int, "경력 연수 (-1: 전체, 0: 신입)"] = -1,
    limit: Annotated[int, "결과 개수 (최대 100)"] = 20,
) -> dict:
    """원티드 내부 API를 통해 채용공고를 검색합니다 (인증 불필요)."""
    from .scrapers import wanted
    result = await wanted.search_jobs(
        keyword=keyword,
        job_category=job_category,
        location=location,
        years=years,
        limit=limit,
    )
    return _format_result(result)


@mcp.tool(description="원티드 채용공고 상세 정보를 조회합니다.")
async def get_wanted_job_detail(
    job_id: Annotated[str, "원티드 채용공고 ID (숫자, 예: 365793)"],
) -> dict:
    """원티드 특정 채용공고의 상세 내용을 가져옵니다."""
    from .scrapers import wanted
    job = await wanted.get_job_detail(job_id)
    if not job:
        return {"error": f"채용공고를 찾을 수 없습니다: {job_id}"}
    return job.model_dump(exclude_none=True)


@mcp.tool(description="zighang.com/it에서 IT 채용공고를 검색합니다.")
async def search_zighang_jobs(
    keyword: Annotated[Optional[str], "검색 키워드"] = None,
    limit: Annotated[int, "결과 개수"] = 20,
    page: Annotated[int, "페이지 번호 (1부터 시작)"] = 1,
) -> dict:
    """zighang.com/it IT 채용 공고를 검색합니다."""
    from .scrapers import zighang
    result = await zighang.search_jobs(keyword=keyword, limit=limit, page=page)
    return _format_result(result)


@mcp.tool(description="카카오(careers.kakao.com) 채용공고를 검색합니다.")
async def search_kakao_jobs(
    keyword: Annotated[Optional[str], "검색 키워드"] = None,
    limit: Annotated[int, "결과 개수"] = 20,
) -> dict:
    """카카오 채용 공고를 검색합니다."""
    from .scrapers import kakao
    result = await kakao.search_jobs(keyword=keyword, limit=limit)
    return _format_result(result)


@mcp.tool(description="네이버(recruit.naver.com) 채용공고를 검색합니다.")
async def search_naver_jobs(
    keyword: Annotated[Optional[str], "검색 키워드"] = None,
    limit: Annotated[int, "결과 개수"] = 20,
) -> dict:
    """네이버 채용 공고를 검색합니다."""
    from .scrapers import naver
    result = await naver.search_jobs(keyword=keyword, limit=limit)
    return _format_result(result)


@mcp.tool(description="삼성(samsungcareers.com) 채용공고를 검색합니다.")
async def search_samsung_jobs(
    keyword: Annotated[Optional[str], "검색 키워드"] = None,
    subsidiary: Annotated[Optional[str], "계열사 (삼성전자/삼성SDS/삼성리서치/삼성반도체)"] = None,
    limit: Annotated[int, "결과 개수"] = 20,
) -> dict:
    """삼성 계열사 채용 공고를 검색합니다."""
    from .scrapers import samsung
    result = await samsung.search_jobs(keyword=keyword, subsidiary=subsidiary, limit=limit)
    return _format_result(result)


@mcp.tool(description="대기업/IT기업 채용공고를 검색합니다. 지원 기업: LG, 현대, SK하이닉스, 쿠팡, 라인, 크래프톤, 엔씨소프트, 넥슨, 카카오뱅크, 토스, 당근마켓")
async def search_company_jobs(
    company: Annotated[
        str,
        "기업 키 (lg/hyundai/sk/coupang/line/krafton/ncsoft/nexon/kakaobank/toss/당근)",
    ],
    keyword: Annotated[Optional[str], "검색 키워드"] = None,
    limit: Annotated[int, "결과 개수"] = 20,
) -> dict:
    """특정 기업의 채용 공고를 검색합니다."""
    from .scrapers import conglomerate
    result = await conglomerate.search_company_jobs(
        company_key=company, keyword=keyword, limit=limit
    )
    return _format_result(result)


@mcp.tool(description="여러 한국 대기업/IT기업에서 동시에 채용공고를 검색합니다.")
async def search_all_companies(
    keyword: Annotated[Optional[str], "검색 키워드"] = None,
    companies: Annotated[
        Optional[list[str]],
        "검색할 기업 키 목록. None이면 전체 기업 검색 (lg/hyundai/sk/coupang/line/krafton/ncsoft/nexon/kakaobank/toss/당근)",
    ] = None,
    limit_per_company: Annotated[int, "기업당 최대 결과 개수"] = 5,
) -> dict:
    """지원하는 모든 대기업/IT기업 채용공고를 병렬로 검색합니다."""
    from .scrapers import conglomerate
    result = await conglomerate.search_all_companies(
        keyword=keyword,
        company_keys=companies,
        limit_per_company=limit_per_company,
    )
    return _format_result(result)


@mcp.tool(description="원티드 + zighang + 카카오 + 네이버를 통합 검색합니다.")
async def search_all_jobs(
    keyword: Annotated[Optional[str], "검색 키워드"] = None,
    sources: Annotated[
        Optional[list[str]],
        "검색할 소스 목록 (wanted/zighang/kakao/naver/samsung). None이면 전체 검색",
    ] = None,
    limit: Annotated[int, "소스당 최대 결과 개수"] = 10,
) -> dict:
    """여러 채용 플랫폼에서 동시에 채용공고를 검색합니다."""
    from .scrapers import wanted, zighang, kakao, naver, samsung

    active_sources = sources or ["wanted", "zighang", "kakao", "naver"]

    tasks = []
    source_names = []

    if "wanted" in active_sources:
        tasks.append(wanted.search_jobs(keyword=keyword, limit=limit))
        source_names.append("wanted")
    if "zighang" in active_sources:
        tasks.append(zighang.search_jobs(keyword=keyword, limit=limit))
        source_names.append("zighang")
    if "kakao" in active_sources:
        tasks.append(kakao.search_jobs(keyword=keyword, limit=limit))
        source_names.append("kakao")
    if "naver" in active_sources:
        tasks.append(naver.search_jobs(keyword=keyword, limit=limit))
        source_names.append("naver")
    if "samsung" in active_sources:
        tasks.append(samsung.search_jobs(keyword=keyword, limit=limit))
        source_names.append("samsung")

    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_jobs = []
    source_summary = {}
    for name, result in zip(source_names, results):
        if isinstance(result, SearchResult):
            all_jobs.extend(result.jobs)
            source_summary[name] = len(result.jobs)
        else:
            source_summary[name] = 0

    return {
        "total": len(all_jobs),
        "source_summary": source_summary,
        "keyword": keyword,
        "jobs": [j.model_dump(exclude_none=True) for j in all_jobs],
    }


@mcp.tool(description="지원하는 기업 목록을 조회합니다.")
async def list_supported_companies() -> dict:
    """한국 채용 MCP가 지원하는 기업 목록을 반환합니다."""
    from .scrapers import conglomerate
    companies = await conglomerate.list_companies()
    return {
        "platforms": {
            "원티드": "wanted.co.kr - 스타트업/중견기업 채용 플랫폼",
            "직장인": "zighang.com/it - IT 전문 채용",
        },
        "companies": companies,
        "usage": {
            "통합검색": "search_all_jobs(keyword='백엔드')",
            "원티드": "search_wanted_jobs(keyword='Python', job_category='백엔드')",
            "특정기업": "search_company_jobs(company='toss', keyword='개발')",
        },
    }


def _format_result(result: SearchResult) -> dict:
    return {
        "total": result.total,
        "source": result.source,
        "keyword": result.keyword,
        "jobs": [j.model_dump(exclude_none=True) for j in result.jobs],
    }
