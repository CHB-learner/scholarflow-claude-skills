---
name: topic-research
description: |
  用户说"调研XXX领域的文章"、"帮我搜索XXX相关论文"、"我想了解一下XXX方向"时使用。
  根据用户输入的主题，用 LLM 生成多样化检索关键词，然后自动抓取、点评、更新 summary 候选列表。
  调研阶段不精读论文，不调用 paper-reader，不下载 PDF，不抽图。

  **触发词**：调研、搜索、了解、看看XX方向、XX领域文章
context: fork
allowed-tools: Bash, Read, Write, Glob, Grep
---

> **开始前**: 先跟用户打个招呼 🐕，确认日期（如"今天是5月19日"）。

# 主题调研（LLM 生成关键词版）

根据用户描述的主题，Claude 自动理解意图并生成多样化检索关键词，然后跑完多源抓取 → 规范化去重 → 相关性筛选 → 点评 → 更新 `summary.md` 候选列表。

**本 skill 是轻量调研入口：不调用 paper-reader，不精读论文，不生成中英双语深度笔记。**

**不要写临时全量抓取脚本直接刷新 summary。** 必须走 `multi_source_fetch.py` 生成候选和诊断文件，再由 Claude 做相关性筛选后只把前 50 篇 `core/adjacent` 候选写入 `_meta/topic_papers.json` 和 `summary.md`。

## Step 0: 读取共享配置

读取 `../_shared/user-config.json`（和 `user-config.local.json` 如果存在）。配置同时兼容新格式 `vault/folders/daily/fields/zotero` 和旧格式 `paths/daily_papers/research_fields`。

显式生成以下变量：
- `VAULT_PATH` — Obsidian 输出根目录
- `RESEARCH_FIELDS_PATH` — 研究方向目录 `{VAULT_PATH}/{research_fields_folder}`，默认 `{VAULT_PATH}/Research_Fields`
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

将关键词写入配置的研究方向字段。如果使用新格式，更新 `fields["{主题}"]`；如果使用旧格式，更新 `research_fields["{主题}"]`。如果该主题已存在则覆盖。

读取现有配置，尽量只更新对应主题的关键词，不要重写用户的其它配置项。

## Step 4: 创建研究方向目录并多源抓取论文

```bash
FIELD_DIR="{VAULT_PATH}/Research_Fields/{主题}"
PAPERS_DIR="{FIELD_DIR}/papers"
META_DIR="{FIELD_DIR}/_meta"
mkdir -p "$PAPERS_DIR" "$META_DIR"
python3 ~/.claude/skills/daily-papers/multi_source_fetch.py \
  --topic "{主题}" \
  --queries-json '["{关键词1}", "{关键词2}", "{关键词3}"]' \
  --since-year {年份下限} \
  --max-results 100 \
  --sources auto \
  --output "$META_DIR/candidates.json"
```

读取 `$META_DIR/candidates.json`，获取规范化、去重、排序后的候选论文。检查 `$META_DIR/source_diagnostics.json` 和 `$META_DIR/dedup_stats.json`，把来源失败和去重情况写入调研记录。

禁止用 ad hoc `for 365 days`、单独 arXiv/HF 循环脚本直接生成 `summary.md`。这些脚本会绕过 ScholarFlow 的去重、筛选、summary 增量更新和候选上限，容易产生几百行噪声候选。

调研方向时不要创建 `Dailypaper/{月份}`、`Dailypaper/{月份}/{DD}` 或其 `_meta` 目录；调研相关中间产物只放在 `{FIELD_DIR}/_meta/`。

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

筛选后只允许把最多 50 篇 `core/adjacent` 论文进入 Research_Fields summary；完整候选和排除记录保留在 `_meta` 诊断文件里，不把原始候选全量塞进 summary。

**锐评要求**：
1. 核心方法：2-3 句话讲清楚方法怎么工作
2. 关键贡献：相比前人有什么新意
3. 锐评：方法有没有硬伤？claim 和 evidence 匹配吗？
4. emoji 判决：🔥=强推，👀=值得关注，⚠️=有硬伤但方向对，💀=灌水，🤡=标题党，💤=无聊

## Step 6: 保存候选索引并更新 Research_Fields

### 6a. 保存候选索引

把筛选后排名最高的最多 50 篇 `core` 和 `adjacent` 相关论文写入：

`{FIELD_DIR}/_meta/topic_papers.json`

