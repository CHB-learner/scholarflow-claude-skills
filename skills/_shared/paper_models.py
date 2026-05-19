from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Paper:
    title: str
    authors: list[str] = field(default_factory=list)
    year: int | None = None
    venue: str | None = None
    abstract: str | None = None
    doi: str | None = None
    arxiv_id: str | None = None
    openreview_id: str | None = None
    url: str | None = None
    pdf_url: str | None = None
    citation_count: int | None = None
    source: str = "unknown"
    sources: list[str] = field(default_factory=list)
    code_url: str | None = None
    rank_score: float = 0.0
    raw: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.title = _metadata_text(self.title)
        self.authors = [_metadata_text(author) for author in self.authors if _metadata_text(author)]
        self.venue = _metadata_text(self.venue) or None
        self.abstract = _metadata_text(self.abstract) or None
        self.doi = _metadata_text(self.doi) or None
        self.arxiv_id = _metadata_text(self.arxiv_id) or None
        self.openreview_id = _metadata_text(self.openreview_id) or None
        self.url = _metadata_text(self.url) or None
        self.pdf_url = _metadata_text(self.pdf_url) or None
        self.source = _metadata_text(self.source) or "unknown"
        self.sources = sorted(set(_metadata_text(source) for source in (self.sources or [self.source]) if _metadata_text(source)))
        self.code_url = _metadata_text(self.code_url) or None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["sources"] = sorted(set(self.sources or [self.source]))
        return data


@dataclass
class SearchPlan:
    topic: str
    queries: list[str]
    since_year: int | None
    max_results: int
    sources: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ResearchProtocol:
    topic: str
    inclusion_criteria: list[str] = field(default_factory=list)
    exclusion_criteria: list[str] = field(default_factory=list)
    negative_keywords: list[str] = field(default_factory=list)
    search_sources: list[str] = field(default_factory=list)
    since_year: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class InclusionDecision:
    label: str
    score: float
    reason: str
    matched_terms: list[str] = field(default_factory=list)
    negative_hits: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _metadata_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return " ".join(value.split())
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, dict):
        for key in ("display_name", "name", "title", "value", "text"):
            if value.get(key):
                return _metadata_text(value.get(key))
        return " ".join(_metadata_text(item) for item in value.values() if _metadata_text(item)).strip()
    if isinstance(value, (list, tuple, set)):
        return ", ".join(_metadata_text(item) for item in value if _metadata_text(item)).strip()
    return str(value).strip()
