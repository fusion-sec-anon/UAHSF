# Prompt ablations

This folder provides prompt-only variants derived from the UAHSF uncertainty-aware prompt.
Each variant removes a specific injected signal while keeping the overall instruction flow consistent
(term interpretation → trigger inference → final decision with likelihood).

## Variants

- `no_uncertainty/`  
  Removes all injected guidance signals. The LLM makes the decision based only on the bug report text,
  while preserving the same three-step instruction structure and JSON output format.

- `no_local/` (Global-only)  
  Removes the local semantic-conflict indicator (key-contradiction cue). The prompt keeps only the
  global incompleteness signals (matched CWE patterns and completeness score) and the BERT prior.

- `no_global/` (Local-only)  
  Removes the global incompleteness indicator (CWE-pattern completeness cues). The prompt keeps only
  the key-contradiction signal and the BERT prior.

- `no_cwe/`  
  Removes CWE-based domain knowledge cues from the prompt. In this variant, the prompt does not use
  CWE pattern matches or external vulnerability prototypes, while preserving the remaining instruction
  structure and output schema.
