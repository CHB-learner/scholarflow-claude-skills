from __future__ import annotations

import datetime as dt
import html
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable

from paper_models import Paper, SearchPlan


Searcher = Callable[[str, int, int | None], list[Paper]]

DEFAULT_SOURCES = [
    "arxiv",
    "semantic_scholar",
    "openalex",
    "crossref",
    "openreview",
    "pubmed",
    "europe_pmc",
    "biorxiv",
    "medrxiv",
]


def search_all_with_diagnostics(
    plan: SearchPlan,
    per_query_limit: int = 10,
    *,
    sources: list[str] | None = None,
    registry: dict[str, Searcher] | None = None,
) -> tuple[list[Paper], dict]:
    registry = registry or SOURCE_REGISTRY
    source_names = _resolve_sources(sources, registry)
    diagnostics = {
        "enabled_sources": source_names,
        "queries": list(plan.queries),
        "total_returned": 0,
        "sources": {
            source: {
                "status": "pending",
                "queries": 0,
                "returned": 0,
                "errors": [],
            }
            for source in source_names
        },
    }
    papers: list[Paper] = []
    futures = {}
    with ThreadPoolExecutor(max_workers=min(8, max(1, len(source_names) * max(1, len(plan.queries))))) as executor:
        for query in plan.queries:
            for source in source_names:
                diagnostics["sources"][source]["queries"] += 1
                futures[executor.submit(registry[source], query, per_query_limit, plan.since_year)] = source
        for future in as_completed(futures):
            source = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                diagnostics["sources"][source]["status"] = "error"
                diagnostics["sources"][source]["errors"].append(f"{type(exc).__name__}: {exc}")
                continue
            diagnostics["sources"][source]["status"] = "ok"
            diagnostics["sources"][source]["returned"] += len(result)
            papers.extend(result)
    diagnostics["total_returned"] = len(papers)
    return papers, diagnostics


def _resolve_sources(sources: list[str] | None, registry: dict[str, Searcher]) -> list[str]:
    if not sources or sources == ["auto"]:
        requested = DEFAULT_SOURCES
    else:
        requested = sources
    return [source for source in requested if source in registry]


def search_arxiv(query: str, limit: int, since_year: int | None) -> list[Paper]:
    search_query = f'all:"{query}"'
    if since_year:
        search_query += f" AND submittedDate:[{since_year}01010000 TO 999912312359]"
    url = "https://export.arxiv.org/api/query?" + _encode(
        {
            "search_query": search_query,
            "start": 0,
            "max_results": limit,
            "sortBy": "relevance",
            "sortOrder": "descending",
        }
    )
    text = _request_text(url)
    if not text:
        return []
    root = ET.fromstring(text)
    ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}
    papers: list[Paper] = []
    for entry in root.findall("atom:entry", ns):
        arxiv_url = _xml_text(entry, "atom:id", ns)
        arxiv_id = arxiv_url.rsplit("/", 1)[-1] if arxiv_url else None
        authors = [
            _compact(author.findtext("atom:name", default="", namespaces=ns))
            for author in entry.findall("atom:author", ns)
        ]
        pdf_url = None
        for link in entry.findall("atom:link", ns):
            if link.attrib.get("title") == "pdf":
                pdf_url = link.attrib.get("href")
        papers.append(
            Paper(
                title=_compact(_xml_text(entry, "atom:title", ns)),
                authors=[author for author in authors if author],
                year=_coerce_year(_xml_text(entry, "atom:published", ns), since_year),
                venue="arXiv",
                abstract=_compact(_xml_text(entry, "atom:summary", ns)),
                arxiv_id=arxiv_id,
                url=arxiv_url,
                pdf_url=pdf_url or (f"https://arxiv.org/pdf/{arxiv_id}" if arxiv_id else None),
                source="arxiv",
                sources=["arxiv"],
                raw={"query": query},
            )
        )
    return [paper for paper in papers if paper.title]


