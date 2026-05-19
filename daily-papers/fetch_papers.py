#!/usr/bin/env python3
"""
fetch_papers.py — Broad search for papers, keyword-filtered.

Usage:
    python3 fetch_papers.py --field "RNA序列设计" --keywords "RNA design,mRNA,ribozyme" --days 60

Output: JSON array of fetched papers matching keywords.
If --download-pdfs is set, also downloads PDFs to --pdf-dir.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from glob import glob
from pathlib import Path
from urllib.request import Request, urlopen

ATOM_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
}

ARXIV_COLLECTOR_PATH = "/tmp/arxiv_collector"

# ── URL Fetching with Retry ───────────────────────────────────────────────────


def fetch_url(url: str, timeout: int = 30, retries: int = 3, backoff: float = 5.0) -> str:
    for attempt in range(retries):
        try:
            req = Request(url, headers={"User-Agent": "daily-papers-bot/1.0 (research paper aggregator)"})
            with urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8")
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "Too Many Requests" in err_str:
                wait = backoff * (2 ** attempt)
                print(f"  [WARN] Rate limited, retrying in {wait:.0f}s... (attempt {attempt+1}/{retries})", file=sys.stderr)
                time.sleep(wait)
                continue
            print(f"  [WARN] fetch failed {url}: {e}", file=sys.stderr)
            return ""
    print(f"  [WARN] all retries exhausted for {url}", file=sys.stderr)
    return ""


def fetch_bytes(url: str, timeout: int = 60, retries: int = 3, backoff: float = 5.0) -> bytes:
    for attempt in range(retries):
        try:
            req = Request(url, headers={"User-Agent": "daily-papers-bot/1.0 (research paper aggregator)"})
            with urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "Too Many Requests" in err_str:
                wait = backoff * (2 ** attempt)
                print(f"  [WARN] Rate limited, retrying in {wait:.0f}s... (attempt {attempt+1}/{retries})", file=sys.stderr)
                time.sleep(wait)
                continue
            print(f"  [WARN] binary fetch failed {url}: {e}", file=sys.stderr)
            return b""
    print(f"  [WARN] all retries exhausted for {url}", file=sys.stderr)
    return b""


# ── Keyword Filtering ─────────────────────────────────────────────────────────


def paper_matches_keywords(paper: dict, keywords: list[str]) -> bool:
    """Check if paper title or abstract matches any keyword (case-insensitive)."""
    text = (paper.get("title", "") + " " + paper.get("abstract", "")).lower()
    for kw in keywords:
        if kw.lower() in text:
            return True
    return False


# ── HuggingFace Fetching ─────────────────────────────────────────────────────


def fetch_hf_papers(keywords: list[str], days: int = 60) -> list[dict]:
    """Fetch HF daily papers for the past N days + trending, filtered by keywords."""
    all_papers = {}

    today = datetime.now().date()

    for d in range(days):
        date = today - timedelta(days=d)
        endpoint = f"https://huggingface.co/api/daily_papers?date={date.isoformat()}&limit=100"
        print(f"  Fetching hf-daily {date.isoformat()}...", file=sys.stderr)
        raw = fetch_url(endpoint)
        if raw:
            try:
                items = json.loads(raw)
            except json.JSONDecodeError:
                items = []
            for item in items:
                p = item.get("paper", {})
                arxiv_id = p.get("id", "")
                if not arxiv_id:
                    continue
                authors_raw = p.get("authors", [])
                if isinstance(authors_raw, list):
                    names = [a.get("name", "") if isinstance(a, dict) else str(a) for a in authors_raw]
                    authors = ", ".join(n for n in names if n)
                else:
                    authors = str(authors_raw)
                paper = {
                    "title": p.get("title", ""),
                    "authors": authors,
                    "affiliations": "",
                    "abstract": p.get("summary", ""),
                    "url": f"https://arxiv.org/abs/{arxiv_id}",
                    "pdf": f"https://arxiv.org/pdf/{arxiv_id}",
                    "date": (p.get("publishedAt") or "")[:10],
                    "source": "hf-daily",
                    "hf_upvotes": p.get("upvotes", 0) or 0,
                }
                if paper_matches_keywords(paper, keywords):
                    all_papers[arxiv_id] = paper

    endpoint = "https://huggingface.co/api/daily_papers?sort=trending&limit=100"
    print(f"  Fetching hf-trending...", file=sys.stderr)
    raw = fetch_url(endpoint)
    if raw:
        try:
            items = json.loads(raw)
        except json.JSONDecodeError:
            items = []
        for item in items:
            p = item.get("paper", {})
            arxiv_id = p.get("id", "")
            if not arxiv_id or arxiv_id in all_papers:
                continue
            authors_raw = p.get("authors", [])
            if isinstance(authors_raw, list):
                names = [a.get("name", "") if isinstance(a, dict) else str(a) for a in authors_raw]
                authors = ", ".join(n for n in names if n)
            else:
                authors = str(authors_raw)
            paper = {
                "title": p.get("title", ""),
                "authors": authors,
                "affiliations": "",
                "abstract": p.get("summary", ""),
                "url": f"https://arxiv.org/abs/{arxiv_id}",
                "pdf": f"https://arxiv.org/pdf/{arxiv_id}",
                "date": (p.get("publishedAt") or "")[:10],
                "source": "hf-trending",
                "hf_upvotes": p.get("upvotes", 0) or 0,
            }
            if paper_matches_keywords(paper, keywords):
                all_papers[arxiv_id] = paper

    print(f"  HF (keyword-filtered): {len(all_papers)} papers", file=sys.stderr)
    return list(all_papers.values())


# ── Arxiv-Paper-Collector ─────────────────────────────────────────────────────


def run_arxiv_collector(keywords: list[str], days: int = 60, max_results: int = 300) -> list[dict]:
    """Run Arxiv-Paper-Collector to fetch papers, returns list of paper dicts."""
    import shutil
    # Check if collector is available
    collector_dir = Path(ARXIV_COLLECTOR_PATH)
    if not collector_dir.exists():
        print(f"  [WARN] Arxiv-Paper-Collector not found at {ARXIV_COLLECTOR_PATH}, skipping", file=sys.stderr)
        return []

    # Use temp dir for output
    temp_dir = tempfile.mkdtemp(prefix="arxiv_collector_")
    original_cwd = Path.cwd()

    try:
        # Change to collector dir
        os.chdir(collector_dir)

        # Build command - search across relevant CS categories
        categories = "cs.AI,cs.CV,cs.CL,cs.LG"
        keyword_str = ",".join(keywords[:5])  # limit to 5 keywords

        cmd = [
            sys.executable, "main.py",
            "--categories", categories,
            "--days", str(days),
            "--keywords", keyword_str,
            "--search-fields", "title,abstract",
            "--limit", str(max_results),
            "--log-level", "WARNING",
            "--batch", "False"
        ]

        print(f"  Running Arxiv-Paper-Collector: {' '.join(cmd)}", file=sys.stderr)

        result = subprocess.run(
            cmd,
            cwd=str(collector_dir),
            capture_output=True,
            text=True,
            timeout=600
        )

        if result.returncode != 0:
            print(f"  [WARN] Arxiv-Paper-Collector failed: {result.stderr[:200]}", file=sys.stderr)
            return []

        # Find JSONL output files
        jsonl_files = glob(str(collector_dir / "data" / "metadata" / "**" / "*.jsonl"), recursive=True)
        print(f"  Found {len(jsonl_files)} JSONL files", file=sys.stderr)

        papers = []
        for jsonl_file in jsonl_files:
            try:
                with open(jsonl_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                            # Map to standard paper format
                            arxiv_id = entry.get("arxiv_id", "")
                            papers.append({
                                "title": entry.get("title", ""),
                                "authors": ", ".join(entry.get("authors", [])) if isinstance(entry.get("authors"), list) else entry.get("authors", ""),
                                "affiliations": "",
                                "abstract": entry.get("abstract", ""),
                                "url": f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else "",
                                "pdf": f"https://arxiv.org/pdf/{arxiv_id}" if arxiv_id else "",
                                "date": (entry.get("published", "") or "")[:10],
                                "category": entry.get("primary_category", ""),
                                "source": "arxiv",
                                "hf_upvotes": 0,
                            })
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                print(f"  [WARN] Error reading {jsonl_file}: {e}", file=sys.stderr)
                continue

        print(f"  Arxiv-Paper-Collector: {len(papers)} papers", file=sys.stderr)
        return papers

    except subprocess.TimeoutExpired:
        print(f"  [WARN] Arxiv-Paper-Collector timed out after 600s", file=sys.stderr)
        return []
    except Exception as e:
        print(f"  [WARN] Arxiv-Paper-Collector error: {e}", file=sys.stderr)
        return []
    finally:
        os.chdir(original_cwd)
        shutil.rmtree(temp_dir, ignore_errors=True)


# ── Legacy arXiv Fetching (fallback) ─────────────────────────────────────────

ARXIV_REQUEST_DELAY = 3.0


def fetch_arxiv_papers(keywords: list[str], days: int = 60, max_results: int = 300) -> list[dict]:
    """Fetch arXiv papers matching any of the keywords, with rate limiting."""
    keyword_queries = [f"all:{kw.replace(' ', '+')}" for kw in keywords]
    query = "+OR+".join(keyword_queries)

    url = (
        f"https://export.arxiv.org/api/query?"
        f"search_query=({query})"
        f"&sortBy=submittedDate&sortOrder=descending&max_results={max_results}"
    )

    timeout = 120
    print(f"  Fetching arXiv (keywords={keywords[:3]}..., max_results={max_results})...", file=sys.stderr)
    xml_text = fetch_url(url, timeout=timeout, retries=5, backoff=15.0)
    if not xml_text:
        print(f"  [WARN] arXiv fetch failed after retries", file=sys.stderr)
        return []

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        print(f"  [WARN] arXiv XML parse error: {e}", file=sys.stderr)
        return []

    papers = []
    today = datetime.now().date()
    start_date = today - timedelta(days=days)

    for entry in root.findall("atom:entry", ATOM_NS):
        title_el = entry.find("atom:title", ATOM_NS)
        summary_el = entry.find("atom:summary", ATOM_NS)
        published_el = entry.find("atom:published", ATOM_NS)
        id_el = entry.find("atom:id", ATOM_NS)

        if title_el is None or summary_el is None:
            continue

        title = " ".join(title_el.text.split())
        abstract = " ".join(summary_el.text.split())
        entry_url = id_el.text.strip() if id_el is not None else ""
        date = published_el.text[:10] if published_el is not None else ""
        arxiv_id = entry_url.split("/abs/")[-1] if "/abs/" in entry_url else ""

        if date:
            try:
                pub_date = datetime.strptime(date, "%Y-%m-%d").date()
                if pub_date < start_date:
                    continue
            except ValueError:
                pass

        author_els = entry.findall("atom:author", ATOM_NS)
        names = []
        affiliations = set()
        for a in author_els:
            name_el = a.find("atom:name", ATOM_NS)
            if name_el is not None and name_el.text:
                names.append(name_el.text.strip())
            for aff_el in a.findall("arxiv:affiliation", ATOM_NS):
                if aff_el.text and aff_el.text.strip():
                    affiliations.add(aff_el.text.strip())

        cat_el = entry.find("arxiv:primary_category", ATOM_NS)
        category = cat_el.get("term", "") if cat_el is not None else ""

        papers.append({
            "title": title,
            "authors": ", ".join(names),
            "affiliations": ", ".join(sorted(affiliations)) if affiliations else "",
            "abstract": abstract,
            "url": entry_url,
            "pdf": f"https://arxiv.org/pdf/{arxiv_id}" if arxiv_id else "",
            "date": date,
            "category": category,
            "source": "arxiv",
            "hf_upvotes": 0,
        })

    print(f"  arXiv: {len(papers)} papers", file=sys.stderr)
    return papers


# ── Deduplication ─────────────────────────────────────────────────────────────


def extract_arxiv_id(url: str) -> str:
    m = re.search(r"(\d{4}\.\d{4,5})", url)
    return m.group(1) if m else ""


def merge_papers(hf_papers: list[dict], arxiv_papers: list[dict]) -> list[dict]:
    """Merge HF and arXiv papers, dedup by arXiv ID."""
    by_id = {}
    for p in hf_papers + arxiv_papers:
        aid = extract_arxiv_id(p["url"])
        if not aid:
            continue
        if aid not in by_id:
            by_id[aid] = p

    print(f"  Merged: {len(by_id)} unique papers", file=sys.stderr)
    return list(by_id.values())


# ── Main ─────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--field", required=True, help="Research field name (e.g., 'RNA序列设计')")
    parser.add_argument("--keywords", required=True, help="Comma-separated keywords for search")
    parser.add_argument("--days", type=int, default=60, help="Number of days to search (default: 60)")
    parser.add_argument("--max-arxiv", type=int, default=300, help="Max arXiv results (default: 300)")
    parser.add_argument(
        "--download-pdfs",
        action="store_true",
        help="Download PDFs for all fetched papers to --pdf-dir"
    )
    parser.add_argument(
        "--pdf-dir",
        type=str, default="",
        help="Directory to save PDFs (required if --download-pdfs is set)"
    )
    args = parser.parse_args()

    keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]

    print(f"[fetch_papers] field={args.field}, keywords={keywords[:5]}..., days={args.days}", file=sys.stderr)

    hf_papers = fetch_hf_papers(keywords=keywords, days=args.days)

    print(f"  Cooldown before arXiv request (3s)...", file=sys.stderr)
    time.sleep(3.0)

    # Try Arxiv-Paper-Collector first, fallback to legacy
    arxiv_papers = run_arxiv_collector(keywords=keywords, days=args.days, max_results=args.max_arxiv)
    if not arxiv_papers:
        print(f"  [INFO] Falling back to legacy arXiv API", file=sys.stderr)
        arxiv_papers = fetch_arxiv_papers(keywords=keywords, days=args.days, max_results=args.max_arxiv)

    all_papers = merge_papers(hf_papers, arxiv_papers)

    all_papers.sort(key=lambda x: (x.get("date", ""), x.get("hf_upvotes", 0)), reverse=True)

    print(f"  Final: {len(all_papers)} papers (keyword-filtered)", file=sys.stderr)

    # Optional PDF download
    if args.download_pdfs and args.pdf_dir:
        import re as re2
        pdf_dir = Path(args.pdf_dir)
        pdf_dir.mkdir(parents=True, exist_ok=True)
        for i, paper in enumerate(all_papers):
            pdf_url = paper.get("pdf", "")
            if not pdf_url:
                continue
            m = re2.search(r"(\d{4}\.\d{4,5})", pdf_url)
            if not m:
                continue
            arxiv_id = m.group(1)
            pdf_path = pdf_dir / f"{arxiv_id}.pdf"
            if pdf_path.exists():
                print(f"  [{i+1}/{len(all_papers)}] SKIP (exists) {pdf_path.name}", file=sys.stderr)
                continue
            print(f"  [{i+1}/{len(all_papers)}] DOWNLOAD {arxiv_id}", file=sys.stderr)
            raw = fetch_bytes(pdf_url, timeout=60, retries=3, backoff=5.0)
            if raw:
                pdf_path.write_bytes(raw)
                print(f"  Saved: {pdf_path.name}", file=sys.stderr)
            time.sleep(1.0)

    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    json.dump(all_papers, sys.stdout, ensure_ascii=False, indent=2)
    print(file=sys.stdout)


if __name__ == "__main__":
    main()
