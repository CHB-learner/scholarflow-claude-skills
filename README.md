# ScholarFlow Claude Skills

📚 **ScholarFlow 是一套面向 Claude Code 的论文调研、候选筛选、精读笔记生成与 Obsidian 知识库维护 skills。**

它的核心目标很简单：让 Claude Code 帮你把论文从“搜到一堆链接”整理成“可以在 Obsidian 里长期积累的研究知识库”。

## ✨ 主要功能

1. 🗞️ **每日论文推荐**
   抓取最近论文，去重、筛选、点评，并输出到 Obsidian 的每日论文目录。

2. 🔎 **研究方向调研**
   例如调研 “Agentic RL”“RNA 序列设计”“扩散模型”，只更新候选列表，不自动精读。

3. 📖 **指定论文精读**
   用户明确说 `读一下 XXX` 或 `精读 XXX` 后，才下载/读取论文并生成中英双语深度笔记。

4. 🧠 **Obsidian 研究方向 summary 维护**
   自动维护 `summary.md` 里的论文表格，同时保留你手写的研究判断、备注和额外章节。

5. 🔗 **链接回填**
   精读完成后，summary 中同一篇论文会从 `待精读` 更新为 EN/ZH/PDF 等本地笔记链接。

## 🚀 安装到 Claude Code

### 1. 安装 Claude Code

```bash
npm install -g @anthropic-ai/claude-code
claude --version
```

### 2. 安装 ScholarFlow skills

Claude Code 识别的 skill 路径是：

```text
~/.claude/skills/<skill-name>/SKILL.md
```

本仓库的可安装内容放在 `skills/` 目录里，所以安装时要把 `skills/` 里面的内容平铺同步到 `~/.claude/skills/`。

📦 **个人级安装，一行命令：**

```bash
mkdir -p ~/.claude/skills && \
tmp_dir="$(mktemp -d)" && \
git clone https://github.com/CHB-learner/scholarflow-claude-skills.git "$tmp_dir/scholarflow-claude-skills" && \
rsync -a "$tmp_dir/scholarflow-claude-skills/skills/" ~/.claude/skills/ && \
rm -rf "$tmp_dir"
```

✅ **确认安装成功：**

```bash
find ~/.claude/skills -maxdepth 2 -name SKILL.md | sort
```

你应该能看到：

```text
~/.claude/skills/daily-papers/SKILL.md
~/.claude/skills/daily-papers-fetch/SKILL.md
~/.claude/skills/daily-papers-notes/SKILL.md
~/.claude/skills/daily-papers-review/SKILL.md
~/.claude/skills/paper-reader/SKILL.md
~/.claude/skills/topic-research/SKILL.md
```

🔄 **后续更新：**

```bash
cd ~/scholarflow-claude-skills
git pull
rsync -a skills/ ~/.claude/skills/
```

如果你还没有保留仓库工作副本，可以先 clone：

```bash
git clone https://github.com/CHB-learner/scholarflow-claude-skills.git ~/scholarflow-claude-skills
```

## ⚙️ 配置 Obsidian 路径

复制示例配置：

```bash
cp ~/.claude/skills/_shared/user-config.example.json ~/.claude/skills/_shared/user-config.local.json
```

然后编辑：

```text
~/.claude/skills/_shared/user-config.local.json
```

重点配置这些字段：

```json
{
  "paths": {
    "obsidian_vault": "/你的/Obsidian/Vault/路径",
    "daily_papers_folder": "Dailypaper",
    "research_fields_folder": "Research_Fields"
  },
  "daily_papers": {
    "keywords": ["RNA design", "LLM agent"]
  },
  "research_fields": {
    "RNA序列设计": ["RNA sequence design", "mRNA design"]
  }
}
```

## 🗂️ Obsidian 输出结构

ScholarFlow 会把内容写进你的 Obsidian vault。典型结构如下：

