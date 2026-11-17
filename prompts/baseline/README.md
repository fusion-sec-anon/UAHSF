# ChatGPT-FS baseline prompt assets

This folder provides baseline prompt templates for SBR detection in three settings:
- `zero_shot/` (k=0 demonstrations)
- `one_shot/` (k=1 demonstration; uses the first example per dataset)
- `few_shot/` (k=5 demonstrations)

## Examples
`example/example.json` stores five labeled examples for each dataset.

## How templates use examples
Each `template.json` specifies a demo-selection rule and placeholder bindings:
- Zero-shot: no demonstrations.
- One-shot: fill `DEMO_1_*` from `examples[0]` for the chosen dataset.
- Few-shot: fill `DEMO_1_*` ... `DEMO_5_*` from `examples[0..4]` for the chosen dataset.

Only `DATASET` and `BUG_REPORT_TEXT` are required at runtime; demonstrations are resolved via `example.json`.
