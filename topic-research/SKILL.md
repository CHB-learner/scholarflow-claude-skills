---
name: topic-research
description: |
  用户说"调研XXX领域的文章"、"帮我搜索XXX相关论文"、"我想了解一下XXX方向"时使用。
  根据用户输入的主题，用 LLM 生成多样化检索关键词，然后自动抓取、点评、生成笔记。
  全自动流水线，无需用户干预。

  **触发词**：调研、搜索、了解、看看XX方向、XX领域文章
context: fork
allowed-tools: Bash, Read, Write, Glob, Grep
---

> **开始前**: 先跟用户打个招呼 🐕，确认日期（如"今天是5月19日"）。

# 主题调研（LLM 生成关键词版）

根据用户描述的主题，Claude 自动理解意图并生成多样化检索关键词，然后跑完多源抓取 → 规范化去重 → 相关性筛选 → 点评 → 笔记流水线。

## Step 0: 读取共享配置

读取 `../_shared/user-config.json`（和 `user-config.local.json` 如果存在）。

显式生成以下变量：
- `VAULT_PATH` — Obsidian 库根目录（不含 "papers" 后缀）
- `RESEARCH_FIELDS_PATH` — 研究方向目录 `{VAULT_PATH}/Research_Fields`
- `DAILY_PAPERS_PATH` — 每日推荐目录 `{VAULT_PATH}/Dailypaper`
- `SAVE_MODE` = `"research_field"`（表示保存到领域目录）

## Step 1: 解析用户意图

从用户消息中提取：
- **研究主题**：从用户描述中提取核心主题（如"具身智能"、"扩散模型"、"蛋白质设计"）
- **时间范围**：默认 7 天（"最近"），如果用户指定了具体天数则用用户值

| 用户消息 | 主题 | 天数 |
|---------|------|------|
| 调研过去一周具身智能领域的文章 | 具身智能 | 7 |
| 看看扩散模型有什么新文章 | 扩散模型 | 7 |
| 搜索最近3天机器人抓取方向的论文 | 机器人抓取 | 3 |
| 了解一下mRNA疫苗设计 | mRNA疫苗设计 | 60 |
| 帮我调研具身智能 | 具身智能 | 7 |

## Step 2: LLM 生成多样化关键词

用 LLM 生成 8-15 个关键词（中英文混合），要求：
1. 覆盖主题的多个子方向（不能全是同义词）
2. 英文为主（arXiv 检索主要用英文）
3. 包含中文（覆盖中文论文）
4. 包含变体和缩写（如 sim-to-real, sim2real）
5. 包含上/下游相关方向

**生成示例（用于参考）：**

主题"具身智能" → `embodied AI, robot manipulation, robotic grasping, sim-to-real, sim2real transfer, reinforcement learning robot, vision-language-action, VLA model, robot navigation, mobile manipulation, dextrous manipulation, 具身智能, 机器人操作, 强化学习机器人, 仿真到现实迁移`

主题"扩散模型" → `diffusion model, score-based model, DDPM, DDIM, latent diffusion, text-to-image, image generation, generative model, flow matching, consistency model, diffusion transformer, 扩散模型, 扩散生成, 文生图, 潜在扩散`

**输出格式**：将生成的关键词以逗号分隔列出（不带引号）。

## Step 3: 保存关键词到 user-config.json

将关键词写入 `user-config.json` 的 `research_fields` 字段。如果该主题已存在则覆盖。

读取现有 `user-config.json`，更新 `research_fields["{主题}"]`，写回。

## Step 4: 多源抓取论文

```bash
META_DIR="{DAILY_PAPERS_PATH}/{月份}/{DD}/_meta"
mkdir -p "$META_DIR"
python3 ~/.claude/skills/daily-papers/multi_source_fetch.py \
  --topic "{主题}" \
  --queries-json '["{关键词1}", "{关键词2}", "{关键词3}"]' \
  --since-year {年份下限} \
  --max-results 100 \
  --sources auto \
  --output "$META_DIR/candidates.json"
```

读取 `$META_DIR/candidates.json`，获取规范化、去重、排序后的候选论文。检查 `$META_DIR/source_diagnostics.json` 和 `$META_DIR/dedup_stats.json`，把来源失败和去重情况写入调研记录。

## Step 5: Claude 筛选与点评（风格：毒舌但精准）

