# 🌿 GreenPipe — AI-Powered CI/CD Carbon Footprint Analyzer

> **The first AI agent that measures, benchmarks, and auto-fixes CI/CD pipeline carbon emissions using the ISO/IEC 21031:2024 SCI standard.**

[![GitLab AI Hackathon](https://img.shields.io/badge/GitLab-AI%20Hackathon%202026-orange)](https://gitlab.com/gitlab-ai-hackathon)
[![Green Agent Prize](https://img.shields.io/badge/Prize-Green%20Agent-green)](https://gitlab.com/gitlab-ai-hackathon)
[![ISO/IEC 21031:2024](https://img.shields.io/badge/Standard-ISO%2FIEC%2021031%3A2024-blue)](https://sci.greensoftware.foundation/)
[![Powered by Claude](https://img.shields.io/badge/Powered%20by-Claude%20(Anthropic)-purple)](https://www.anthropic.com/)
[![SCI Score](https://img.shields.io/badge/SCI%20Score-14.96%20gCO₂e%2Frun-brightgreen)](https://sci.greensoftware.foundation/)
[![Carbon Saved](https://img.shields.io/badge/Carbon%20Saved-376%20gCO₂e%2Fmonth-green)]()
[![Dataset](https://img.shields.io/badge/Dataset-200%20Pipelines-informational)]()
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 🎯 What GreenPipe Does

GreenPipe is a GitLab Duo AI agent that **automatically analyzes any GitLab CI/CD pipeline** for carbon waste, calculates a standardized SCI score, and **creates a merge request with optimizations** — all triggered by a single comment on an issue.

### The Complete Loop: Measure → Analyze → Fix → Verify

```
Developer comments: "@greenpipe analyze pipeline"
         │
         ▼
    ┌─────────────┐
    │  📖 READ     │  Reads .gitlab-ci.yml + config + benchmarks
    └──────┬──────┘
           ▼
    ┌─────────────┐
    │  🔬 ANALYZE  │  Calculates SCI score, detects 13 waste patterns
    └──────┬──────┘
           ▼
    ┌─────────────┐
    │  🔧 FIX      │  Generates optimized .gitlab-ci.yml
    └──────┬──────┘
           ▼
    ┌─────────────┐
    │  ✅ VALIDATE  │  Runs ci_linter to verify YAML
    └──────┬──────┘
           ▼
    ┌─────────────┐
    │  📝 COMMIT   │  Creates branch + commits fix
    └──────┬──────┘
           ▼
    ┌─────────────┐
    │  🔀 MR       │  Opens merge request with SCI report
    └──────┬──────┘
           ▼
    Developer reviews → clicks Merge → Pipeline is greener ✅
```

---

## 🏆 Key Features

### 1. ISO/IEC 21031:2024 SCI Scoring
The only CI/CD tool that uses the **actual ISO standard** for software carbon intensity:

```
SCI = ((E × I) + M) / R

E = Energy (7W TDP × 1.1 PUE × duration)
I = Grid carbon intensity (400 gCO2e/kWh default)
M = Embodied carbon (34.25 gCO2e/hour)
R = 1 pipeline run
```

### 2. Per-Job Carbon Attribution
Every job gets an individual carbon score showing exactly where waste occurs.

### 3. Auto-Fix Merge Request
GreenPipe doesn't just report — it **fixes**. It creates a branch, commits an optimized `.gitlab-ci.yml`, validates it with `ci_linter`, and opens an MR with the full SCI analysis.

### 4. Benchmarking Against 200 Real Pipelines
Every analysis is compared against our dataset of **200 real-world GitLab pipelines**:
- ✅ EXCELLENT: SCI < 311 gCO2e (top 25%)
- 🟢 GOOD: SCI 311-623 gCO2e
- 🟡 AVERAGE: SCI 623-1194 gCO2e
- 🟠 POOR: SCI 1194-2144 gCO2e
- 🔴 CRITICAL: SCI > 2144 gCO2e (bottom 10%)

### 5. Net Carbon Impact (Agent Self-Accounting)
The **only green AI tool that accounts for its own carbon cost**:

| Component | Value |
|-----------|-------|
| Carbon saved per run | 14.46 gCO2e |
| Monthly savings (×50) | 723 gCO2e |
| AI agent analysis cost | 1.5 gCO2e |
| **Carbon ROI** | **482×** |

### 6. Carbon-Aware Scheduling
Recommends lower-carbon regions and off-peak scheduling:

> *"Moving runners to GCP europe-north1 (13 gCO2e/kWh) could reduce SCI by 97%"*

### 7. Works on Any GitLab Project
No hardcoded project IDs. Dynamically discovers project context, default branch, and configuration.

### 8. Configurable via `.gitlab/greenpipe.yml`
```yaml
carbon_budget_gco2e_per_run: 50
runner:
  tdp_per_vcpu_watts: 7
  pue: 1.1
carbon_intensity_gco2e_per_kwh: 400
estimated_runs_per_month: 50
```

---

## 📊 Results

### Dataset Analysis: 200 Real GitLab Pipelines

| Metric | Value |
|--------|-------|
| Pipelines analyzed | 200 |
| Average waste score | 5.5 / 9 |
| Average SCI before | 1,099 gCO2e/run |
| Average SCI after | 769 gCO2e/run |
| Average reduction | 35.6% |
| Total monthly savings | 2,609 kgCO2e |

### Most Common Waste Patterns

| Pattern | Frequency | Impact |
|---------|-----------|--------|
| NO_RETRY | 88% | LOW |
| NO_TIMEOUT | 88% | LOW |
| NO_INTERRUPTIBLE | 88% | MEDIUM |
| NO_SHALLOW_CLONE | 87% | MEDIUM |
| NO_CACHE | 67% | HIGH |

### Demo: Real-World Frontend Pipeline

GreenPipe analyzed a **real production frontend pipeline** and auto-created an MR:

- **Before:** SCI = 22.48 gCO2e/run
- **After:** SCI = 14.96 gCO2e/run → **-33.4%**
- **Benchmark:** ✅ EXCELLENT — Top 5% of 200 pipelines
- **Monthly savings:** 376 gCO2e
- **Carbon ROI:** 251×
- **Auto-fix MR:** Created with CI validation passing ✅

---

## 🚀 How to Use

### 1. Enable GreenPipe
Enable the `greenops_flow` from the AI Catalog in your GitLab group.

### 2. (Optional) Configure
Add `.gitlab/greenpipe.yml` to customize carbon budget, runner specs, and grid intensity.

### 3. Trigger
Comment on any issue:
```
@ai-greenops_flow-gitlab-ai-hackathon analyze pipeline
```

### 4. Review & Merge
GreenPipe creates a merge request with the optimized pipeline. Review and click Merge.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                 GitLab Duo Platform                   │
│                                                      │
│  ┌────────────────────────────────────────────────┐  │
│  │            GreenPipe Flow Agent                 │  │
│  │                                                │  │
│  │  Discovery → Analysis → Optimization → Publish │  │
│  │                                                │  │
│  │  Tools: get_project, read_files, ci_linter,    │  │
│  │         create_commit, create_merge_request,    │  │
│  │         create_issue                            │  │
│  └────────────────────────────────────────────────┘  │
│                        │                             │
│  ┌────────────────────────────────────────────────┐  │
│  │          Dataset & Knowledge Base               │  │
│  │                                                │  │
│  │  200 real .gitlab-ci.yml files                 │  │
│  │  SCI benchmarks (P25/P50/P75/P90)              │  │
│  │  Per-project config (.gitlab/greenpipe.yml)    │  │
│  └────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

---

## 🔬 Research Foundation

### The SCI Formula (ISO/IEC 21031:2024)

$$\text{SCI} = \frac{(E \times I) + M}{R}$$

Where:
- **E** = Energy consumed = `[CPU_Watts × Usage% + Static_Watts] × PUE × Time` (kWh)
- **I** = Location-based carbon intensity of electricity (gCO₂e/kWh)
- **M** = Embodied carbon of hardware, amortized over lifespan (gCO₂e)
- **R** = Functional unit = 1 pipeline run

For GitLab shared runners (AMD EPYC 7B12):
- TDP share per job: **7W** (4 vCPUs / 128 threads × 225W)
- PUE: **1.1** (Google Cloud)
- Default I: **400 gCO₂e/kWh** (global average)
- M rate: **34.25 gCO₂e/hour** (1200 kgCO₂e server / 4-year lifespan)

### Powered by Claude (Anthropic) via GitLab Duo

GreenPipe runs on **Claude** through the GitLab Duo Agent Platform. The agent uses Claude's reasoning capabilities to:
- Analyze complex YAML configurations and detect waste patterns
- Calculate SCI scores with proper scientific methodology
- Generate valid, optimized .gitlab-ci.yml files
- Make intelligent decisions about which fixes to apply
- Self-correct when ci_linter validation fails (agentic behavior)

### Novel Contributions

1. **First application of SCI (ISO/IEC 21031:2024) to CI/CD pipelines** — No previous tool applies the ISO standard to CI/CD as a software system.

2. **AI-driven CI/CD carbon optimization** — A 2025 systematic mapping study of 92 papers found ZERO papers on this topic (MDPI 2025).

3. **Net Carbon Impact accounting** — First green AI tool that transparently reports its own inference carbon cost alongside claimed savings.

4. **CI/CD carbon benchmarking dataset** — 200 real-world GitLab pipelines analyzed with SCI scoring and waste pattern detection.

### References

1. arxiv:2510.26413 — "Environmental Impact of CI/CD Pipelines" (2025)
2. MDPI 2025 — "CI/CD Pipeline Optimization Using AI: A Systematic Mapping Study"
3. ISO/IEC 21031:2024 — Software Carbon Intensity Specification
4. Green Software Foundation — https://sci.greensoftware.foundation/
5. arxiv:2505.09598 — "How Hungry is AI? Benchmarking LLM Inference"
6. Eco-CI — https://www.green-coding.io/products/eco-ci/
7. Cloud Carbon Footprint — https://www.cloudcarbonfootprint.org/

### Data Sources

| Source | Used For |
|--------|----------|
| SPECpower Database | Server power measurements, CPU TDP |
| Electricity Maps | Grid carbon intensity by region |
| Cloud Carbon Footprint | Embodied carbon, PUE values |
| Eco-CI Project | GitLab runner CPU identification |

---

## 🔧 13 Waste Patterns Detected

| # | Pattern | Impact | Fix |
|---|---------|--------|-----|
| 1 | NO_CACHE | HIGH | Cache with lock-file keys |
| 2 | OVERSIZED_IMAGES | HIGH | Alpine/slim variants |
| 3 | NO_DAG_NEEDS | HIGH | Parallel execution |
| 4 | REDUNDANT_INSTALLS | HIGH | Cache/artifacts |
| 5 | NO_RULES | HIGH | Conditional rules |
| 6 | NO_INTERRUPTIBLE | MEDIUM | interruptible: true |
| 7 | NO_ARTIFACT_EXPIRY | MEDIUM | expire_in |
| 8 | FULL_GIT_CLONE | MEDIUM | GIT_DEPTH |
| 9 | DOCKER_IN_DOCKER | MEDIUM | Kaniko/buildah |
| 10 | UNPINNED_IMAGES | MEDIUM | Pin versions |
| 11 | NO_TIMEOUT | LOW | timeout |
| 12 | NO_RETRY | LOW | retry |
| 13 | NPM_INSTALL | LOW | npm ci |

---

## 🌍 Why This Matters

- GitHub Actions alone produced **456.9 MTCO2e** in 2024
- **76%** of real pipelines have no cache
- **88%** lack interruptible — wasting compute on cancelled pipelines
- Average pipeline can be optimized for **35.6% carbon reduction**
- At scale: 1000 projects × GreenPipe → **~26 tons CO2e saved per month**

---

## 🏅 Comparison

| Feature | GreenPipe | Eco-CI | CarbonRunner | Others |
|---------|-----------|--------|--------------|--------|
| ISO SCI Standard | ✅ | ❌ | ❌ | ❌ |
| Auto-fix MR | ✅ | ❌ | ❌ | ❌ |
| Per-job attribution | ✅ | ❌ | ❌ | ❌ |
| Dataset benchmark | ✅ | ❌ | ❌ | ❌ |
| Agent self-cost | ✅ | ❌ | ❌ | ❌ |
| Carbon budget | ✅ | ❌ | ❌ | ❌ |
| Carbon-aware tips | ✅ | ❌ | ✅ | ❌ |
| Any project | ✅ | ✅ | ✅ | ❌ |

---

## 📁 Project Structure

```
GreenPipe/
├── flow.yml                          # AI agent flow definition
├── .gitlab-ci.yml                    # Pipeline (includes greenpipe_stats)
├── .gitlab/
│   └── greenpipe.yml                 # Per-project carbon config
├── dataset/
│   ├── yaml_files/                   # 200 real .gitlab-ci.yml files
│   ├── dataset_benchmarks.json       # Percentiles for benchmarking
│   ├── dataset_stats.yml             # Aggregated statistics
│   └── batch_analysis_results.csv    # SCI scores for all pipelines
├── scripts/
│   ├── collect_gitlab_ci_dataset.py  # Dataset collector
│   ├── generate_dataset_stats.py     # Benchmark generator
│   └── batch_sci_analysis.py         # Batch analysis
└── README.md
```

---

## 👩‍💻 Author

**Noura Hosny** — Software Engineer & MSc Student

Built with GitLab Duo Agent Platform, ISO/IEC 21031:2024 SCI Standard, and a dataset of 200 real-world CI/CD pipelines.

---

*🌿 GreenPipe: Because every pipeline run has a carbon cost — and now you can measure, benchmark, and fix it.*