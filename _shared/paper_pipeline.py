from __future__ import annotations

import datetime as dt
import math
import re
from collections import Counter
from difflib import SequenceMatcher

from paper_models import Paper


CODE_URL_RE = re.compile(r"https?://(?:www\.)?(?:github\.com|gitlab\.com|huggingface\.co)/[^\s)\]}>\"']+", re.I)


def normalize_title(title: str) -> str:
    text = re.sub(r"<[^>]+>", " ", title or "")
    text = text.lower()
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def dedup_keys(paper: Paper) -> list[str]:
    keys: list[str] = []
    if paper.doi:
        keys.append("doi:" + paper.doi.lower())
    if paper.arxiv_id:
        keys.append("arxiv:" + _strip_arxiv_version(paper.arxiv_id.lower()))
    if paper.openreview_id:
        keys.append("openreview:" + paper.openreview_id.lower())
    identifiers = (paper.raw or {}).get("identifiers") or {}
    for key in ("pmid", "pmcid"):
        if identifiers.get(key):
            keys.append(f"{key}:{str(identifiers[key]).lower()}")
    normalized = normalize_title(paper.title)
    if normalized:
        keys.append("title:" + normalized)
    return list(dict.fromkeys(keys)) or [f"object:{id(paper)}"]


def deduplicate_papers(papers: list[Paper]) -> tuple[list[Paper], dict]:
    merged: list[Paper] = []
    key_index: dict[str, Paper] = {}
    identifier_merges = 0
    title_merges = 0

    for paper in papers:
        keys = dedup_keys(paper)
        match = next((key_index[key] for key in keys if key in key_index), None)
        if match:
            identifier_merges += 1
            _merge_paper(match, paper)
        else:
            match = _find_title_match(merged, paper)
            if match:
                title_merges += 1
                _merge_paper(match, paper)
            else:
                paper.sources = sorted(set(paper.sources or [paper.source]))
                merged.append(paper)
                match = paper
        for key in dedup_keys(match) + keys:
            key_index[key] = match

    stats = {
        "raw_count": len(papers),
        "after_identifier_dedup": len(papers) - identifier_merges,
        "after_title_similarity_dedup": len(merged),
        "identifier_merges": identifier_merges,
        "title_similarity_merges": title_merges,
    }
    return merged, stats


def rank_papers(papers: list[Paper], topic: str, since_year: int | None) -> list[Paper]:
    terms = _terms(topic)
    current_year = dt.date.today().year
    for paper in papers:
        text = " ".join([paper.title or "", paper.abstract or "", paper.venue or ""]).lower()
        term_hits = sum(1 for term in terms if term in text)
        relevance = term_hits / max(1, len(terms))
        year = _coerce_year(paper.year)
        if year != paper.year:
            paper.year = year
        recency = 0.0
        if year:
            recency = max(0.0, 1.0 - min(10, current_year - year) / 10)
        citations = math.log1p(paper.citation_count or 0) / 10
        pdf_bonus = 0.1 if paper.pdf_url else 0.0
        code_bonus = 0.1 if paper.code_url else 0.0
        source_bonus = min(0.12, 0.03 * max(0, len(set(paper.sources or [paper.source])) - 1))
        paper.rank_score = round(relevance * 2 + recency + citations + pdf_bonus + code_bonus + source_bonus, 4)
    return sorted(papers, key=lambda p: (p.rank_score, p.year or 0, p.title), reverse=True)


def resolve_code_links(papers: list[Paper]) -> list[Paper]:
    for paper in papers:
        if paper.code_url:
            continue
        haystack = "\n".join([paper.title or "", paper.abstract or "", paper.url or "", paper.pdf_url or ""])
        match = CODE_URL_RE.search(haystack)
        if match:
            paper.code_url = match.group(0).rstrip(".,;")
    return papers


def _find_title_match(existing: list[Paper], paper: Paper) -> Paper | None:
    normalized = normalize_title(paper.title)
    if not normalized:
        return None
    for candidate in existing:
        candidate_title = normalize_title(candidate.title)
        if not candidate_title:
            continue
        if normalized == candidate_title:
            return candidate
        ratio = SequenceMatcher(None, normalized, candidate_title).ratio()
        years_close = not paper.year or not candidate.year or abs(paper.year - candidate.year) <= 1
        author_overlap = bool(set(_author_last_names(paper)) & set(_author_last_names(candidate)))
        if ratio >= 0.93 and (years_close or author_overlap):
            return candidate
    return None


def _merge_paper(current: Paper, incoming: Paper) -> None:
    current.sources = sorted(set((current.sources or [current.source]) + (incoming.sources or [incoming.source]) + [incoming.source]))
    for field in ("abstract", "doi", "arxiv_id", "openreview_id", "url", "pdf_url", "venue", "code_url"):
        if not getattr(current, field) and getattr(incoming, field):
            setattr(current, field, getattr(incoming, field))
    if incoming.citation_count and (not current.citation_count or incoming.citation_count > current.citation_count):
        current.citation_count = incoming.citation_count
    if incoming.year and (not current.year or incoming.year > current.year):
        current.year = incoming.year
    if len(incoming.authors) > len(current.authors):
        current.authors = incoming.authors
    current.raw.setdefault("identifiers", {}).update((incoming.raw or {}).get("identifiers") or {})


def _strip_arxiv_version(arxiv_id: str) -> str:
    return re.sub(r"v\d+$", "", arxiv_id)


def _author_last_names(paper: Paper) -> list[str]:
    result = []
    for author in paper.authors:
        parts = re.findall(r"[A-Za-z]+", author.lower())
        if parts:
            result.append(parts[-1])
    return result


def _terms(topic: str) -> list[str]:
    tokens = re.findall(r"[a-zA-Z0-9\u4e00-\u9fff]+", topic.lower())
    counts = Counter(token for token in tokens if len(token) > 1)
    return list(counts) or [topic.lower()]


def _coerce_year(value) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    text = str(value)
    match = re.search(r"(19|20)\d{2}", text)
    if not match:
        return None
    year = int(match.group(0))
    current = dt.date.today().year
    if 1500 <= year <= current + 1:
        return year
    return None
