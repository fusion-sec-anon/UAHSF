# 🗂️ Datasets

This directory contains the **full processed datasets** used in the UAHSF experiments.

## Data Format

Each row corresponds to one bug report instance.

## Data Splitting

For experimental evaluation, each project dataset is split into **train/validation/test** sets with an **8:1:1** ratio at the bug-report level, while preserving the original class distribution.

The splits are generated in the experiment code using a **fixed random seed** and **deterministic shuffling** to ensure reproducibility and to avoid information leakage between splits. For detailed specifications, please refer to [SPLIT_SPEC.md](SPLIT_SPEC.md).

## Notes

- The released datasets are derived from publicly available bug tracking systems.
- The processed data is intended for research purposes.


