# 🇰🇷 Korean Job MCP

한국 채용 정보를 AI 어시스턴트(Claude, Cursor 등)에서 바로 조회할 수 있는 MCP(Model Context Protocol) 서버입니다.

**인증 없이 무료로 사용 가능합니다.**

## 지원 소스

| 플랫폼 | 설명 | 상태 |
|--------|------|------|
| **원티드** | wanted.co.kr - 스타트업/중견기업 채용 | ✅ 동작 |
| **직행 (zighang)** | zighang.com/it - IT 전문 채용 (11만개+) | ✅ 동작 |
| **카카오** | careers.kakao.com - 카카오 계열사 채용 | ✅ 동작 |
| **네이버** | recruit.naver.com - 네이버 채용 | 🔧 개선 중 |
| **삼성** | samsungcareers.com - 삼성 계열사 채용 | 🔧 개선 중 |
| **토스/당근/쿠팡 등** | 주요 IT 기업 채용 | 🔧 개선 중 |

## 설치

### 요구사항
- Python 3.12+
- [uv](https://github.com/astral-sh/uv) 패키지 매니저

```bash
# uv 설치
curl -LsSf https://astral.sh/uv/install.sh | sh

# 저장소 클론
git clone https://github.com/Hwan3434/korean-job-mcp.git
cd korean-job-mcp

# 의존성 설치
uv sync

# Playwright 브라우저 설치
uv run playwright install chromium
```

## Claude Desktop 연동

`~/Library/Application Support/Claude/claude_desktop_config.json`에 추가:

```json
{
  "mcpServers": {
    "korean-job-mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "/절대경로/korean-job-mcp",
        "run",
        "korean-job-mcp"
      ]
    }
  }
}
```

## Cursor 연동

`.cursor/mcp.json`에 추가:

```json
{
  "mcpServers": {
    "korean-job-mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "/절대경로/korean-job-mcp",
        "run",
        "korean-job-mcp"
      ]
    }
  }
}
```

## MCP 툴 목록

| 툴 이름 | 설명 |
|---------|------|
| `search_all_jobs` | 원티드 + zighang + 카카오 + 네이버 통합 검색 |
| `search_wanted_jobs` | 원티드 채용 검색 (직군/지역/경력 필터) |
| `get_wanted_job_detail` | 원티드 채용공고 상세 조회 |
| `search_zighang_jobs` | zighang IT 채용 검색 (직군 카테고리 필터) |
| `search_kakao_jobs` | 카카오 계열사 채용 검색 |
| `search_naver_jobs` | 네이버 채용 검색 |
| `search_samsung_jobs` | 삼성 계열사 채용 검색 |
| `search_company_jobs` | 개별 기업 채용 검색 (토스/당근/쿠팡 등) |
| `search_all_companies` | 여러 기업 동시 병렬 검색 |
| `list_supported_companies` | 지원 기업 목록 조회 |

## 사용 예시

Claude에게 이렇게 질문해보세요:

```
"백엔드 개발자 채용공고 원티드랑 zighang에서 찾아줘"
"카카오 개발자 채용 현황 알려줘"
"서울에서 Python 개발자 채용 5개 찾아줘"
"토스, 당근마켓, 쿠팡 채용 비교해줘"
```

## 응답 형식

```json
{
  "total": 1194,
  "source": "zighang",
  "keyword": "백엔드",
  "jobs": [
    {
      "id": "abc-123",
      "title": "백엔드 개발자 (Backend Engineer)",
      "company": "스타트업",
      "location": "서울",
      "url": "https://zighang.com/recruitment/abc-123",
      "posted_date": "2026-06-01",
      "experience": "3~7년",
      "tech_stack": ["Java", "Spring", "AWS"],
      "source": "zighang"
    }
  ]
}
```

## 캐싱

각 요청 결과는 **30분간 메모리 캐시**됩니다. 서버 재시작 시 초기화.

## 개발 / 테스트

```bash
# FastMCP 개발 모드 (MCP Inspector 연동)
uv run fastmcp dev src/korean_job_mcp/server.py

# 직접 테스트
uv run python -c "
import asyncio
from korean_job_mcp.scrapers import wanted
result = asyncio.run(wanted.search_jobs(keyword='백엔드', limit=5))
for j in result.jobs:
    print(j.title, j.company)
"
```

## 기여

PR과 이슈 환영합니다!

## 라이선스

MIT