def search_semantic_scholar(query: str, limit: int, since_year: int | None) -> list[Paper]:
    fields = "title,authors,year,abstract,venue,citationCount,externalIds,url,openAccessPdf"
    url = "https://api.semanticscholar.org/graph/v1/paper/search?" + _encode(
        {"query": query, "limit": limit, "fields": fields, "year": f"{since_year}-" if since_year else None}
    )
    data = _request_json(url)
    papers = []
    for item in data.get("data", []) if isinstance(data, dict) else []:
        external = item.get("externalIds") or {}
        open_pdf = item.get("openAccessPdf") or {}
        papers.append(
            Paper(
                title=_compact(item.get("title")),
                authors=[author.get("name", "") for author in item.get("authors", []) if author.get("name")],
                year=_coerce_year(item.get("year"), since_year),
                venue=item.get("venue"),
                abstract=_compact(item.get("abstract")),
                doi=external.get("DOI"),
                arxiv_id=external.get("ArXiv"),
                url=item.get("url"),
                pdf_url=open_pdf.get("url"),
                citation_count=item.get("citationCount"),
                source="semantic_scholar",
                sources=["semantic_scholar"],
                raw={"query": query},
            )
        )
    return [paper for paper in papers if paper.title]


def search_openalex(query: str, limit: int, since_year: int | None) -> list[Paper]:
    filters = f"from_publication_date:{since_year}-01-01" if since_year else None
    url = "https://api.openalex.org/works?" + _encode(
        {"search": query, "per-page": limit, "filter": filters}
    )
    data = _request_json(url)
    papers = []
    for item in data.get("results", []) if isinstance(data, dict) else []:
        doi = item.get("doi")
        if doi and doi.startswith("https://doi.org/"):
            doi = doi.removeprefix("https://doi.org/")
        authors = [
            (auth.get("author") or {}).get("display_name")
            for auth in item.get("authorships", [])
            if (auth.get("author") or {}).get("display_name")
        ]
        papers.append(
            Paper(
                title=_compact(item.get("display_name")),
                authors=authors,
                year=_coerce_year(item.get("publication_year"), since_year),
                venue=((item.get("primary_location") or {}).get("source") or {}).get("display_name"),
                abstract=_openalex_abstract(item.get("abstract_inverted_index")),
                doi=doi,
                url=item.get("id"),
                pdf_url=(item.get("best_oa_location") or {}).get("pdf_url"),
                citation_count=item.get("cited_by_count"),
                source="openalex",
                sources=["openalex"],
                raw={"query": query},
            )
        )
    return [paper for paper in papers if paper.title]


def search_crossref(query: str, limit: int, since_year: int | None) -> list[Paper]:
    filters = f"from-pub-date:{since_year}" if since_year else None
    url = "https://api.crossref.org/works?" + _encode({"query": query, "rows": limit, "filter": filters})
    data = _request_json(url)
    items = ((data.get("message") or {}).get("items") or []) if isinstance(data, dict) else []
    papers = []
    for item in items:
        authors = []
        for author in item.get("author", []):
            name = " ".join(part for part in [author.get("given"), author.get("family")] if part)
            if name:
                authors.append(name)
        papers.append(
            Paper(
                title=_compact((item.get("title") or [""])[0]),
                authors=authors,
                year=_crossref_year(item, since_year),
                venue=(item.get("container-title") or [None])[0],
                abstract=_compact(re.sub("<[^>]+>", " ", item.get("abstract") or "")) or None,
                doi=item.get("DOI"),
                url=item.get("URL"),
                citation_count=item.get("is-referenced-by-count"),
                source="crossref",
                sources=["crossref"],
                raw={"query": query},
            )
        )
    return [paper for paper in papers if paper.title]


def search_openreview(query: str, limit: int, since_year: int | None) -> list[Paper]:
    url = "https://api2.openreview.net/notes/search?" + _encode({"term": query, "limit": limit})
    data = _request_json(url)
    papers = []
    for note in data.get("notes", []) if isinstance(data, dict) else []:
        content = note.get("content") or {}
        title = _content_value(content.get("title"))
        authors = _content_value(content.get("authors")) or []
        if isinstance(authors, str):
            authors = [authors]
        paper_id = note.get("id")
        year = _timestamp_year(note.get("cdate"), since_year)
        papers.append(
            Paper(
                title=_compact(title),
                authors=authors,
                year=year,
                venue=note.get("forum"),
                abstract=_compact(_content_value(content.get("abstract"))),
                openreview_id=paper_id,
                url=f"https://openreview.net/forum?id={paper_id}" if paper_id else None,
                pdf_url=f"https://openreview.net/pdf?id={paper_id}" if paper_id else None,
                source="openreview",
                sources=["openreview"],
                raw={"query": query},
            )
        )
    return [paper for paper in papers if paper.title]


