#!/usr/bin/env python3
"""
generate_research_field_mocs.py

为 Research_Fields 下的每个研究方向生成 summary.md 索引页。
同时兼容 vault 根目录下的 未分类/ 论文目录。
每个方向的 summary.md 记录该方向下所有已保存的论文。

目录结构:
Research_Fields/{方向}/
├── summary.md
└── papers/
    ├── {论文名}/
    │   ├── pngs/
    │   ├── {论文名}_en.md
    │   ├── {论文名}_zh.md
    │   └── {论文名}.pdf

Usage:
    python3 generate_research_field_mocs.py [vault_path]
"""

import re
import json
import sys
from pathlib import Path

# Add _shared to path for user_config
_SCRIPT_DIR = Path(__file__).resolve().parent
_SHARED_DIR = _SCRIPT_DIR.parent / "_shared"
if str(_SHARED_DIR) not in sys.path:
    sys.path.insert(0, str(_SHARED_DIR))

from user_config import paths_config, load_user_config


PAPER_LIST_START = "<!-- scholarflow:paper-list:start -->"
PAPER_LIST_END = "<!-- scholarflow:paper-list:end -->"
MAX_SUMMARY_PAPERS = 50

GITHUB_URL_RE = re.compile(r"https?://github\.com/[^\s\]\)>,;\"']+", re.IGNORECASE)
PROJECT_URL_RE = re.compile(
    r"https?://[^\s\]\)>,;\"']*(?:github\.io|pages\.dev|huggingface\.co/spaces)[^\s\]\)>,;\"']*",
    re.IGNORECASE,
)


def extract_arxiv_source(content: str) -> str:
    """Extract arXiv source URL from content (any format)."""
    # Try various arXiv ID patterns
    patterns = [
        r'arXiv ID[^|]*\|\s*(\d{4}\.\d{4,5})',  # | arXiv ID | 2605.07608 |
        r'arXiv ID\*\*:\s*(\d{4}\.\d{4,5})',  # **arXiv ID**: 2605.07608
        r'arXiv\*\*:\s*(\d{4}\.\d{4,5})',  # **arXiv**: 2605.07608
        r'arxiv_id:\s*"?(\d{4}\.\d{4,5})"?',  # arxiv_id: "2605.07608"
        r'arXiv ID:\s*(\d{4}\.\d{4,5})',  # arXiv ID: 2605.07608
    ]
    for p in patterns:
        m = re.search(p, content)
        if m:
            return f"https://arxiv.org/abs/{m.group(1)}"
    return ""


def extract_date_from_arxiv(content: str) -> str:
    """Extract date from arXiv ID (YYMM format -> YYYY-MM-01)."""
    patterns = [
        r'arXiv ID[^|]*\|\s*(\d{4}\.\d{4,5})',
        r'\|\s*(?:\*\*)?arXiv ID(?:\*\*)?\s*\|\s*(\d{4}\.\d{4,5})',
        r'-\s*\*\*arXiv ID\*\*:\s*(\d{4}\.\d{4,5})',
        r'-\s*\*\*arXiv\*\*:\s*(\d{4}\.\d{4,5})',
        r'arxiv_id:\s*"?(\d{4}\.\d{4,5})"?',
    ]
    for p in patterns:
        m = re.search(p, content)
        if m:
            arxiv_id = re.sub(r'v\d+$', '', m.group(1))
            try:
                yy = int(arxiv_id[:2])
                mm = int(arxiv_id[2:4])
                yyyy = 2000 + yy if yy < 50 else 1900 + yy
                if 1 <= mm <= 12:
                    return f"{yyyy}-{mm:02d}-01"
            except:
                pass
    return ""


