#!/usr/bin/env python3
"""Quick dataset profiling script — runs without Jupyter."""
import sys
import pandas as pd

if len(sys.argv) < 2:
    print("Usage: quick_profile.py <csv_path>")
    sys.exit(1)

path = sys.argv[1]
df = pd.read_csv(path, nrows=5000)

print(f"Shape: {df.shape[0]} rows x {df.shape[1]} columns")
print(f"\nColumns: {', '.join(df.columns)}")
print(f"\nDtypes:\n{df.dtypes.to_string()}")
print(f"\nNull counts:\n{df.isnull().sum().to_string()}")
print(f"\nNumeric summary:\n{df.describe().to_string()}")