def search_pubmed(query: str, limit: int, since_year: int | None) -> list[Paper]:
    term = f"({query}) AND {since_year}:3000[pdat]" if since_year else query
    url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?" + _encode(
        {"db": "pubmed", "term": term, "retmode": "json", "retmax": limit, "sort": "relevance"}
    )
    data = _request_json(url)
    ids = ((data.get("esearchresult") or {}).get("idlist") or []) if isinstance(data, dict) else []
    if not ids:
        return []
    fetch_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?" + _encode(
        {"db": "pubmed", "id": ",".join(ids), "retmode": "xml"}
    )
    text = _request_text(fetch_url)
    if not text:
        return []
    root = ET.fromstring(text)
    papers = []
    for article in root.findall(".//PubmedArticle"):
        pmid = _element_text(article, ".//PMID")
        doi = None
        pmcid = None
        for aid in article.findall(".//ArticleId"):
            if aid.attrib.get("IdType") == "doi":
                doi = aid.text
            if aid.attrib.get("IdType") == "pmc":
                pmcid = aid.text
        papers.append(
            Paper(
                title=_compact(_element_text(article, ".//ArticleTitle")),
                authors=_pubmed_authors(article),
                year=_pubmed_year(article, since_year),
                venue=_element_text(article, ".//Journal/Title") or _element_text(article, ".//ISOAbbreviation"),
                abstract=_compact(" ".join(node.text or "" for node in article.findall(".//AbstractText"))) or None,
                doi=doi,
                url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else None,
                source="pubmed",
                sources=["pubmed"],
                raw={"query": query, "identifiers": {"pmid": pmid, "pmcid": pmcid}},
            )
        )
    return [paper for paper in papers if paper.title]


def search_europe_pmc(query: str, limit: int, since_year: int | None) -> list[Paper]:
    europe_query = f"({query}) FIRST_PDATE:[{since_year}-01-01 TO 3000-12-31]" if since_year else query
    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search?" + _encode(
        {"query": europe_query, "format": "json", "pageSize": limit, "resultType": "core"}
    )
    data = _request_json(url)
    papers = []
    for item in (((data.get("resultList") or {}).get("result")) or []) if isinstance(data, dict) else []:
        pdf_url = None
        urls = ((item.get("fullTextUrlList") or {}).get("fullTextUrl") or []) if isinstance(item.get("fullTextUrlList"), dict) else []
        if urls:
            pdf_url = urls[0].get("url")
        papers.append(
            Paper(
                title=_compact(item.get("title")),
                authors=[a.strip() for a in (item.get("authorString") or "").rstrip(".").split(",") if a.strip()],
                year=_coerce_year(item.get("pubYear"), since_year),
                venue=item.get("journalTitle"),
                abstract=_compact(item.get("abstractText")),
                doi=item.get("doi"),
                url=item.get("doiUrl") or (f"https://europepmc.org/article/MED/{item.get('pmid')}" if item.get("pmid") else None),
                pdf_url=pdf_url,
                source="europe_pmc",
                sources=["europe_pmc"],
                raw={"query": query, "identifiers": {"pmid": item.get("pmid"), "pmcid": item.get("pmcid")}},
            )
        )
    return [paper for paper in papers if paper.title]


def search_biorxiv(query: str, limit: int, since_year: int | None) -> list[Paper]:
    return _search_bio_med_rxiv("biorxiv", query, limit, since_year)


def search_medrxiv(query: str, limit: int, since_year: int | None) -> list[Paper]:
    return _search_bio_med_rxiv("medrxiv", query, limit, since_year)


