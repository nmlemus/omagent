#!/usr/bin/env python3
"""Model evaluation helper — generates metrics report."""
import sys
import json

if len(sys.argv) < 2:
    print("Usage: evaluate_model.py <metrics_json>")
    sys.exit(1)

metrics = json.loads(sys.argv[1])
print("Model Evaluation Report")
print("=" * 40)
for key, value in metrics.items():
    if isinstance(value, float):
        print(f"  {key}: {value:.4f}")
    else:
        print(f"  {key}: {value}")
