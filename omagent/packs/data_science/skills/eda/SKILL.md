---
name: eda
description: Exploratory data analysis — profiling datasets, checking distributions, finding correlations, and identifying outliers
triggers:
  - eda
  - exploratory
  - explore the data
  - profile the data
  - distributions
  - correlations
  - outliers
  - data overview
allowed-tools: jupyter_execute dataset_profile read_file list_dir
user-invocable: true
level: 1
metadata:
  pack: data_science
  version: "1.0"
---

## Exploratory Data Analysis Workflow

When performing EDA on a dataset:

### Step 1: Understand the Data
- Use `dataset_profile` to get shape, dtypes, null counts, and sample rows
- Identify the target variable if applicable
- Note any obvious data quality issues

### Step 2: Data Quality Assessment
- Check null value percentages per column
- Identify duplicate rows
- Check for inconsistent data types (numbers stored as strings, etc.)
- Flag columns with suspiciously low cardinality

### Step 3: Univariate Analysis
- Numeric columns: compute mean, median, std, min, max, quartiles
- Plot histograms or KDE for key numeric distributions
- Categorical columns: value counts, bar charts for top categories
- Check for class imbalance in target variable

### Step 4: Bivariate Analysis
- Compute correlation matrix for numeric columns
- Create heatmap visualization
- Scatter plots for highly correlated pairs
- Box plots for numeric vs categorical relationships

### Step 5: Outlier Detection
- IQR method: flag values below Q1-1.5*IQR or above Q3+1.5*IQR
- Z-score method for normally distributed features
- Visualize outliers with box plots

### Step 6: Summary Report
- Key statistics table
- Data quality score (% complete, % unique, type consistency)
- Top findings and actionable insights
- Recommended next steps (cleaning, feature engineering, modeling)
