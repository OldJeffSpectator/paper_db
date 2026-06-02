from pydantic import BaseModel
from typing import Optional, List, Dict


class PaperCreate(BaseModel):
    title: str
    year: Optional[int] = None
    labels: str = ""
    ref_count: int = 0
    cited_by_count: int = 0
    abstract: str = ""
    authors: str = ""
    paper_link: str = ""
    citations: Dict[str, str] = {}  # {"APA": "...", "IEEE": "...", ...}


class PaperUpdate(BaseModel):
    title: Optional[str] = None
    year: Optional[int] = None
    labels: Optional[str] = None
    ref_count: Optional[int] = None
    cited_by_count: Optional[int] = None
    abstract: Optional[str] = None
    authors: Optional[str] = None
    paper_link: Optional[str] = None
    citations: Optional[Dict[str, str]] = None


class QueryRequest(BaseModel):
    sql: str


class ReferenceParseRequest(BaseModel):
    source_paper_id: int
    text: str


class ReferenceBatchInsert(BaseModel):
    source_paper_id: int
    references: List[dict]  # [{"raw_citation_text": "...", "referenced_paper_title": "...", "referenced_paper_id": ...}, ...]