def _search_bio_med_rxiv(server: str, query: str, limit: int, since_year: int | None) -> list[Paper]:
    start = f"{since_year or dt.date.today().year - 2}-01-01"
    end = dt.date.today().isoformat()
    url = f"https://api.biorxiv.org/details/{server}/{start}/{end}/0"
    data = _request_json(url)
    papers = []
    terms = [term.lower() for term in re.findall(r"[a-zA-Z0-9]+", query) if len(term) > 2]
    for item in data.get("collection", []) if isinstance(data, dict) else []:
        text = " ".join([item.get("title", ""), item.get("abstract", "")]).lower()
        if terms and not any(term in text for term in terms):
            continue
        doi = item.get("doi")
        papers.append(
            Paper(
                title=_compact(item.get("title")),
                authors=[a.strip() for a in (item.get("authors") or "").split(";") if a.strip()],
                year=_coerce_year(item.get("date"), since_year),
                venue=server,
                abstract=_compact(item.get("abstract")),
                doi=doi,
                url=f"https://www.{server}.org/content/{doi}" if doi else None,
                pdf_url=f"https://www.{server}.org/content/{doi}.full.pdf" if doi else None,
                source=server,
                sources=[server],
                raw={"query": query},
            )
        )
        if len(papers) >= limit:
            break
    return papers


SOURCE_REGISTRY: dict[str, Searcher] = {
    "arxiv": search_arxiv,
    "semantic_scholar": search_semantic_scholar,
    "openalex": search_openalex,
    "crossref": search_crossref,
    "openreview": search_openreview,
    "pubmed": search_pubmed,
    "europe_pmc": search_europe_pmc,
    "biorxiv": search_biorxiv,
    "medrxiv": search_medrxiv,
}


def _request_text(url: str, timeout: int = 20) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "claude-paper-skills/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _encode(params: dict) -> str:
    return urllib.parse.urlencode({key: value for key, value in params.items() if value is not None})


def _request_json(url: str, timeout: int = 20) -> dict:
    text = _request_text(url, timeout=timeout)
    return json.loads(text) if text else {}


def _compact(value) -> str:
    if value is None:
        return ""
    value = html.unescape(str(value))
    return re.sub(r"\s+", " ", value).strip()


def _xml_text(node, path: str, ns: dict[str, str]) -> str:
    child = node.find(path, ns)
    return child.text or "" if child is not None else ""


def _element_text(node, path: str) -> str:
    if node is None:
        return ""
    child = node.find(path)
    return child.text or "" if child is not None else ""


def _coerce_year(value, since_year: int | None) -> int | None:
    if value is None:
        return None
    match = re.search(r"(19|20)\d{2}", str(value))
    if not match:
        return None
    year = int(match.group(0))
    current = dt.date.today().year
    if year > current + 1 or year < 1500:
        return None
    if since_year and year < since_year:
        return None
    return year


def _crossref_year(item: dict, since_year: int | None) -> int | None:
    for key in ("published-print", "published-online", "created", "issued"):
        parts = ((item.get(key) or {}).get("date-parts") or [[]])[0]
        if parts:
            return _coerce_year(parts[0], since_year)
    return None


def _timestamp_year(value, since_year: int | None) -> int | None:
    try:
        return _coerce_year(dt.datetime.fromtimestamp(float(value) / 1000).year, since_year)
    except (TypeError, ValueError, OSError, OverflowError):
        return None


def _content_value(value):
    if isinstance(value, dict):
        return value.get("value")
    return value


def _openalex_abstract(index: dict | None) -> str | None:
    if not isinstance(index, dict):
        return None
    words: list[tuple[int, str]] = []
    for word, positions in index.items():
        for position in positions:
            words.append((position, word))
    return " ".join(word for _, word in sorted(words))


def _pubmed_authors(article) -> list[str]:
    authors = []
    for author in article.findall(".//Author"):
        name = " ".join(part for part in [_element_text(author, "ForeName"), _element_text(author, "LastName")] if part)
        if name:
            authors.append(name)
    return authors


def _pubmed_year(article, since_year: int | None) -> int | None:
    for path in (".//ArticleDate/Year", ".//PubDate/Year", ".//DateCompleted/Year"):
        year = _coerce_year(_element_text(article, path), since_year)
        if year:
            return year
    return None