```text
{obsidian_vault}/
├── Dailypaper/
│   └── 5月/
│       └── 0519/
│           ├── 今日论文推荐.md
│           ├── research-AgenticRL.md
│           └── _meta/
│               ├── candidates.json
│               ├── screening.json
│               ├── source_diagnostics.json
│               └── dedup_stats.json
│
└── Research_Fields/
    └── AgenticRL/
        ├── summary.md
        ├── _meta/
        │   └── topic_papers.json
        └── papers/
            └── Code-as-Agent-Harness/
                ├── Code-as-Agent-Harness_en.md
                ├── Code-as-Agent-Harness_zh.md
                ├── Code-as-Agent-Harness.pdf
                └── pngs/
```

### 📌 `Dailypaper/`

这里放每日推荐和某次调研的快速导航：

- `今日论文推荐.md`：每日论文推荐入口
- `research-{方向}.md`：某个研究方向的调研推荐
- `_meta/`：抓取、去重、筛选的中间记录，方便复盘

### 🧭 `Research_Fields/{方向}/summary.md`

这里是一个方向的长期索引页。自动表格类似：

```markdown
| 发布时间 | 论文 | 笔记 | 代码 | 来源 | 备注 |
|----------|------|------|------|------|------|
| 2026.05.18 | [Code as Agent Harness](https://arxiv.org/abs/2605.18747) | 待精读 |  | [arXiv](https://arxiv.org/abs/2605.18747) |  |
```

说明：

- 📝 未精读：笔记列显示 `待精读`
- 📖 已精读：笔记列显示 `[EN] [ZH]`
- 🔗 论文名优先链接本地 PDF，否则链接 arXiv/来源页
- 🧑‍🔬 `备注` 列留空，给你人工写判断
- 🧩 自动区块之外的内容不会被覆盖

### 📚 `Research_Fields/{方向}/papers/{论文名}/`

精读后，每篇论文会有自己的目录：

```text
papers/{MethodName}/
├── {MethodName}_en.md
├── {MethodName}_zh.md
├── {MethodName}.pdf
└── pngs/
```

## 🧪 怎么使用

在 Claude Code 里直接用自然语言触发。

### 1. 🗞️ 每日论文推荐

```text
今日论文推荐
过去一周论文推荐
最近 3 天 RNA design 有什么论文
```

输出位置：

```text
{obsidian_vault}/Dailypaper/{月份}/{日期}/
```

### 2. 🔎 调研一个研究方向

```text
调研过去一年 Agentic RL 的论文
调研 RNA 序列设计 方向最近的论文
看看扩散模型有什么新文章
```

调研阶段只做：

- 🔍 抓取候选论文
- 🧹 去重和相关性筛选
- 🧾 更新 `Research_Fields/{方向}/summary.md`
- 🗃️ 写入 `Research_Fields/{方向}/_meta/topic_papers.json`

不会自动精读，也不会自动生成深度笔记。

### 3. 📖 精读指定论文

```text
读一下 RiboSphere
精读 Code as Agent Harness
生成笔记 https://arxiv.org/abs/2605.18747
```

精读后会写入：

```text
Research_Fields/{方向}/papers/{MethodName}/
```

并回填 `summary.md` 里的笔记链接。

### 4. 📝 只看待精读候选

```text
读一下
```

如果不带论文名，Claude 不会自动开读，而是列出 summary 中的 `待精读` 候选，让你指定要读哪一篇。

## 🧱 仓库结构

```text
.
├── README.md
├── skills/
│   ├── _shared/
│   ├── daily-papers/
│   ├── daily-papers-fetch/
│   ├── daily-papers-review/
│   ├── daily-papers-notes/
│   ├── paper-reader/
│   └── topic-research/
└── tests/
```

## 🌟 一句话记住

先用 `调研 XXX` 建立方向候选列表，再用 `读一下 XXX` 精读指定论文，最后所有结果都会沉淀到 Obsidian 的 `Research_Fields/` 里。
