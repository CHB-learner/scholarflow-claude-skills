#!/usr/bin/env python3
"""
generate_research_field_mocs.py

为 Research_Fields 下的每个研究方向生成 summary.md 索引页。
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

    if not rf_path.exists():
        print(f"[warn] Research_Fields folder not found: {rf_path}")
        return {"status": "skipped", "reason": "folder not found"}

    result = {
        "root_dir": str(rf_path),
        "research_fields": 0,
        "papers_found": 0,
        "created_files": 0,
        "updated_files": 0,
    }

    # Scan each research field subdirectory
    for field_dir in sorted(rf_path.iterdir()):
        if not field_dir.is_dir() or field_dir.name.startswith("."):
            continue

        result["research_fields"] += 1
        field_name = field_dir.name

        # papers are under {field_dir}/papers/{paper_name}/
        papers_dir = field_dir / "papers"
        if not papers_dir.exists():
            papers_dir = field_dir  # fallback to old structure

        papers = []
        for paper_dir in sorted(papers_dir.iterdir()) if papers_dir.exists() else []:
            if not paper_dir.is_dir() or paper_dir.name.startswith("."):
                continue

            method_name = paper_dir.name
            has_en = (paper_dir / f"{method_name}_en.md").exists()
            has_zh = (paper_dir / f"{method_name}_zh.md").exists()
            has_pdf = (paper_dir / f"{method_name}.pdf").exists()

            # Extract info from en.md (or zh.md as fallback)
            paper_date = ""
            paper_github = ""
            paper_source = ""
            note_file = paper_dir / f"{method_name}_en.md" if has_en else (paper_dir / f"{method_name}_zh.md" if has_zh else None)
            if note_file and note_file.exists():
                content = note_file.read_text(encoding="utf-8")

                # Date: try frontmatter date first, then Published table, then arXiv ID
                date_match = re.search(r'^date:\s*(\d{4}-\d{2}-\d{2})', content, re.MULTILINE)
                if not date_match:
                    date_match = re.search(r'\|\s*\*\*?Published\*\*?\s*\|\s*(\d{4}-\d{2}-\d{2})', content, re.IGNORECASE)
                if not date_match:
                    paper_date = extract_date_from_arxiv(content)
                else:
                    paper_date = date_match.group(1)

                # Source (arXiv URL) - extract regardless of date
                paper_source = extract_arxiv_source(content)

                # GitHub extraction
                github_match = re.search(r'(?:github|code):\s*(https://github\.com/[^\s]+)', content, re.IGNORECASE)
                if not github_match:
                    github_match = re.search(r'\[(?:GitHub|Code|github)\]\((https://github\.com/[^\)]+)\)', content, re.IGNORECASE)
                if github_match:
                    paper_github = github_match.group(1)

            if has_en or has_zh:
                papers.append({
                    "name": method_name,
                    "path": paper_dir,
                    "has_en": has_en,
                    "has_zh": has_zh,
                    "has_pdf": has_pdf,
                    "date": paper_date,
                    "github": paper_github,
                    "source": paper_source,
                })

        result["papers_found"] += len(papers)

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
                pdf_path = f"papers/{method_name}/{method_name}.pdf"
                paper_link = f"[{method_name}](obsidian://open?vault={vault_name}&file={pdf_path})"
            elif paper.get("source"):
                paper_link = f"[{method_name}]({paper.get('source')})"
            else:
                paper_link = method_name

            # Notes: EN and ZH links
            en_link = f"[EN](obsidian://open?vault={vault_name}&file=papers/{method_name}/{method_name}_en)" if paper.get("has_en") else ""
            zh_link = f"[ZH](obsidian://open?vault={vault_name}&file=papers/{method_name}/{method_name}_zh)" if paper.get("has_zh") else ""
            notes_link = " ".join(filter(None, [en_link, zh_link]))

            # GitHub link
            github = paper.get("github", "")
            github_link = f"[GitHub]({github})" if github else ""

            # Source
            source = paper.get("source", "")
            source_link = f"[arXiv]({source})" if source else ""

            lines.append(f"| {date_str} | {paper_link} | {notes_link} | {github_link} | {source_link} | |")

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
