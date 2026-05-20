# 每日论文推荐

这是面向用户的一句话入口。

## 识别用户意图

1. **识别时间范围**：
   - `今日论文推荐`、`每日推荐`、`今日论文` -> 当天
   - `过去3天论文推荐`、`最近3天论文` -> 3 天
   - `过去一周论文推荐`、`看看这周有啥论文` -> 7 天
   - `过去两个月` -> 60 天
   - 其他 N 天 -> 用户指定的 N

2. **识别关键词**：
   - 如果用户指定了关键词（如"大模型评测"、"扩散模型"），使用用户提供的
   - 如果用户没有指定，从 `daily.keywords` 配置获取默认关键词；旧配置 `daily_paper_keywords` 仍兼容

## 执行流程

## 路径契约（必须）

每日论文只能写入一个日期目录：

```text
{DAILY_PAPERS_PATH}/{YYYY-MM-DD}/
```

例如 `Dailypaper/2026-05-20/`。禁止创建或写入任何月份/日期混合目录，包括：

- `Dailypaper/5月/0520/`
- `Dailypaper/5月/520/`
- `Dailypaper/{月份}/{DD}/`
- `Dailypaper/{月份}/{MMDD}/`

执行前必须显式设置并复用：

```bash
DATE_DIR="$(date +%F)"
DAILY_RUN_DIR="{DAILY_PAPERS_PATH}/$DATE_DIR"
META_DIR="$DAILY_RUN_DIR/_meta"
RECOMMENDATION_FILE="$DAILY_RUN_DIR/$DATE_DIR-论文推荐.md"
```

后续抓取、点评、笔记、图片、`_meta` 都只能使用这些变量。不要手写 `5月`、`0520`、`520` 这种路径。

如果发现同一天的旧式目录已经存在，先停止写入并迁移到 `Dailypaper/{YYYY-MM-DD}/`；如果目标目录已有内容，保留目标目录，不要把新内容写回旧式目录。

### Step 1: 关键词丰富化

对每个原始关键词进行丰富化（英文 + 中文变体）：

| 原始关键词 | 丰富化关键词 |
|-----------|-------------|
| 大模型评测 | LLM evaluation, large language model benchmark, foundation model evaluation, 模型评测, 大模型评估 |
| 扩散模型 | diffusion model, score-based model, diffusion generative model, 扩散生成模型 |

丰富化逻辑：
- 每个关键词展开为 4-6 个相关关键词（中英文混合）
- 英文为主（覆盖 arXiv 检索），保留中文（覆盖中文论文）

### Step 2: 多源检索（multi_source_fetch.py）

调用 `multi_source_fetch.py`，传入丰富化后的关键词。输出保存在当天日期目录的 `_meta/` 下，便于复盘：

```bash
python3 scripts/daily-papers/multi_source_fetch.py \
  --topic "每日论文" \
  --queries-json '["{丰富化关键词1}", "{丰富化关键词2}"]' \
  --since-year {年份下限} \
  --max-results 100 \
  --sources auto \
  --output "$META_DIR/candidates.json"
```

输出：
- `_meta/candidates.json`：规范化、去重、排序后的候选论文
- `_meta/source_diagnostics.json`：各来源请求状态
- `_meta/dedup_stats.json`：去重统计
- `_meta/plan.json`：本次 topic / queries / source 配置

### Step 3: Codex 判断相关性（daily-papers-review）

读取 `_meta/candidates.json`，Codex 逐一判断每篇论文是否与关键词相关，输出 `core / adjacent / exclude` 筛选理由并生成推荐点评。

### Step 4: 生成笔记（daily-papers-notes）

对推荐中标记为"🔥 必读"的论文，逐篇生成中英双语笔记。

## 重要约束

- **不要先要求用户手动跑** `跑一下论文抓取 / 点评 / 笔记`
- 这 3 句是内部流水线和调试入口，不是首页主交互
- 如果用户明确只想跑其中一步，再交给对应 skill

## 自动化

- 本 skill 本身是"一步跑完整流水线"的入口
- 如果用户想做本地定时任务，默认也应该触发这一句