def build_research_field_mocs(vault_path: Path) -> dict:
    """为每个研究方向生成 summary.md"""
    config = load_user_config()
    rf_folder = config.get("paths", {}).get("research_fields_folder", "Research_Fields")
    rf_path = vault_path / rf_folder

    uncategorized_path = vault_path / "未分类"
    if not rf_path.exists() and not uncategorized_path.exists():
        print(f"[warn] Research_Fields folder not found: {rf_path}")
        return {"status": "skipped", "reason": "folder not found"}

    result = {
        "root_dir": str(rf_path),
        "research_fields": 0,
        "papers_found": 0,
        "created_files": 0,
        "updated_files": 0,
    }

    for field_dir in _iter_research_field_dirs(vault_path, rf_path):
        result["research_fields"] += 1
        field_name = field_dir.name

        papers = _collect_field_papers(field_dir)

        # Sort papers by date descending
        def sort_key(p):
            d = p.get("date", "")
            if not d:
                return (1, "")
            try:
                y, m, day = d.split("-")
                return (0, -int(y) * 10000 - int(m) * 100 - int(day))
            except:
                return (1, "")
        papers.sort(key=sort_key)
        papers = papers[:MAX_SUMMARY_PAPERS]

        result["papers_found"] += len(papers)

        # Generate summary.md
        summary_path = field_dir / "summary.md"
        managed_block = _build_managed_paper_list_block(papers, vault_path)

        if summary_path.exists():
            existing = summary_path.read_text(encoding="utf-8")
            content = _merge_summary_content(existing, field_name, managed_block)
            if existing == content:
                pass
            else:
                summary_path.write_text(content, encoding="utf-8")
                result["updated_files"] += 1
        else:
            content = _build_summary_content(field_name, managed_block)
            summary_path.write_text(content, encoding="utf-8")
            result["created_files"] += 1

    return result


def _iter_research_field_dirs(vault_path: Path, rf_path: Path) -> list[Path]:
    """Return normal research fields plus the root-level uncategorized field."""
    field_dirs = []
    if rf_path.exists():
        field_dirs.extend(
            field_dir
            for field_dir in sorted(rf_path.iterdir())
            if field_dir.is_dir() and not field_dir.name.startswith(".")
        )
    uncategorized_dir = vault_path / "未分类"
    if uncategorized_dir.exists() and uncategorized_dir.is_dir() and uncategorized_dir not in field_dirs:
        field_dirs.append(uncategorized_dir)
    return field_dirs


def _build_summary_content(field_name: str, managed_block: str) -> str:
    """生成 summary.md 的内容"""
    lines = [
        "---",
        "tags: [MOC, auto-generated, research-field]",
        "generated_by: dailypaper-skills",
        "---",
        "",
        f"# {field_name}",
        "",
    ]
    lines.append(managed_block)
    return "\n".join(lines)


def _build_managed_paper_list_block(papers: list, vault_root: Path) -> str:
    """Build the auto-managed paper list block for summary.md."""
    lines = [
        PAPER_LIST_START,
        f"该研究方向下共有 **{len(papers)}** 篇论文。",
        "",
        "## 论文列表",
        "",
    ]

    if not papers:
        lines.append("- 暂无内容")
    else:
        lines.append("| 发布时间 | 论文 | 笔记 | 代码 | 来源 | 备注 |")
        lines.append("|----------|------|------|------|------|------|")

        vault_name = vault_root.parent.name

        for paper in papers:
            method_name = paper["name"]

            # Format date
            date_str = paper.get("date", "").replace("-", ".") if paper.get("date") else ""

            # Paper name with optional link
            if paper.get("has_pdf"):
                pdf_path = f"{paper.get('rel_dir', f'papers/{method_name}')}/{method_name}.pdf"
                paper_link = f"[{method_name}](obsidian://open?vault={vault_name}&file={pdf_path})"
            elif paper.get("source"):
                paper_link = f"[{method_name}]({paper.get('source')})"
            elif paper.get("pdf_url"):
                paper_link = f"[{method_name}]({paper.get('pdf_url')})"
            else:
                paper_link = method_name

            # Notes: EN and ZH links
            rel_dir = paper.get("rel_dir", f"papers/{method_name}")
            en_link = f"[EN](obsidian://open?vault={vault_name}&file={rel_dir}/{method_name}_en)" if paper.get("has_en") else ""
            zh_link = f"[ZH](obsidian://open?vault={vault_name}&file={rel_dir}/{method_name}_zh)" if paper.get("has_zh") else ""
            notes_link = " ".join(filter(None, [en_link, zh_link])) or "待精读"

            # Code/project link
            code_url = paper.get("github", "") or paper.get("code_url", "")
            if code_url:
                code_label = "GitHub" if "github.com" in code_url.lower() else "Project"
                github_link = f"[{code_label}]({code_url})"
            else:
                github_link = ""

            # Source
            source = paper.get("source", "")
            source_label = "arXiv" if "arxiv.org" in source.lower() else "Source"
            source_link = f"[{source_label}]({source})" if source else ""

            lines.append(f"| {date_str} | {paper_link} | {notes_link} | {github_link} | {source_link} |  |")

    lines.append(PAPER_LIST_END)
    return "\n".join(lines)


