from __future__ import annotations
from typing import Optional
from pydantic import BaseModel


class JobListing(BaseModel):
    id: Optional[str] = None
    title: str
    company: str
    location: Optional[str] = None
    description: Optional[str] = None
    url: str
    posted_date: Optional[str] = None
    deadline: Optional[str] = None
    requirements: Optional[list[str]] = None
    tech_stack: Optional[list[str]] = None
    salary: Optional[str] = None
    job_type: Optional[str] = None
    experience: Optional[str] = None
    source: str  # wanted / zighang / kakao / naver / samsung / etc.
    reward: Optional[str] = None


class SearchResult(BaseModel):
    total: int
    jobs: list[JobListing]
    source: str
    keyword: Optional[str] = None
