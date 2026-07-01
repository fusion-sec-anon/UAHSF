# UAHSF

[![Artifact](https://img.shields.io/badge/artifact-public%20package-6f42c1?style=flat-square)](#)
[![Datasets](https://img.shields.io/badge/artifacts-datasets-blue?style=flat-square)](datasets/)
[![Uncertainty](https://img.shields.io/badge/artifacts-uncertainty_quantification-9cf?style=flat-square)](uncertainty_quantification/)
[![Prompts](https://img.shields.io/badge/artifacts-prompts-brightgreen?style=flat-square)](prompts/)
[![Source Code](https://img.shields.io/badge/source-code-orange?style=flat-square)](src/)
[![Toolkit](https://img.shields.io/badge/artifacts-toolkit-ff69b4?style=flat-square)](toolkit/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)

**📄 UAHSF: Uncertainty-Aware Hierarchical Semantic Fusion for Reliable Security Bug Report Detection**

This repository hosts an anonymous artifact package accompanying the UAHSF paper. It contains the  **processed datasets**, **uncertainty resources**, **prompt assets**, **source code** and **toolkit** used in the study.

---

## Highlights

- 🗂️ **Datasets (7 projects)**: fully processed, ready-to-use tables with a documented split protocol (`datasets/`).
- 🔍 **Uncertainty resources**: CWE-derived security terms, CWE Top-25 pattern artifacts, and FARSEC-style cross words (`uncertainty_quantification/`).
- 🧠 **Prompts**: UAHSF uncertainty-aware template + baselines (0/1/few-shot) + prompt-only ablations (`prompts/`).
- 🧩 **Source code**: Core implementation of UAHSF modules and entry points for reproducing the UAHSF workflow (`src/`).
- 🛠 **Toolkit**: A lightweight visualization toolkit for exploring the UAHSF workflow (`toolkit/`). Try the UI demo via GitHub Pages: [UAHSF UI Demo](https://fusion-sec-anon.github.io/UAHSF/toolkit/uahsf_ui_demo.html).

---

## Repository map

```text
.
├── datasets/                         # processed datasets + split specification
├── uncertainty_quantification/       # CWE patterns / CWE terms / cross words
├── prompts/                          # UAHSF prompt, baselines, and prompt ablations
├── src/                              # source code for UAHSF core modules
├── toolkit/                          # visualization demo and lightweight utilities
├── LICENSE
└── README.md
```

---

## What is included

### 1) 🗂️ Datasets — `datasets/`
Processed datasets for all projects are provided as spreadsheet files.  
See `datasets/README.md` and `datasets/SPLIT_SPEC.md` for format and split protocol.

### 2) 🔍 Uncertainty quantification resources — `uncertainty_quantification/`
This folder contains the public resources used to construct and support UAHSF’s uncertainty signals:

- **CWE Top-25 pattern artifacts** (`cwe_patterns/`) used to build the pattern set P_CWE
- **CWE-derived security terms** (`security_keywords/`) used to form the security keyword reference set
- **Security cross words** (`security_cross_words/`) packaged as indices for multi-dataset use

Each subfolder includes a dedicated README describing files and intended usage.

### 3) 🧠 Prompts — `prompts/`
Prompts are organized in a paper-aligned layout:

- `prompts/uahsf/` — UAHSF uncertainty-aware prompt template, schemas, parsing rules, and inference parameters
- `prompts/baseline/` — ChatGPT-FS prompts in **zero-shot / one-shot / few-shot** settings
- `prompts/ablations/` — prompt-only variants removing a specific injected signal


### 4) 🧩 Source code — `src/`
The core components of UAHSF, including local semantic conflict estimation, global semantic completeness modeling and uncertainty-weighted prediction fusion.


### 5) 🛠 Toolkit — `toolkit/`
The toolkit provides a lightweight visualization interface and utility scripts for exploring the UAHSF workflow. The UI demo (`toolkit/uahsf_ui_demo.html`) is intended to provide an intuitive view of how UAHSF processes a bug report.

---

## License

See `LICENSE`.