def _merge_summary_content(existing: str, field_name: str, managed_block: str) -> str:
    """Update only ScholarFlow's managed paper-list block in summary.md."""
    if PAPER_LIST_START in existing and PAPER_LIST_END in existing:
        start = existing.index(PAPER_LIST_START)
        end = existing.index(PAPER_LIST_END, start) + len(PAPER_LIST_END)
        suffix = existing[end:]
        return (
            existing[:start].rstrip()
            + "\n\n"
            + managed_block
            + ("\n\n" + suffix.lstrip("\n") if suffix.strip() else "")
        )

    heading_match = re.search(r"(?m)^## 论文列表\s*$", existing)
    if heading_match:
        prefix = _strip_legacy_count(existing[: heading_match.start()])
        next_heading = re.search(r"(?m)^## .+$", existing[heading_match.end():])
        if next_heading:
            suffix = existing[heading_match.end() + next_heading.start():]
        else:
            suffix = ""
        return prefix.rstrip() + "\n\n" + managed_block + ("\n\n" + suffix.lstrip("\n") if suffix.strip() else "")

    base = existing.rstrip()
    if not base:
        return _build_summary_content(field_name, managed_block)
    return base + "\n\n" + managed_block


def _strip_legacy_count(prefix: str) -> str:
    """Remove the old auto-generated count line immediately before ## 论文列表."""
    lines = prefix.rstrip().splitlines()
    while lines and not lines[-1].strip():
        lines.pop()
    if lines and re.fullmatch(r"该研究方向下共有 \*\*\d+\*\* 篇论文。", lines[-1].strip()):
        lines.pop()
    return "\n".join(lines)


def _collect_field_papers(field_dir: Path) -> list[dict]:
    entries = _load_topic_paper_candidates(field_dir) + _scan_note_papers(field_dir)
    merged: dict[str, dict] = {}
    key_index: dict[str, str] = {}
    for entry in entries:
        keys = _entry_keys(entry)
        primary_key = next((key_index[key] for key in keys if key in key_index), keys[0])
        if primary_key in merged:
            merged[primary_key] = _merge_paper_entry(merged[primary_key], entry)
        else:
            merged[primary_key] = entry
        for key in keys:
            key_index[key] = primary_key
    return list(merged.values())


