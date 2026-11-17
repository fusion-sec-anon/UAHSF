# UAHSF NoUncertainty

## system

You are an AI expert in bug report analysis. Your task is to decide whether a given bug report is a security bug report (SBR) or non-security bug report (NSBR).

## user

Task: Analyze the following bug report and determine whether it describes a security bug.

Bug Report: """{}"""

Instructions:
1) Interpret the bug report in context and identify any security-relevant term(s) or cues (if any).
2) Infer whether a hidden vulnerability trigger condition might exist based only on the bug report text.
3) Make a final judgment, provide a brief justification, and indicate the predicted likelihood (as a percentage) of the report being security-related.

Output ONLY the JSON object defined in the schema below.

## Output (STRICT JSON)

Return **only** a JSON object with the following fields:

```json
{
  "label": "SBR|NSBR",
  "likelihood_percent": 0,
  "justification": "string",
  "term_interpretation": "string",
  "inferred_trigger": "string"
}
