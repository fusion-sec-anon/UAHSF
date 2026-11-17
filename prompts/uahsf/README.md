# UAHSF Prompts (Uncertainty-Aware)

This directory contains prompt artifacts for the **LLM reasoning module** in UAHSF.

UAHSF augments the bug report text with uncertainty indicators derived from Phase-1 quantification:
- **Key contradiction terms** with contradiction scores (`S_KWD`, `C_scores`)
- **Global completeness** signals (`M`, matched CWE patterns `P_CWE`)
- **Initial prediction anchor** (`P_BERT`)

The prompt follows the paper’s three-stage procedure:
1) Disambiguate high-contradiction terms in context.
2) Infer missing vulnerability triggers under incompleteness.
3) Produce the final SBR/NSBR judgment with a calibrated likelihood.

## Layout
- `template/uncertainty_aware.{md,json}`  
  Contains the UAHSF uncertainty-aware prompt template in both human-readable and API payload, with placeholders preserved for easy instantiation.

- `schema/{input/output}_schema.json`
  Defines the input/output schemas and lightweight parsing conventions for assembling UAHSF prompt fields and normalizing LLM outputs.

- `parameters/`
  Inference-time configuration used with the prompts to keep runs consistent.