读取所有候选论文后，Claude 逐一判断相关性并生成锐评。

**点评人设**：毒舌但眼光极准的 AI 论文审稿人，像 senior researcher，对灌水零容忍。

**判断标准**：
- 论文是否与该主题有实质性关联
- 方法是否针对该领域的问题
- 即使标题含关键词，如果核心方法不相关也应排除

**筛选标签**：
- `core`：直接解决主题或核心子任务，进入主推荐
- `adjacent`：相关但偏背景、工具、综述或旁支，可补充
- `exclude`：不相关、标题蹭词、领域偏移或证据不足

把完整筛选记录保存到 `$META_DIR/screening.json`，每篇包含：
`title`、`label`、`score`、`reason`、`matched_terms`、`negative_hits`。

**锐评要求**：
1. 核心方法：2-3 句话讲清楚方法怎么工作
2. 关键贡献：相比前人有什么新意
3. 锐评：方法有没有硬伤？claim 和 evidence 匹配吗？
4. emoji 判决：🔥=强推，👀=值得关注，⚠️=有硬伤但方向对，💀=灌水，🤡=标题党，💤=无聊

## Step 6: 保存论文文件到 Research_Fields

### 6a. 创建目录结构

```bash
FIELD_DIR="{VAULT_PATH}/Research_Fields/{主题}"
PAPERS_DIR="{FIELD_DIR}/papers"
mkdir -p "{PAPERS_DIR}"
```

### 6b. 保存推荐文件

路径：`{FIELD_DIR}/summary.md`（每次重新生成）

格式：
```markdown
---
tags: [MOC, auto-generated, research-field]
generated_by: dailypaper-skills
---

# {主题}

该研究方向下共有 **{N}** 篇论文。

## 论文列表

| 发布时间 | 论文 | 笔记 | 代码 | 来源 | 备注 |
|----------|------|------|------|------|------|
| ... |
```

同时保留 `_meta/` 中间产物：
```
{FIELD_DIR}/_meta/
├── plan.json
├── candidates.json
├── source_diagnostics.json
├── dedup_stats.json
└── screening.json
```

papers/ 目录下每篇论文的结构：
```
{papers_dir}/{论文名}/
├── pngs/
├── {论文名}_en.md
├── {论文名}_zh.md
└── {论文名}.pdf
```

### 6c. 保存快速导航推荐文件

同时在 Dailypaper 目录下生成一个快速导航文件：

路径：`{DAILY_PAPERS_PATH}/{月份}/{DD}/research-{主题}.md`

内容：
```markdown
---
date: {YYYY-MM-DD}
topic: {主题}
keywords: [{关键词列表}]
tags: [topic-research, auto-generated]
---

# {主题} 论文推荐

调研时间：{YYYY-MM-DD} | 关键词：{主题}

## 分流表

| 等级 | 论文 | 笔记 |
|------|------|------|
| 🔥 必读 | [[论文名]] | [笔记](./papers/{论文名}/{论文名}_zh.md) |
...

## 论文点评

### 1. {论文标题}
- **链接**: [arXiv](url) | [PDF](pdf_url)
- **核心方法**: ...
- **锐评**: ...
- 💡 运行：`读一下 {论文标题}`
...
```

## Step 7: 生成笔记（🔥 必读论文）

对所有 `core` 且在分流表中标记为 🔥 必读的论文，逐篇调用 paper-reader skill 生成中英双语笔记：

每篇笔记的结构（由 paper-reader skill 生成）：
- `{论文名}_en.md`：英文深度笔记
- `{论文名}_zh.md`：中文深度笔记
- `pngs/`：从 PDF 提取的图片

笔记生成完成后，更新 `summary.md` 中的链接。

## Step 8: 完成后告知用户

告知用户：
- 抓取到多少篇论文，其中 🔥🔥👀 各多少
- 推荐文件保存在：`Dailypaper/{月份}/{DD}/research-{主题}.md`
- 笔记保存在：`Research_Fields/{主题}/papers/{论文名}/`
- 运行下一步：`读一下 {论文标题}` 可以精读某篇

## 重要约束

- **不要先要求用户确认关键词**，LLM 生成的就是要用的
- **不要只生成关键词就停下**，继续跑完整流水线
- 主题模糊时，关键词应偏宽泛而非狭窄
- PDF 必须下载（因为 paper-reader 需要）
