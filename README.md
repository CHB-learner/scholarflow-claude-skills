# ScholarFlow Claude Skills

ScholarFlow 是一套写给 Claude Code 使用的论文工作流 skills，用来完成论文抓取、主题调研、候选筛选、精读笔记生成，以及 Obsidian 知识库索引维护。

本项目不是独立 Web 应用。仓库里的 `SKILL.md`、提示词、路径约定和工具调用假设都面向 Claude Code。

## 核心能力

- 多源抓取论文：支持 arXiv、Semantic Scholar、OpenAlex、Crossref、OpenReview、PubMed、Europe PMC、bioRxiv、medRxiv 等来源。
- 统一论文数据：对候选论文做 schema 规范化、标识符去重、标题相似度去重和排序。
- 每日论文推荐：把近期论文整理成 Obsidian 推荐笔记。
- 研究方向调研：根据主题生成关键词，抓取候选，筛选 `core` / `adjacent` / `exclude`，只更新候选列表。
- 指定论文精读：用户明确指定论文后，再生成中英双语深度笔记、公式、图表和锐评。
- Obsidian 索引维护：自动维护 `summary.md` 的论文列表区块，同时保留用户手写内容。
- Zotero 辅助读取：可从本地 Zotero 数据库和 storage 中定位论文 PDF。

## Skills 一览

| Skill | 用途 |
| --- | --- |
| `daily-papers` | 每日论文推荐总入口 |
| `daily-papers-fetch` | 多源抓取、规范化、去重、排序 |
| `daily-papers-review` | Claude Code 论文筛选和推荐点评 |
| `daily-papers-notes` | 推荐论文笔记生成和链接回填 |
| `paper-reader` | 单篇论文精读和双语笔记生成 |
| `topic-research` | 研究领域/方向调研，只更新候选 summary |

共享 Python 工具位于 `skills/_shared/`。安装到 Claude Code 后，它会变成 `~/.claude/skills/_shared/` 或 `<project>/.claude/skills/_shared/`。

## 目录结构

```text
.
├── README.md                # GitHub 项目说明
├── skills/                  # Claude Code 可安装内容，安装时平铺到 .claude/skills
│   ├── _shared/             # 共享配置、schema、抓取器、summary 生成器
│   ├── daily-papers/        # 每日论文抓取和富化脚本
│   ├── daily-papers-fetch/  # 抓取阶段 Claude Code skill
│   ├── daily-papers-review/ # 筛选点评 Claude Code skill
│   ├── daily-papers-notes/  # 笔记生成 Claude Code skill
│   ├── paper-reader/        # 单篇论文精读 skill 和 Zotero daemon
│   └── topic-research/      # 研究方向调研 skill
└── tests/                   # Python 单元测试
```

## 安装到 Claude Code

### 1. 安装 Claude Code 本体

如果还没有安装 Claude Code，先安装官方 CLI：

```bash
npm install -g @anthropic-ai/claude-code
claude --version
```

首次使用时进入任意项目目录启动 Claude Code，并按提示登录：

```bash
cd /path/to/your/project
claude
```

### 2. 安装 ScholarFlow skills

Claude Code 会读取这些位置的 skill：

- 个人级：`~/.claude/skills/<skill-name>/SKILL.md`，所有项目可用
- 项目级：`<project>/.claude/skills/<skill-name>/SKILL.md`，只对当前项目可用

本仓库包含多个 skills 和共享脚本，因此需要安装整个 ScholarFlow 目录集合，而不是只复制某一个 `SKILL.md`。

仓库里的 `skills/` 是源目录。安装时要把 `skills/` 里面的内容平铺复制到 Claude Code 的 skills 目录，而不是把整个仓库 clone 到 `~/.claude/skills`。

#### 一行安装：个人级 skills

适合大多数用户。安装后，在任何 Claude Code 项目里都能触发 ScholarFlow：

```bash
mkdir -p ~/.claude/skills && \
tmp_dir="$(mktemp -d)" && \
git clone https://github.com/CHB-learner/scholarflow-claude-skills.git "$tmp_dir/scholarflow-claude-skills" && \
rsync -a "$tmp_dir/scholarflow-claude-skills/skills/" ~/.claude/skills/ && \
rm -rf "$tmp_dir"
```

安装后确认：

```bash
find ~/.claude/skills -maxdepth 2 -name SKILL.md | sort
```

应该能看到：

```text
~/.claude/skills/daily-papers/SKILL.md
~/.claude/skills/daily-papers-fetch/SKILL.md
~/.claude/skills/daily-papers-notes/SKILL.md
~/.claude/skills/daily-papers-review/SKILL.md
~/.claude/skills/paper-reader/SKILL.md
~/.claude/skills/topic-research/SKILL.md
```

#### 一行安装：项目级 skills

如果只想让某个项目使用 ScholarFlow，在该项目根目录运行：

```bash
mkdir -p .claude/skills && \
tmp_dir="$(mktemp -d)" && \
git clone https://github.com/CHB-learner/scholarflow-claude-skills.git "$tmp_dir/scholarflow-claude-skills" && \
rsync -a "$tmp_dir/scholarflow-claude-skills/skills/" .claude/skills/ && \
rm -rf "$tmp_dir"
```

安装后确认：

```bash
find .claude/skills -maxdepth 2 -name SKILL.md | sort
```

