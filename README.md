# ScholarFlow Claude Skills

📚✨ **ScholarFlow 是一套面向 Claude Code 的论文推荐、论文精读、领域调研与 Obsidian 知识库维护 skills。**

它的目标很简单：你用自然语言让 Claude Code 找论文 🔍、读论文 📖、整理方向 🧭，它把结果沉淀到 Obsidian 🧠。

## ✨ 主要功能

1. 🗞️ **每日论文推荐**

   📰 按你的关键词抓取近期论文，自动去重、筛选、点评，输出每日推荐。

2. 📖 **读某篇论文**

   🧠 你说 `读一下 XXX` 或 `精读 XXX`，Claude 生成中英双语深度笔记。若论文不匹配任何研究方向，自动保存到 `未分类/`，文件夹结构和领域内精读笔记一致。

3. 🔎 **领域调研**

   🧭 你说 `调研 XXX`，Claude 只抓取、筛选、更新候选列表和 summary，不自动精读；后续你指定论文再读。

🛠️ 底层仍保留 `daily-papers-fetch`、`daily-papers-review`、`daily-papers-notes` 等分步骤 skills，方便需要时单独调试。

## 🚀 安装到 Claude Code

📍 Claude Code 识别的 skill 路径是：

```text
~/.claude/skills/<skill-name>/SKILL.md
```

📦 本仓库的可安装内容在 `skills/` 目录里。安装时要把 `skills/` 里面的内容平铺同步到 `~/.claude/skills/`。

```bash
mkdir -p ~/.claude/skills && \
tmp_dir="$(mktemp -d)" && \
git clone https://github.com/CHB-learner/scholarflow-claude-skills.git "$tmp_dir/scholarflow-claude-skills" && \
rsync -a "$tmp_dir/scholarflow-claude-skills/skills/" ~/.claude/skills/ && \
rm -rf "$tmp_dir"
```

✅ 确认安装：

```bash
find ~/.claude/skills -maxdepth 2 -name SKILL.md | sort
```

## ⚙️ 配置参数

📋 复制示例配置：

```bash
cp ~/.claude/skills/_shared/user-config.example.json ~/.claude/skills/_shared/user-config.local.json
```

✏️ 编辑：

```text
~/.claude/skills/_shared/user-config.local.json
```

🌈 推荐配置格式：

```json
{
  "vault": "~/Obsidian/ScholarFlowDemo",
  "folders": {
    "daily": "Dailypaper",
    "research": "Research_Fields",
    "uncategorized": "未分类"
  },
  "daily": {
    "keywords": ["scientific agents", "controllable generation"]
  },
  "fields": {
    "多智能体科研": ["multi-agent research automation", "scientific agent"],
    "可控生成模型": ["controllable generation", "diffusion planning"]
  },
  "zotero": {
    "db": "~/Zotero/zotero.sqlite",
    "storage": "~/Zotero/storage"
  }
}
```

🧩 字段含义：

- 🏠 `vault`：你的 Obsidian 输出根目录。
- 🗞️ `folders.daily`：每日论文推荐目录。
- 🧭 `folders.research`：领域调研目录。
- 📦 `folders.uncategorized`：未匹配领域论文的默认目录。
- 🎯 `daily.keywords`：每日论文推荐默认关键词。
- 🧪 `fields`：研究方向和对应检索关键词。
- 📚 `zotero`：可选，用于本地 Zotero PDF 定位。

🔁 旧版 `paths`、`daily_papers`、`research_fields` 配置仍然兼容，不需要强制迁移。

## 🗂️ Obsidian 输出结构

🗺️ 典型输出结构如下：

```text
{vault}/
├── Dailypaper/
│   ├── .history.json
│   └── 2026-05-20/
│       ├── 2026-05-20-论文推荐.md
│       └── _meta/
│           ├── candidates.json
│           ├── screening.json
│           └── source_diagnostics.json
│
├── Research_Fields/
│   └── 多智能体科研/
│       ├── summary.md
│       ├── _meta/
│       │   ├── candidates.json
│       │   ├── screening.json
│       │   ├── source_diagnostics.json
│       │   ├── dedup_stats.json
│       │   └── topic_papers.json
│       └── papers/
│           └── AtlasAgent/
│               ├── AtlasAgent_en.md
│               ├── AtlasAgent_zh.md
│               ├── AtlasAgent.pdf
│               └── pngs/
│
└── 未分类/
    ├── summary.md
    └── papers/
        └── CurioGraph/
            ├── CurioGraph_en.md
            ├── CurioGraph_zh.md
            ├── CurioGraph.pdf
            └── pngs/
```

### 🗞️ `Dailypaper/`

📰 每日论文推荐输出在这里。它是“今天/最近几天有什么值得看”的入口。

### 🧭 `Research_Fields/{方向}/`

🧭 领域调研输出在这里：

- 🧾 `summary.md`：方向总览和候选论文表格。
- 🗃️ `_meta/topic_papers.json`：候选论文索引。
- 🔍 `_meta/candidates.json`、`screening.json`：抓取和筛选记录。
- 📖 `papers/{MethodName}/`：精读后的论文笔记目录。

`summary.md` 的自动表格类似：

| 发布时间 | 论文 | 笔记 | 代码 | 来源 | 备注 |
|----------|------|------|------|------|------|
| 2026.06.01 | [AtlasAgent](https://arxiv.org/abs/xxxx.xxxxx) | 待精读 | [GitHub](https://github.com/example/atlas-agent) | [arXiv](https://arxiv.org/abs/xxxx.xxxxx) |  |

说明：

- 📝 未精读：笔记列显示 `待精读`
- 📖 已精读：笔记列显示 `[EN] [ZH]`
- 🧑‍🔬 `备注` 列留空，给你人工写判断
- 🧩 自动区块之外的手写内容会保留

### 📦 `未分类/`

📦 当你直接说 `读一下 XXX`，但这篇论文不匹配任何已有研究方向时，笔记会放到这里：

```text
{vault}/未分类/papers/{MethodName}/
```

✅ 输出格式和 `Research_Fields/{方向}/papers/{MethodName}/` 完全一致。

## 🧪 怎么使用

### 1. 🗞️ 每日论文推荐

```text
今日论文推荐
过去一周论文推荐
最近 3 天 scientific agents 有什么论文
```

📍 输出到：

```text
{vault}/Dailypaper/{YYYY-MM-DD}/
```

### 2. 📖 读某篇论文

```text
读一下 AtlasAgent
精读 MemoryWeaver
生成笔记 https://arxiv.org/abs/xxxx.xxxxx
```

🎯 如果匹配到研究方向，输出到：

```text
{vault}/Research_Fields/{方向}/papers/{MethodName}/
```

📦 如果匹配不到研究方向，输出到：

```text
{vault}/未分类/papers/{MethodName}/
```

### 3. 🔎 领域调研

```text
调研过去一年多智能体科研助手的论文
调研可控生成模型方向最近的论文
看看扩散模型有什么新文章
```

🧭 领域调研只更新：

```text
{vault}/Research_Fields/{方向}/summary.md
{vault}/Research_Fields/{方向}/_meta/topic_papers.json
```

🚫 不会自动精读，也不会写入 `Dailypaper/{YYYY-MM-DD}`。

## 🌟 一句话记住

🗞️ `今日论文推荐` 看新论文，📖 `读一下 XXX` 生成深度笔记，🔎 `调研 XXX` 建立研究方向候选列表。
