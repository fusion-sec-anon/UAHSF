# Source Code
This folder contains the core source code for the UAHSF artifact.

## Directory layout

```text
src/
├── bert/                             # BERT-based SBR scorer
├── data/                             # data loading and schema normalization utilities
├── evaluation/                       # pd, pf, and g-measure
├── fusion/                           # uncertainty-weighted BERT/LLM fusion
├── llm/                              # LLM client, output parser, and prompt payload builder
├── uncertainty/                      # local conflict and global semantic incompleteness modules
├── utils/                            # config loading and random seed setup
├── pipeline.py                       # UAHSF inference pipeline
├── configs/
│   └── default.yaml                  # default artifact configuration
├── scripts/
│   ├── run_inference.py              # run UAHSF-style inference
│   ├── evaluate_predictions.py       # compute pd / pf / g-measure
│   └── run_ablation.py               # run ablation study
├── requirements.txt
└── README.md
```
## Installation

From the repository root:

```bash
python -m pip install -r src/requirements.txt
export PYTHONPATH="$PWD/src:$PYTHONPATH"
```

For Windows PowerShell:

```powershell
$env:PYTHONPATH="$PWD/src;$env:PYTHONPATH"
```

Optional dependencies may be required for specific backends:

```bash
# Optional: OpenAI-compatible LLM backend
pip install openai

# Optional: dependency parsing / SRL backends for CWE causal-fragment extraction
pip install spacy stanza
```

If using spaCy, install an English model:

```bash
python -m spacy download en_core_web_sm
```

## Quick start

```bash
python -m pip install -r requirements.txt
python scripts/run_inference.py \
  --config configs/default.yaml \
  --input datasets/*.csv \
  --output results/predictions.csv \
  --dry-run
python scripts/evaluate_predictions.py --pred results/predictions.csv
```