def _load_topic_paper_candidates(field_dir: Path) -> list[dict]:
    topic_papers_path = _topic_papers_path(field_dir)
    if topic_papers_path is None:
        return []
    try:
        payload = json.loads(topic_papers_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if isinstance(payload, dict):
        raw_papers = payload.get("papers", [])
    else:
        raw_papers = payload
    if not isinstance(raw_papers, list):
        return []

    papers = []
    for item in raw_papers:
        if not isinstance(item, dict):
            continue
        if _metadata_text(item.get("label")).lower() == "exclude":
            continue
        title = _metadata_text(item.get("title"))
        method_name = _metadata_text(item.get("method_name") or item.get("name")) or _method_name_from_title(title)
        if not method_name:
            continue
        source = _source_url(item)
        code_url = _extract_code_url(item)
        papers.append({
            "name": method_name,
            "title": title,
            "has_en": False,
            "has_zh": False,
            "has_pdf": False,
            "date": _coerce_candidate_date(item),
            "github": code_url if "github.com" in code_url.lower() else "",
            "code_url": code_url,
            "source": source,
            "pdf_url": _metadata_text(item.get("pdf_url")),
            "label": _metadata_text(item.get("label")),
            "reason": _metadata_text(item.get("reason")),
            "note_status": _metadata_text(item.get("note_status")) or "pending",
        })
    return papers


def _topic_papers_path(field_dir: Path) -> Path | None:
    meta_path = field_dir / "_meta" / "topic_papers.json"
    if meta_path.exists():
        return meta_path
    legacy_path = field_dir / "topic_papers.json"
    if legacy_path.exists():
        return legacy_path
    return None


def _scan_note_papers(field_dir: Path) -> list[dict]:
    paper_dirs: list[Path] = []
    papers_dir = field_dir / "papers"
    if papers_dir.exists():
        paper_dirs.extend(_paper_note_dirs(papers_dir))
    paper_dirs.extend(_paper_note_dirs(field_dir, exclude_names={"papers", "_meta"}))

    papers = []
    seen_dirs = set()
    for paper_dir in paper_dirs:
        if paper_dir in seen_dirs:
            continue
        seen_dirs.add(paper_dir)
        method_name = paper_dir.name
        has_en = (paper_dir / f"{method_name}_en.md").exists()
        has_zh = (paper_dir / f"{method_name}_zh.md").exists()
        has_pdf = (paper_dir / f"{method_name}.pdf").exists()
        if not has_en and not has_zh:
            continue

        paper_date = ""
        paper_github = ""
        paper_source = ""
        note_file = paper_dir / f"{method_name}_en.md" if has_en else paper_dir / f"{method_name}_zh.md"
        content = note_file.read_text(encoding="utf-8")

        date_match = re.search(r'^date:\s*(\d{4}-\d{2}-\d{2})', content, re.MULTILINE)
        if not date_match:
            date_match = re.search(r'\|\s*\*\*?Published\*\*?\s*\|\s*(\d{4}-\d{2}-\d{2})', content, re.IGNORECASE)
        paper_date = date_match.group(1) if date_match else extract_date_from_arxiv(content)

        paper_source = extract_arxiv_source(content)

        github_match = re.search(r'(?:github|code):\s*(https://github\.com/[^\s]+)', content, re.IGNORECASE)
        if not github_match:
            github_match = re.search(r'\[(?:GitHub|Code|github)\]\((https://github\.com/[^\)]+)\)', content, re.IGNORECASE)
        if github_match:
            paper_github = github_match.group(1)

        papers.append({
            "name": method_name,
            "path": paper_dir,
            "rel_dir": paper_dir.relative_to(field_dir).as_posix(),
            "has_en": has_en,
            "has_zh": has_zh,
            "has_pdf": has_pdf,
            "date": paper_date,
            "github": paper_github,
            "source": paper_source,
            "note_status": "done",
        })
    return papers


def _paper_note_dirs(root: Path, exclude_names: set[str] | None = None) -> list[Path]:
    exclude_names = exclude_names or set()
    dirs = []
    for child in sorted(root.iterdir()) if root.exists() else []:
        if not child.is_dir() or child.name.startswith(".") or child.name in exclude_names:
            continue
        if (child / f"{child.name}_en.md").exists() or (child / f"{child.name}_zh.md").exists():
            dirs.append(child)
    return dirs


def _merge_paper_entry(existing: dict, incoming: dict) -> dict:
    merged = dict(existing)
    incoming_done = incoming.get("note_status") == "done" or incoming.get("has_en") or incoming.get("has_zh")
    for key, value in incoming.items():
        if value in ("", None, [], {}):
            continue
        if key in {"label", "reason"} and merged.get(key):
            continue
        if incoming_done or not merged.get(key):
            merged[key] = value
    if incoming_done:
        merged["note_status"] = "done"
    return merged


def _entry_keys(entry: dict) -> list[str]:
    keys = []
    if entry.get("name"):
        keys.append("name:" + entry.get("name", "").lower())
    for url_key in ("source", "pdf_url"):
        source = entry.get(url_key, "")
        arxiv_id = _extract_arxiv_id(source)
        if arxiv_id:
            keys.append("arxiv:" + arxiv_id)
    title = _metadata_text(entry.get("title"))
    if title:
        keys.append("title:" + re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", title.lower()).strip())
    return keys or ["object:" + str(id(entry))]


def _source_url(item: dict) -> str:
    for key in ("url", "source_url", "source"):
        value = _metadata_text(item.get(key))
        if value.startswith("http://") or value.startswith("https://"):
            return _normalize_source_url(value)
    arxiv_id = _metadata_text(item.get("arxiv_id"))
    if arxiv_id:
        return f"https://arxiv.org/abs/{_normalize_arxiv_id(arxiv_id)}"
    return ""


def _normalize_source_url(value: str) -> str:
    value = _clean_url(value)
    arxiv_id = _extract_arxiv_id(value)
    if arxiv_id:
        return f"https://arxiv.org/abs/{arxiv_id}"
    return value


def _extract_arxiv_id(value: str) -> str:
    match = re.search(r"arxiv\.org/(?:abs|pdf)/([^?#\s)]+)", _metadata_text(value), re.IGNORECASE)
    if match:
        return _normalize_arxiv_id(match.group(1))
    match = re.search(r"\b(\d{4}\.\d{4,5})(?:v\d+)?\b", _metadata_text(value))
    if match:
        return _normalize_arxiv_id(match.group(0))
    return ""


def _normalize_arxiv_id(value: str) -> str:
    return re.sub(r"v\d+$", "", value.strip(), flags=re.IGNORECASE).lower()


def _extract_code_url(item: dict) -> str:
    direct_fields = (
        "github",
        "code_url",
        "code",
        "repository",
        "repo_url",
        "project_url",
        "homepage",
        "demo_url",
    )
    for key in direct_fields:
        url = _first_code_url(_metadata_text(item.get(key)))
        if url:
            return url

    text_fields = (
        "title",
        "abstract",
        "summary",
        "comment",
        "comments",
        "notes",
        "raw",
    )
    text = "\n".join(_metadata_text(item.get(key)) for key in text_fields if item.get(key))
    return _first_code_url(text)


def _first_code_url(text: str) -> str:
    if not text:
        return ""
    match = GITHUB_URL_RE.search(text)
    if match:
        return _clean_url(match.group(0))
    match = PROJECT_URL_RE.search(text)
    if match:
        return _clean_url(match.group(0))
    return ""


def _clean_url(value: str) -> str:
    value = re.sub(r"\{[^}]*\}", "", _metadata_text(value))
    return value.rstrip(".,;:)]}\"'")


def _coerce_candidate_date(item: dict) -> str:
    for key in ("date", "published", "published_date"):
        value = _metadata_text(item.get(key))
        match = re.search(r"(19|20)\d{2}-\d{2}-\d{2}", value)
        if match:
            return match.group(0)
    year = _metadata_text(item.get("year"))
    if re.fullmatch(r"(19|20)\d{2}", year):
        return f"{year}-01-01"
    return ""


def _method_name_from_title(title: str) -> str:
    if not title:
        return ""
    if ":" in title:
        return title.split(":", 1)[0].strip()
    return title.strip()


def _metadata_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return " ".join(value.split())
    if isinstance(value, (int, float)):
        return str(value)
    return str(value).strip()


def main():
    if len(sys.argv) > 1:
        vault_path = Path(sys.argv[1])
    else:
        config = load_user_config()
        vault_path = Path(config.get("paths", {}).get("obsidian_vault", ".")).expanduser().resolve()

    if not vault_path.exists():
        print(f"[error] Vault path not found: {vault_path}")
        sys.exit(1)

    print(f"[generate_research_field_mocs] vault: {vault_path}")
    result = build_research_field_mocs(vault_path)
    print(f"[done] research_fields={result['research_fields']}, "
          f"papers={result['papers_found']}, "
          f"created={result['created_files']}, "
          f"updated={result['updated_files']}")
    return result


if __name__ == "__main__":
    main()
