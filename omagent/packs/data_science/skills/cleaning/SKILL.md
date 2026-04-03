---
name: cleaning
description: Data cleaning — handling missing values, outliers, duplicates, type corrections, and validation
triggers:
  - clean
  - cleaning
  - missing values
  - null values
  - duplicates
  - data quality
  - fix the data
  - preprocess
allowed-tools: jupyter_execute dataset_profile read_file write_file
user-invocable: true
level: 1
metadata:
  pack: data_science
  version: "1.0"
---

## Data Cleaning Workflow

When cleaning a dataset:

### Step 1: Profile First
- Use `dataset_profile` to understand structure and quality
- Identify columns with nulls, incorrect types, suspicious values

### Step 2: Handle Missing Values
- Numeric columns: median imputation (robust to outliers) or mean
- Categorical columns: mode imputation or "Unknown" category
- High-null columns (>50%): consider dropping
- Document every imputation decision

### Step 3: Fix Data Types
- Convert date strings to datetime
- Convert numeric strings to float/int
- Standardize boolean representations
- Parse currency strings to numeric

### Step 4: Handle Duplicates
- Check for exact duplicates: `df.duplicated().sum()`
- Check for near-duplicates on key columns
- Decide: drop all, keep first, or merge

### Step 5: Outlier Treatment
- Identify using IQR or z-score
- Options: cap (winsorize), remove, or flag
- Never silently remove — always document

### Step 6: Validate & Save
- Re-profile cleaned data
- Compare before/after statistics
- Save cleaned dataset to workspace artifacts
- Document all cleaning steps taken
