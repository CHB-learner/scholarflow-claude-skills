---
name: scholarflow
description: >
  Codex-native ScholarFlow paper workflow for Obsidian. Use when the user asks
  for daily paper recommendations, paper reading notes, paper deep dives,
  research-field surveys, topic paper discovery, summary.md maintenance, or
  Chinese paper commands such as 今日论文推荐, 过去一周论文推荐, 读一下 XXX,
  精读 XXX, 生成笔记 XXX, 调研 XXX, 搜索 XXX 相关论文, or 了解 XXX 方向.
metadata:
  codex_adapter: true
  version: "0.1.0"
---

# ScholarFlow for Codex

ScholarFlow is an Obsidian-first paper workflow. Route each request to one of
three workflows, then read only the matching reference file.

## Resource Map

All paths below are relative to this skill directory.

- Configuration helpers: `scripts/_shared/`
- Daily paper scripts: `scripts/daily-papers/`
- Daily review helpers: `scripts/daily-papers-review/`
- Daily note helpers: `scripts/daily-papers-notes/`
- Paper reading helpers: `scripts/paper-reader/`
- Paper note templates: `assets/paper-reader/`
- Workflow references: `references/`

Configuration is loaded from `scripts/_shared/user-config.json` and
`scripts/_shared/user-config.local.json`. The compact config shape
`vault/folders/daily/fields/zotero` and the legacy
`paths/daily_papers/research_fields` shape are both supported.

## Intent Router

### Daily Paper Recommendations

Use this path when the user asks:

- `今日论文推荐`
- `每日论文推荐`
- `过去一周论文推荐`
- `最近 3 天 scientific agents 有什么论文`

Read `references/daily-papers.md` first. If the user asks to run a specific
stage, read the matching stage file:

- Fetch only: `references/daily-papers-fetch.md`
- Review only: `references/daily-papers-review.md`
- Notes/backfill only: `references/daily-papers-notes.md`

Daily output must stay under `{vault}/Dailypaper/{YYYY-MM-DD}/`.
Never create month/day mixed directories such as `Dailypaper/5月/0520/`.

### Read One Paper

Use this path when the user says:

- `读一下 XXX`
- `精读 XXX`
- `生成笔记 XXX`
- provides an arXiv URL, DOI, PDF path, or paper title and asks for notes

Read `references/paper-reader.md` first.

If the user only says `读一下` without a title, URL, DOI, or PDF path, do not
start deep reading. List pending candidates from the relevant `summary.md` or
`_meta/topic_papers.json` and ask the user to specify a paper.

Matched research-field papers go to
`{vault}/Research_Fields/{方向}/papers/{MethodName}/`. Papers that do not match
an existing research field go to `{vault}/未分类/papers/{MethodName}/`.

### Research Field Survey

Use this path when the user asks:

- `调研 XXX`
- `搜索 XXX 相关论文`
- `了解 XXX 方向`
- `看看 XXX 领域有什么文章`

Read `references/topic-research.md` first.

Research-field survey is lightweight: fetch, deduplicate, screen, and update
`summary.md` plus `_meta/topic_papers.json`. Do not deep-read papers, do not
download PDFs, and do not extract figures unless the user later names one paper
for deep reading.

## Output Contract

ScholarFlow writes to the configured Obsidian vault:

```text
{vault}/
├── Dailypaper/{YYYY-MM-DD}/
├── Research_Fields/{方向}/summary.md
├── Research_Fields/{方向}/_meta/topic_papers.json
├── Research_Fields/{方向}/papers/{MethodName}/
└── 未分类/papers/{MethodName}/
```

`summary.md` may contain user-written content. Only update ScholarFlow's managed
paper-list block between:

```text
<!-- scholarflow:paper-list:start -->
<!-- scholarflow:paper-list:end -->
```

Keep the `备注` column empty; it is for human judgment.