每条记录包含：
```json
{
  "title": "论文标题",
  "method_name": "方法名或短标题",
  "date": "YYYY-MM-DD",
  "year": 2026,
  "url": "https://arxiv.org/abs/xxxx",
  "pdf_url": "https://arxiv.org/pdf/xxxx",
  "code_url": "https://github.com/...",
  "label": "core",
  "reason": "一句话相关性理由",
  "source": "arxiv",
  "note_status": "pending"
}
```

如果同一论文已经有笔记，`note_status` 可保持 `pending`；`summary.md` 生成器会根据本地笔记目录自动显示为已精读。

`code_url` 只做快速抽取：优先使用候选源已有的 `github/code_url/repository/project_url/homepage` 字段；如果为空，再从标题、摘要、comment 等元数据中抽取 GitHub 或项目页链接。不要为了补代码链接逐篇联网深搜。

标准候选索引路径是 `{FIELD_DIR}/_meta/topic_papers.json`。不要把新的候选索引写到 `{FIELD_DIR}/topic_papers.json`；根目录旧文件只作为兼容输入。

调研阶段只创建目录和候选索引，不在 `papers/` 下创建论文笔记目录。

### 6b. 更新研究方向 summary

路径：`{FIELD_DIR}/summary.md`（增量更新，禁止整文件覆写）

**重要：`summary.md` 可能包含用户手写的研究判断、备注和额外章节。更新时只能维护 ScholarFlow 自动论文列表区块，必须保留自动区块之外的全部内容。**

自动维护区块边界：
```markdown
<!-- scholarflow:paper-list:start -->
...
<!-- scholarflow:paper-list:end -->
```

更新规则：
- 如果 summary 已有上述标记，只替换标记之间的论文计数和论文列表
- 如果 summary 没有标记但已有 `## 论文列表`，兼容旧格式：替换该章节并加上标记，保留前后用户内容
- 如果 summary 没有 `## 论文列表`，在文件末尾追加自动维护区块
- 用户手写备注应放在自动维护区块之外；自动区块内内容可由 ScholarFlow 重建

格式：
```markdown
---
tags: [MOC, auto-generated, research-field]
generated_by: dailypaper-skills
---

# {主题}

<!-- scholarflow:paper-list:start -->
该研究方向下共有 **{N}** 篇论文。

## 论文列表

| 发布时间 | 论文 | 笔记 | 代码 | 来源 | 备注 |
|----------|------|------|------|------|------|
| 2026.05.02 | [MethodName](arXiv链接) | 待精读 | [GitHub](代码链接) | [arXiv](来源链接) |  |
<!-- scholarflow:paper-list:end -->
```

表格规则：
- 所有 `core/adjacent` 相关论文进入同一张表
- summary 最多显示 50 篇论文，作为人工阅读入口，不做全量候选仓库
- 未精读论文：论文名链接到 arXiv/来源，笔记列显示 `待精读`
- 已精读论文：论文名优先链接本地 PDF，笔记列显示 EN/ZH Obsidian 链接
- 备注列永远留空，由用户人工填写；`label`、`reason`、`hf_upvotes` 等机器字段只保存在 JSON/诊断文件，不写入 summary 表格

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

## Step 7: 完成后告知用户

告知用户：
- 抓取到多少篇候选，筛选出多少篇 `core/adjacent`
- 候选索引保存在：`Research_Fields/{主题}/_meta/topic_papers.json`
- 抓取、去重、筛选诊断文件保存在：`Research_Fields/{主题}/_meta/`
- summary 已更新，未精读论文显示为 `待精读`
- summary 备注列已留空，供用户人工填写
- 运行下一步：`读一下 {论文标题}` 或 `精读 {论文标题}` 可以精读指定论文

## 重要约束

- **不要先要求用户确认关键词**，LLM 生成的就是要用的
- **不要只生成关键词就停下**，继续跑到候选索引和 summary 更新完成
- **调研阶段不调用 paper-reader，不精读论文，不下载 PDF，不抽图**
- **调研阶段不要创建 `Dailypaper/{月份}` 文件夹；中间产物统一放到研究方向 `_meta/` 下**
- **不要把临时脚本结果直接写入 summary.md；必须走 `_meta/topic_papers.json` + summary 生成器**
- **不要自动写 summary 备注列；备注由用户人工维护**
- 主题模糊时，关键词应偏宽泛而非狭窄
- 只有用户明确说 `读一下 {论文标题}`、`精读 {论文标题}` 或 `生成笔记 {论文标题}` 时，才进入 paper-reader 深读流程
