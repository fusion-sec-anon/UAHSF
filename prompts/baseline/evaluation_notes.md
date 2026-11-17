# Evaluation notes

- Use the same inference configuration as UAHSF unless explicitly varied:
  - `temperature=0`, `max_tokens=500` (see `uahsf/parameters/inference_config.yaml`)
- Keep the output convention consistent across baselines:
  - label (`SBR` / `NSBR`)
  - short justification
- If a baseline produces verbose reasoning, downstream normalization can keep only the decision-focused segment.
