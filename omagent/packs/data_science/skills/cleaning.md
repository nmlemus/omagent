# Data Cleaning Best Practices

When cleaning a dataset:

1. Profile first with `dataset_profile` to understand structure
2. In Jupyter:
   - Check and handle missing values (impute, drop, or flag)
   - Detect and handle outliers (IQR, z-score methods)
   - Fix data types (dates, numerics, categoricals)
   - Standardize text fields (strip, lowercase, remove special chars)
   - Remove duplicate rows
   - Validate referential integrity across related datasets
3. Document all cleaning steps and decisions
4. Save cleaned dataset to a new file
