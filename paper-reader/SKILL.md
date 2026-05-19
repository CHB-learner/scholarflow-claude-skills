---
name: paper-reader
description: |
  Use when user asks to "read paper", "analyze paper", "summarize paper",
  "读论文", "分析文献", "帮我看一下这篇paper", "论文笔记", or provides a PDF file
  that appears to be an academic paper.

  **重要触发词**: "读一下 XXX"、"精读 XXX"、"生成笔记 XXX"、"帮我读 XXX" → 必须调用此 skill
  **不要触发**: 用户只说"读一下"但没有给论文名、链接或 PDF 时，不启动深读；先列出 summary 中待精读候选让用户选择。
context: fork
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, WebFetch, WebSearch
---

> **开始前**: 先跟用户打个招呼 🐕

# 学术论文阅读助手 (Paper Reader)

专注学术论文深度阅读，生成**中英双语深度笔记**。
笔记保存在 `Research_Fields/{方向}/papers/{论文名}/` 下。

## 核心原则：深度优先

**不是做摘要，是做深度分析。**

笔记要包含：
- 问题的数学形式化（不是"这个论文解决什么问题"而是"用数学符号怎么描述"）
- 设计空间的量化分析（为什么这个问题困难）
- 方法的完整架构规格（参数量、训练目标、组件细节）
- 所有公式的完整符号表
- 批判性分析（为什么有效、为什么失败）
- 与相关工作的系统对比表
- 实际应用意义

## Step 0: 读取共享配置

先读取 `../_shared/user-config.json`，如果 `../_shared/user-config.local.json` 存在，再用它覆盖默认值。

显式生成并在后续统一使用这些变量：

- `VAULT_PATH` — Obsidian 库根目录
- `RESEARCH_FIELDS_PATH` — 研究方向目录 `{VAULT_PATH}/{research_fields_folder}`
- `DAILY_PAPERS_PATH` — 每日推荐目录 `{VAULT_PATH}/{daily_papers_folder}`
- `ZOTERO_DB` — Zotero 数据库路径
- `ZOTERO_STORAGE` — Zotero 存储路径
- `AUTO_REFRESH_INDEXES` — 是否自动刷新索引
- `GIT_COMMIT_ENABLED` — 是否自动 git commit
- `GIT_PUSH_ENABLED` — 是否自动 git push（仅在 GIT_COMMIT_ENABLED=true 时有效）

## 1. 接收论文

### 触发保护

`读一下` 不带论文名、arXiv 链接或 PDF 路径时，不启动深读，不下载 PDF，不调用任何提取图片/全文的流程。

此时应该：
1. 读取当前相关 `Research_Fields/{方向}/summary.md` 或 `_meta/topic_papers.json`
2. 列出 `待精读` / `note_status=pending` 的候选论文
3. 提醒用户使用 `读一下 {论文标题}`、`精读 {论文标题}` 或 `生成笔记 {论文标题}` 指定一篇论文
4. 停止，不要自行选择下一篇

只有用户明确给出论文标题、方法名、arXiv 链接、DOI、URL 或 PDF 路径时，才开始下面的深度阅读流程。

| 输入方式 | 示例 | 处理方法 |
|----------|------|----------|
| PDF 路径 | `/path/to/paper.pdf` | 直接 Read + pdftotext 提取文字 |
| arXiv 链接 | `https://arxiv.org/abs/xxxx` | WebFetch arXiv HTML + PDF |
| 无 PDF | 只有链接 | 先 WebFetch HTML，失败则下载 PDF |

### 论文内容获取

