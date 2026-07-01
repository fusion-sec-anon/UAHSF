# Split Specification

- Ratio: 8:1:1 (train/val/test)
- Level: bug-report instance (per project)
- Strategy: stratified by label
- Random seed: 42
- Procedure:
  1) For each dataset, perform stratified split into Train (80%) and Temp (20%).
  2) Split Temp into Validation (10%) and Test (10%) with stratification.
  3) Use deterministic shuffling with the fixed seed.