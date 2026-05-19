# ScholarFlow Claude Skills

ScholarFlow is a Claude Code skill suite for paper discovery, paper review, deep reading, and Obsidian research notes.

It is designed for Claude Code. The `SKILL.md` files, workflow wording, daemon prompts, and tool assumptions follow Claude Code's skill conventions.

## What It Does

- Fetches recent papers from multiple sources, including arXiv, Semantic Scholar, OpenAlex, Crossref, OpenReview, PubMed, Europe PMC, bioRxiv, and medRxiv.
- Normalizes papers into a shared schema, deduplicates them by identifiers and title similarity, and ranks candidates.
- Uses Claude Code skills to screen papers as `core`, `adjacent`, or `exclude`.
- Generates opinionated daily recommendation notes for Obsidian.
- Generates deep bilingual paper notes with math formulation, equations, figures, tables, and critical analysis.
- Supports topic-level research workflows and Zotero collection batch processing.

## Skills

| Skill | Purpose |
| --- | --- |
| `daily-papers` | One-command daily paper recommendation pipeline. |
| `daily-papers-fetch` | Multi-source paper retrieval, normalization, deduplication, ranking, and enrichment. |
| `daily-papers-review` | Claude-based paper screening and recommendation writing. |
| `daily-papers-notes` | Deep note generation for must-read papers and note-link backfilling. |
| `paper-reader` | Single-paper deep reading and bilingual note generation. |
| `topic-research` | Topic-driven research pipeline with generated search keywords and saved notes. |

Shared Python helpers live in `_shared/`.

## Repository Layout

```text
.
├── _shared/                 # Shared config, schemas, fetchers, MOC builders
├── daily-papers/            # Fetch/enrich scripts and top-level daily workflow
├── daily-papers-fetch/      # Claude Code skill wrapper for fetch step
├── daily-papers-review/     # Claude Code skill wrapper for review step
├── daily-papers-notes/      # Claude Code skill wrapper for note generation step
├── paper-reader/            # Deep paper-reading skill and Zotero daemon
├── topic-research/          # Topic research skill
└── tests/                   # Python unit tests
```

## Install

If this package owns your Claude Code skills directory:

```bash
git clone https://github.com/CHB-learner/scholarflow-claude-skills.git ~/.claude/skills
```

If you already have other skills in `~/.claude/skills`, clone elsewhere and copy or symlink the skill folders plus `_shared`:

```bash
git clone https://github.com/CHB-learner/scholarflow-claude-skills.git ~/scholarflow-claude-skills
cp -R ~/scholarflow-claude-skills/{_shared,daily-papers,daily-papers-fetch,daily-papers-review,daily-papers-notes,paper-reader,topic-research} ~/.claude/skills/
```

## Configure

Create a local config from the example:

```bash
cp ~/.claude/skills/_shared/user-config.example.json ~/.claude/skills/_shared/user-config.local.json
```

Then edit:

- `paths.obsidian_vault`
- `paths.daily_papers_folder`
- `paths.research_fields_folder`
- `paths.zotero_db`
- `paths.zotero_storage`
- `daily_papers.keywords`
- `research_fields`

Local config files are intentionally ignored by git.

## Usage

In Claude Code, trigger the skills with natural language:

```text
今日论文推荐
过去一周论文推荐
跑一下论文抓取
跑一下论文点评
跑一下论文笔记
读一下 <paper title or arXiv URL>
调研 RNA inverse folding 方向最近的论文
```

The daily pipeline writes outputs under your configured Obsidian vault, usually:

```text
{obsidian_vault}/{daily_papers_folder}/{month}月/{MMDD}/
```

Topic research writes field summaries and paper notes under:

```text
{obsidian_vault}/{research_fields_folder}/{topic}/
```

## Python Scripts

Run tests:

```bash
python3 -m unittest discover -s tests
```

Run multi-source fetch directly:

```bash
python3 daily-papers/multi_source_fetch.py \
  --topic "RNA inverse folding" \
  --queries-json '["RNA inverse folding", "RNA design"]' \
  --since-year 2021 \
  --max-results 100 \
  --sources auto \
  --output /tmp/scholarflow/candidates.json
```

## Requirements

- Claude Code with skill support.
- Python 3.10 or newer.
- Network access for paper source APIs.
- `curl` for enrichment helpers.
- `pdftotext` and `pdfimages` from Poppler for PDF extraction.
- Optional: Zotero local database access for `paper-reader/paper_daemon.py`.

## Notes

- This project is a Claude Code skill package, not a standalone web app.
- Python handles retrieval, normalization, deduplication, enrichment, and backfilling.
- Claude Code handles semantic screening, paper critique, and deep note writing.
- Git automation inside skills is disabled by default.