1. **优先 arXiv HTML**：`https://ar5iv.org/html/{arxiv_id}` 或 `https://arxiv.org/html/{arxiv_id}`
2. **下载 PDF**：
```bash
curl -L -o "{save_dir}/{MethodName}.pdf" "https://arxiv.org/pdf/{arxiv_id}.pdf"
```
3. **提取文字**：
```bash
pdftotext -layout {pdf_path} {save_dir}/{MethodName}.txt
```
必须使用 `-layout` 保留公式结构。
4. **提取图片**：
```bash
mkdir -p papers/pngs
pdfimages -png {pdf_path} pngs/
```
这会在 `pngs/` 目录下生成 `img-000.png`, `img-001.png`, ... 等文件。
```

## 2. 深度分析要求

### 问题形式化（必须）

不要只写"解决什么问题"。要用数学符号描述：

```
问题：给定 {输入}，找到 {输出} 使得 {目标函数} 最大/最小
设计空间：|X| = {指数计算}，{解释规模}
约束：{数学约束条件}
```

**设计空间分析示例**：
如果问题是生成序列，设计空间是多少？为什么这让问题困难？

### 方法架构（必须）

| 组件 | 规格 |
|------|------|
| 模型类型 | Transformer/LSTM/GNN等 |
| 层数 | 具体数字 |
| 隐藏维度 | 具体数字 |
| 参数量 | 含 M/B 后缀 |
| 训练数据 | 大小和来源 |

**不要只写"用了 Transformer"，要写具体的配置。**

### 公式文档（必须）

每个公式需要：
1. 完整的 LaTeX 表达式
2. 一句话目的（这个公式计算什么）
3. 符号表（每符号含义、单位、范围）

### 批判性分析（必须）

- **为什么有效**：这篇论文的关键洞察是什么？哪些设计选择是关键的？
- **为什么失败/局限**：论文自己承认的局限、作者没注意到的潜在问题
- **与其他工作的对比**：表格形式对比训练方式、架构、关键差异

## 3. 方向匹配

### 匹配 research_fields

读取 `user-config.json` 中的 `research_fields` 字段，匹配论文方向。

### 保存目录结构

**文件名格式（必须使用方法缩写作为前缀）**：
```
{VAULT_PATH}/Research_Fields/{方向}/papers/{MethodName}/
├── pngs/           # 图片目录（必须）
├── {MethodName}_en.md   # 英文深度笔记（必须）
├── {MethodName}_zh.md   # 中文深度笔记（必须）
└── {MethodName}.pdf     # PDF 原文（必须）
```

例如：`papers/BeeRNA/BeeRNA_en.md`、`papers/BeeRNA/BeeRNA_zh.md`、`papers/BeeRNA/BeeRNA.pdf`。

## 4. 笔记模板

### 英文模板：`assets/paper-note-template-en.md`
### 中文模板：`assets/paper-note-template-zh.md`

**严格遵循模板**，不可简化。

### 模板核心结构（必须包含）

```markdown
## Background
### Problem Formulation
**Mathematical definition**: {formal problem with math notation}
**Design space analysis**: {exponential formula}, {why hard}
### Limitations of Existing Methods
| Method | Approach | Limitation |
### Key Gap

## Method
### Architecture
| Component | Specification |
### Training Objective
{formula with full notation}
### Key Components
#### Component 1: {Name}
**Motivation**: {why needed}
**Implementation**: {technical details}

## Key Equations
### Equation 1: {Name}
$${LaTeX}$$
**Purpose**: {one sentence}
**Symbol Description**:
| Symbol | Meaning | Unit/Range |

## Critical Analysis
### Why This Approach Works
{deep explanation of key insights}
### Limitations
{with specific evidence}
```

## 5. 图片获取

1. **PDF 提取**：
```bash
mkdir -p papers/pngs
pdfimages -png {pdf_path} pngs/
```
这会在 `pngs/` 目录下生成 `img-000.png`, `img-001.png`, ... 等文件。

2. **嵌入图片**：在笔记中用 `![[pngs/img-000.png]]` 引用（不要用 `pngs-000.png`，那是错误的命名）。

图片是必须有的，如果没有提取到图片，说明你没找到。

## 6. 完成后自检

**不是简单 checklist，是深度验证**：

- [ ] 问题是否用数学符号形式化？设计空间是否量化？
- [ ] 架构是否有完整规格（层数/维度/参数量）？
- [ ] 所有公式是否有完整符号表？
- [ ] 批判性分析是否包含"为什么有效/失败"？
- [ ] 是否有与相关工作的系统对比表？
- [ ] 所有 Figure 是否都在 `pngs/` 目录（不是 `pngs-000.png` 这样的命名）？
- [ ] `{MethodName}_en.md` 和 `{MethodName}_zh.md` 是否都是深度版本（不是摘要）？
- [ ] `{MethodName}.pdf` 是否已下载到笔记目录？

## 7. 写完即保存

**每篇论文完成后立即保存，不要等全部结束。**

## 参考文件

- **`references/quality-standards.md`** — 公式/图片/表格详细质量规范
