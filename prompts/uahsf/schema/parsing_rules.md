# Parsing rules (UAHSF prompt)

UAHSF prompts encourage a concise final judgment plus a likelihood percentage.

This file documents a lightweight extraction convention for downstream normalization.

## Recommended extraction targets

- `label`: one of `SBR` or `NSBR`
- `likelihood_percent`: integer 0–100
- `justification`: a short textual rationale
- optional: `term_interpretation`, `inferred_trigger`

## Practical parsing heuristics

1) **Label**
   - Prefer explicit tokens: `SBR` / `NSBR`
   - Fallback: phrases like "security bug report" vs "non-security bug report"

2) **Likelihood**
   - Prefer the first percentage-like token: e.g., `72%`
   - If the model outputs a decimal, map to percentage:
     - `0.72` -> `72`

3) **Justification**
   - Keep 1–3 sentences after the decision statement.
   - If the model outputs long reasoning, keep the last short paragraph that directly supports the label.

## Example regex (illustrative)

- Label:
  - `\b(SBR|NSBR)\b`
- Percentage:
  - `\b(\d{1,3})\s*%\b`
