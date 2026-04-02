from typing import Any
from omagent.tools.base import Tool


class DatasetProfileTool(Tool):
    """Profile a dataset file (CSV, Excel, Parquet) and return summary statistics."""

    @property
    def name(self) -> str:
        return "dataset_profile"

    @property
    def description(self) -> str:
        return (
            "Profile a dataset file (CSV, Excel, Parquet). Returns shape, dtypes, "
            "null counts, basic statistics, and sample rows. Use this to quickly "
            "understand a dataset before deeper analysis."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the dataset file (CSV, Excel, or Parquet).",
                },
                "sample_rows": {
                    "type": "integer",
                    "description": "Number of sample rows to include (default: 5).",
                },
            },
            "required": ["path"],
        }

    async def execute(self, input: dict[str, Any]) -> dict[str, Any]:
        path = input["path"]
        sample_n = input.get("sample_rows", 5)

        try:
            import pandas as pd
        except ImportError:
            return {"error": "pandas is required. Install with: pip install pandas"}

        try:
            # Detect format and read
            if path.endswith(".csv"):
                df = pd.read_csv(path, nrows=10000)
            elif path.endswith((".xlsx", ".xls")):
                df = pd.read_excel(path, nrows=10000)
            elif path.endswith(".parquet"):
                df = pd.read_parquet(path)
            elif path.endswith(".json"):
                df = pd.read_json(path)
            else:
                # Try CSV as default
                df = pd.read_csv(path, nrows=10000)

            profile = {
                "output": "Dataset profiled successfully",
                "shape": {"rows": len(df), "columns": len(df.columns)},
                "columns": list(df.columns),
                "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
                "null_counts": df.isnull().sum().to_dict(),
                "null_percentages": (df.isnull().sum() / len(df) * 100).round(2).to_dict(),
                "numeric_stats": {},
                "sample_rows": df.head(sample_n).to_dict(orient="records"),
            }

            # Numeric column stats
            numeric_cols = df.select_dtypes(include=["number"]).columns
            if len(numeric_cols) > 0:
                stats = df[numeric_cols].describe().to_dict()
                profile["numeric_stats"] = {
                    col: {k: round(v, 4) if isinstance(v, float) else v for k, v in stat.items()}
                    for col, stat in stats.items()
                }

            return profile

        except FileNotFoundError:
            return {"error": f"File not found: {path}"}
        except Exception as e:
            return {"error": f"Failed to profile dataset: {e}"}
