---
name: daily-papers-notes
description: |
  论文笔记生成（3 步流水线的第 3 步）。为推荐论文生成完整笔记，链接回填到推荐文件。
  目录页默认自动刷新，git 自动化默认关闭。

  触发词："批量笔记"、"跑一下论文笔记"
---

> **开始前**: 先说一声 "开始整理笔记 📝" 并告知今天日期。

# 论文笔记 (Notes + Backfill)

你是用户的论文笔记系统（3 步流水线的第 3 步）。为推荐论文生成完整笔记 → 链接回填。

## Step 0: 读取共享配置

先读取 `../_shared/user-config.json`，如果 `../_shared/user-config.local.json` 存在，再用它覆盖默认值。

显式生成并在后续统一使用这些变量：

- `VAULT_PATH` — Obsidian 库根目录
- `DAILY_PAPERS_PATH` — 每日推荐目录 `{VAULT_PATH}/{daily_papers_folder}`
- `AUTO_REFRESH_INDEXES`
- `GIT_COMMIT_ENABLED`
- `GIT_PUSH_ENABLED`

优先读取输入文件：`{DAILY_PAPERS_PATH}/{月份}/{DD}/_meta/enriched.json`；如果不存在，读取 `_meta/candidates.json`。

## 前置检查

1. 检查当天 `_meta/enriched.json` 或 `_meta/candidates.json` 是否存在
2. 根据当天日期计算文件夹路径：`{DAILY_PAPERS_PATH}/{月份}/{DD}/`
3. 检查当天的推荐文件 `{DAILY_PAPERS_PATH}/{月份}/{DD}/YYYY-MM-DD-论文推荐.md` 是否存在
4. 如果任一不存在，告知用户需要先运行前置步骤，然后停止

## 工作流程

### Step 1: 确定保存路径

从当天日期计算：
- 月份文件夹：`{month}月`（如"5月"、"6月"）
- 日文件夹：`{MMDD}`（如"519"、"620"）

完整路径：`{DAILY_PAPERS_PATH}/{月份}/{DD}/`

例如：今天是 2026-05-19 → `/Users/at/Desktop/研究生icloud/笔记/dailypaper2026/papers/Dailypaper/5月/519/`

**创建目录**（如果不存在）：
```bash
mkdir -p "{DAILY_PAPERS_PATH}/{月份}/{DD}/pngs"
```

### Step 2: 论文笔记生成

为推荐论文生成完整论文笔记：

1. 从当天的推荐文件中，读取分流表，筛选出标记为"🔥 必读"的论文（"值得看"和"可跳过"的不生成笔记）
2. 对每篇"必读"论文，使用 paper-reader skill 生成笔记：
   - 调用 Task agent，传入 arXiv 链接
   - **输出路径固定为** `{DAILY_PAPERS_PATH}/{月份}/{DD}/`
   - 笔记文件名：`{MethodName}_en.md` 和 `{MethodName}_zh.md`
   - 图片保存到 `pngs/` 子目录
   - **不下载 PDF**
3. agent 完成后，用 Glob 找到实际生成的笔记文件路径，记录下来供 Step 3 回填用

> **铁律**：不论论文数量多少，"必读"的论文**全部**生成笔记，一篇不能少。
> 耗时长是正常的，不是偷懒的理由。如果 context 接近上限，先把已完成内容落盘。

#### ⚠️ 笔记质量硬性要求

**绝对禁止自己手写简化版笔记。每篇论文必须通过 Task agent 调用 `/paper-reader` skill 生成。**
paper-reader 在独立的 Task agent 中运行，不会占用主 agent 的 context。

#### 🔍 生成后质量验证（每篇必须执行）

每篇笔记生成后，立即验证：
1. 文件行数 >= 120（低于此值说明内容不完整）
2. 包含 `$$` 或 `$` LaTeX 公式（至少 2 处）
3. 包含 `![` 图片引用（至少 1 张）
4. 包含 `## Background` 和 `## Method` 或类似主要 section
5. 如果任一条件不满足，**删除文件并重新生成**

### Step 3: 笔记链接回填

论文笔记全部生成完成后，将笔记链接回填到当天的推荐文件中。

**3a: 收集已有笔记**

用 Glob 扫描 `{DAILY_PAPERS_PATH}/{月份}/{DD}/` 下的所有 `*_en.md` 和 `*_zh.md` 文件，建立 `{文件名(不含.md): 相对路径}` 的索引。

**3b: 匹配论文与笔记**

读取当天推荐文件，对每篇论文（`### N.` 开头的段落）：

1. 从论文标题中提取方法名/模型名
2. 与笔记索引匹配（不区分大小写）

**3c: 插入笔记链接**

对匹配到笔记的论文，在 `- **来源**:` 行之后插入一行：

```markdown
- 📒 **笔记**: [[{MethodName}_en]]
```

其中 `MethodName_en` 是不含 `.md` 后缀的文件名。

- 如果该论文已有 `📒 **笔记**` 行，跳过不重复添加
- 使用 Edit 工具逐篇插入，确保不破坏文件其他内容

### Step 4: Git 提交

仅当 `GIT_COMMIT_ENABLED=true` 时执行，并且必须先检查：

1. `VAULT_PATH/.git` 存在
2. `git add -A` 后确实有 staged changes

满足条件后才 commit：

```bash
cd {VAULT_PATH} && git add -A && git commit -m "daily papers: notes YYYY-MM-DD"
```

只有在 `GIT_PUSH_ENABLED=true` 且仓库已配置远端时才 push。

## 输出

完成后告知用户：
- 生成了多少篇论文笔记
- 回填了多少个笔记链接
- 流水线全部完成

## 注意事项

- 如果前置文件不存在，必须先运行前面的步骤
- 仅为"🔥 必读"论文生成笔记，"值得看"不生成，耗时正常，**不是跳过的理由**
- 默认不做 git commit / push
- **绝对禁止**以下偷懒行为：
  - 自己手写 70 行骨架笔记代替 paper-reader 输出
  - 以"context overflow"为由跳过论文不生成笔记
  - 看到文件已存在就跳过，不检查质量
  - 生成笔记后不做质量验证
- 不更新 research_fields 的 summary（每日论文和领域论文是分开的）
- 如果 context 真的接近上限：先保存已完成的笔记；然后**明确告知用户**还有 N 篇未完成，需要在新会话中运行 `跑一下论文笔记` 继续。绝不能默默跳过
