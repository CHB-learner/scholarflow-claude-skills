---
title: "{Title}"
method_name: "{MethodName}"
authors: [{Authors}]
year: {Year}
venue: {Venue}
tags: [{tags}]
arxiv_id: "{arxiv_id}"
created: {date}
---

# Paper Notes: {Title}

## Metadata

| Field | Content |
|-------|---------|
| Authors | {Authors} |
| Institution | {Affiliations} |
| Date | {Month Year} |
| Links | [arXiv]({arxiv_url}) | [Code]({code_url}) |

---

## One-Sentence Summary

> {Core contribution in one sentence, under 50 words}

---

## Core Contributions

1. **{Contribution 1 Title}**: {Detailed description with specific numbers/methods}
2. **{Contribution 2 Title}**: {Detailed description with specific numbers/methods}
3. **{Contribution 3 Title}**: {Detailed description with specific numbers/methods}
4. **{Contribution 4 Title}**: {Detailed description with specific numbers/methods}
5. **{Contribution 5 Title}**: {Detailed description with specific numbers/methods}

---

## Background

### Problem Formulation

**Mathematical definition of the problem**:

{Formal problem statement with mathematical notation}

**Design space analysis**:

$$
\text{{DesignSpaceSize}} = {exponential/formula description}
$$

{Explain why this makes the problem hard}

### Limitations of Existing Methods

| Method | Approach | Limitation |
|--------|----------|------------|
| {Method 1} | {approach} | {specific limitation} |
| {Method 2} | {approach} | {specific limitation} |
| {Method 3} | {approach} | {specific limitation} |

**Key gap in the field**: {What is missing that this paper addresses}

### Motivation

{Why do the authors believe their approach succeeds where others fail? What is the key insight?}

---

## Method

### Architecture

| Component | Specification |
|-----------|---------------|
| Model Type | {e.g., Transformer encoder-decoder} |
| Layers | {number} |
| Hidden Size | {dimension} |
| Parameters | {count with M/B suffix} |
| Pre-training Data | {size and source} |

**Input/Output**:
- **Input**: {description}
- **Output**: {description}

### Training Objective

$$
\mathcal{L} = {training loss formula with full notation}
$$

{Explain each term in the loss function}

### Key Components

#### Component 1: {Name}

**Design motivation**: {Why was this component needed? What problem does it solve?}

**Implementation**:
- {Technical detail 1}
- {Technical detail 2}
- {Technical detail 3}

#### Component 2: {Name}

**Design motivation**: {Why was this component needed? What problem does it solve?}

**Implementation**:
- {Technical detail 1}
- {Technical detail 2}
- {Technical detail 3}

#### Component 3: {Name}

**Design motivation**: {Why was this component needed? What problem does it solve?}

**Implementation**:
- {Technical detail 1}
- {Technical detail 2}
- {Technical detail 3}

---

## Key Equations

### Equation 1: {Name}

$$
{LaTeX equation}
$$

**Purpose**: {What does this equation represent or compute?}

**Derivation** (if applicable): {How was this derived?}

**Symbol Description**:
| Symbol | Meaning | Unit/Range |
|--------|---------|------------|
| $x$ | {description} | {range} |
| $y$ | {description} | {range} |
| $\theta$ | {description} | {range} |
| $\lambda$ | {description} | {range} |

### Equation 2: {Name}

$$
{LaTeX equation}
$$

**Purpose**: {What does this equation represent or compute?}

**Symbol Description**:
| Symbol | Meaning | Unit/Range |
|--------|---------|------------|
| $f$ | {description} | {range} |
| $\nabla$ | {description} | {range} |

### Equation 3: {Name}

$$
{LaTeX equation}
$$

**Purpose**: {What does this equation represent or compute?}

**Symbol Description**:
| Symbol | Meaning | Unit/Range |
|--------|---------|------------|
| $\pi$ | {description} | {range} |
| $\mathbb{E}$ | {description} | {range} |

---

## Key Figures

### Figure 1: {Title}

![[pngs/fig1.png]]

**Caption**: {Full figure caption from the paper}

**What to observe**: {Key insights visible in this figure}

### Figure 2: {Title}

![[pngs/fig2.png]]

**Caption**: {Full figure caption from the paper}

**What to observe**: {Key insights visible in this figure}

### Figure 3: {Title}

![[pngs/fig3.png]]

**Caption**: {Full figure caption from the paper}

**What to observe**: {Key insights visible in this figure}

---

## Experiments

### Setup

| Setting | Value |
|---------|-------|
| Hardware | {GPU型号和数量} |
| Training Time | {时长} |
| Batch Size | {大小} |
| Learning Rate | {lr} |
| Optimizer | {Adam/SGD等} |

### Datasets

| Dataset | Size | Characteristics | Split |
|---------|------|----------------|-------|
| {Dataset1} | {size} | {description} | train/test |
| {Dataset2} | {size} | {description} | test |

### Evaluation Metrics

| Metric | Definition | Why It Matters |
|--------|-----------|-----------------|
| {Metric1} | {formula/description} | {reason} |
| {Metric2} | {formula/description} | {reason} |

### Main Results

{Key numerical results with specific numbers}

**Comparison with baselines**:

| Method | Metric1 | Metric2 | Metric3 |
|--------|---------|---------|---------|
| Baseline1 | {score} | {score} | {score} |
| Baseline2 | {score} | {score} | {score} |
| **Ours** | **{score}** | **{score}** | **{score}** |

**Key findings**:
1. {Finding 1 with specific numbers}
2. {Finding 2 with specific numbers}
3. {Finding 3 with specific numbers}

### Ablation Study

| Configuration | Metric | Δ vs Full |
|--------------|--------|-----------|
| Full Model | {score} | — |
| w/o Component A | {score} | {Δ} |
| w/o Component B | {score} | {Δ} |
| Variant C | {score} | {Δ} |

**Analysis**: {Why each component contributes}

---

## Critical Analysis

### Strengths

1. **{Strength 1}**: {Evidence from the paper}
2. **{Strength 2}**: {Evidence from the paper}
3. **{Strength 3}**: {Evidence from the paper}

### Why This Approach Works

{Deep explanation of the key insights that make this method successful. What design choices were critical?}

### Limitations

1. **{Limitation 1}**: {Specific evidence from the paper}
2. **{Limitation 2}**: {Specific evidence from the paper}

### Why Certain Approaches Failed

{For methods that might seem similar but underperform, explain why this method succeeds where they failed}

### Potential Improvements

1. {Improvement 1}: {How it could address current limitations}
2. {Improvement 2}: {How it could extend to new settings}

---

## Related Work Comparison

| Method | Training | Architecture | Key Difference |
|--------|----------|-------------|----------------|
| {Method 1} | {training approach} | {architecture} | {key difference} |
| {Method 2} | {training approach} | {architecture} | {key difference} |
| **{This paper}** | {training approach} | {architecture} | {key difference} |

---

## Practical Implications

{What are the real-world applications of this work? What does it enable?}

### For RNA Design / {Domain} Practitioners

1. {Practical tip 1}
2. {Practical tip 2}

### Limitations in Practice

1. {Practical limitation 1}
2. {Practical limitation 2}

---

## Quick Reference

> [!summary] {Paper Title}
> - **Core**: {one-sentence core contribution}
> - **Method**: {key method with architecture details}
> - **Results**: {main quantitative results with numbers}
> - **Code**: {GitHub link or "Not available"}

---

*Notes created: {timestamp}*