下面是更适合长期维护的安装方式。

#### 长期维护方式：保留仓库工作副本，再同步到 Claude Code

适合需要经常 `git pull` 更新的用户：

```bash
git clone https://github.com/CHB-learner/scholarflow-claude-skills.git ~/scholarflow-claude-skills
mkdir -p ~/.claude/skills
rsync -a ~/scholarflow-claude-skills/skills/ ~/.claude/skills/
```

后续更新：

```bash
cd ~/scholarflow-claude-skills
git pull
rsync -a skills/ ~/.claude/skills/
```

不要把整个仓库 clone 到 `~/.claude/skills`，否则路径会变成 `~/.claude/skills/skills/topic-research/SKILL.md`，Claude Code 发现不到这些 skills。

### 3. 确认 Claude Code 能看到 skill

重启 Claude Code，或退出后重新运行：

```bash
claude
```

然后在 Claude Code 中输入类似请求：

```text
调研 RNA 序列设计 方向最近的论文
读一下 https://arxiv.org/abs/2605.18747
```

如果 Claude Code 能按 `topic-research` 或 `paper-reader` 的流程响应，说明安装成功。

## 配置

先从示例配置创建本地配置：

```bash
cp ~/.claude/skills/_shared/user-config.example.json ~/.claude/skills/_shared/user-config.local.json
```

然后编辑这些字段：

- `paths.obsidian_vault`：Obsidian vault 根目录
- `paths.daily_papers_folder`：每日论文推荐目录
- `paths.research_fields_folder`：研究方向目录
- `paths.zotero_db`：Zotero SQLite 数据库路径
- `paths.zotero_storage`：Zotero storage 目录
- `daily_papers.keywords`：每日推荐关键词
- `research_fields`：研究方向关键词

本地配置文件默认被 git 忽略，不会提交到仓库。

## 推荐工作流

### 1. 每日论文推荐

在 Claude Code 里直接说：

```text
今日论文推荐
过去一周论文推荐
跑一下论文抓取
跑一下论文点评
跑一下论文笔记
```

默认输出到：

```text
{obsidian_vault}/{daily_papers_folder}/{month}月/{MMDD}/
```

### 2. 研究方向调研

在 Claude Code 里说：

```text
调研过去一年 Agentic RL 的论文
调研 RNA 序列设计 方向最近的论文
看看扩散模型有什么新文章
```

`topic-research` 只做轻量调研：

- 生成检索关键词
- 多源抓取候选
- 去重和相关性筛选
- 写入 `{Research_Fields}/{方向}/_meta/topic_papers.json`
- 更新 `{Research_Fields}/{方向}/summary.md`

调研阶段不会下载 PDF，不会抽图，不会调用 `paper-reader`，也不会生成深度笔记。

### 3. 指定论文精读

用户明确指定论文后才会精读：

```text
读一下 RiboSphere
精读 Code as Agent Harness
生成笔记 https://arxiv.org/abs/2605.18747
```

如果只说：

```text
读一下
```

`paper-reader` 应只列出 summary 里的 `待精读` 候选，提示用户指定论文，不自动选择论文开始深读。

## summary.md 规则

研究方向的 `summary.md` 只由 ScholarFlow 维护自动论文列表区块：

```markdown
<!-- scholarflow:paper-list:start -->
...
<!-- scholarflow:paper-list:end -->
```

自动区块之外的内容都视为用户手写内容，更新时必须保留。

自动表格列固定为：

```markdown
| 发布时间 | 论文 | 笔记 | 代码 | 来源 | 备注 |
```

规则：

- summary 最多展示 50 篇候选论文，完整候选和筛选记录保存在 `_meta/`。
- 未精读论文的笔记列显示 `待精读`。
- 已精读论文的笔记列显示 EN/ZH Obsidian 链接。
- 论文名优先链接本地 PDF；没有 PDF 时链接 arXiv 或来源页。
- 代码列只从候选元数据和摘要中快速抽取 GitHub/Project 链接，不逐篇联网深搜。
- 备注列永远留空，供用户人工填写。

## Python 脚本

运行测试：

```bash
python3 -m unittest discover -s tests
```

直接运行多源抓取：

```bash
python3 skills/daily-papers/multi_source_fetch.py \
  --topic "RNA inverse folding" \
  --queries-json '["RNA inverse folding", "RNA design"]' \
  --since-year 2021 \
  --max-results 100 \
  --sources auto \
  --output /tmp/scholarflow/candidates.json
```

重新生成研究方向 summary：

```bash
python3 skills/_shared/generate_research_field_mocs.py [vault_path]
```

## 依赖

- Claude Code，并启用 skills 支持
- Python 3.10 或更新版本
- 可访问论文来源 API 的网络环境
- `curl`
- Poppler 工具：`pdftotext`、`pdfimages`
- 可选：本地 Zotero 数据库和 storage，用于 `skills/paper-reader/paper_daemon.py`

## 重要约束

- 本仓库是 Claude Code skill 包，不是通用命令行产品。
- 调研阶段只更新候选索引和 summary，不自动精读。
- 精读必须由用户明确指定论文标题、方法名、arXiv URL 或 PDF。
- 不要覆写用户手写的 `summary.md` 内容。
- 不要把临时抓取脚本的原始结果直接写入 summary。
- 不要自动填写 summary 的备注列。
