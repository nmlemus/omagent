from typing import Any
from omagent.tools.base import Tool


class ModelTrainTool(Tool):
    """Train sklearn models with cross-validation and return metrics."""

    @property
    def name(self) -> str:
        return "model_train"

    @property
    def description(self) -> str:
        return (
            "Train a scikit-learn model with automatic cross-validation. "
            "Provide a CSV path, target column, model type, and get back "
            "metrics (accuracy/RMSE/F1), feature importances, and the trained model path."
        )

    @property
    def input_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "csv_path": {"type": "string", "description": "Path to CSV data file."},
                "target_column": {"type": "string", "description": "Name of the target/label column."},
                "model_type": {
                    "type": "string",
                    "enum": ["random_forest", "logistic_regression", "linear_regression", "gradient_boosting", "xgboost"],
                    "description": "Model type to train (default: random_forest).",
                },
                "test_size": {"type": "number", "description": "Test split ratio (default: 0.2)."},
                "cv_folds": {"type": "integer", "description": "Cross-validation folds (default: 5)."},
            },
            "required": ["csv_path", "target_column"],
        }

    async def execute(self, input: dict[str, Any]) -> dict[str, Any]:
        try:
            import pandas as pd
            import numpy as np
            from sklearn.model_selection import train_test_split, cross_val_score
            from sklearn.metrics import accuracy_score, mean_squared_error, f1_score, r2_score
            from sklearn.preprocessing import LabelEncoder
        except ImportError:
            return {"error": "scikit-learn required. pip install scikit-learn"}

        csv_path = input["csv_path"]
        target = input["target_column"]
        model_type = input.get("model_type", "random_forest")
        test_size = input.get("test_size", 0.2)
        cv_folds = input.get("cv_folds", 5)

        try:
            df = pd.read_csv(csv_path)
            if target not in df.columns:
                return {"error": f"Column '{target}' not found. Available: {list(df.columns)}"}

            y = df[target]
            X = df.drop(columns=[target])

            # Encode categoricals
            label_encoders = {}
            for col in X.select_dtypes(include=["object", "category"]).columns:
                le = LabelEncoder()
                X[col] = le.fit_transform(X[col].astype(str))
                label_encoders[col] = le

            # Drop non-numeric remaining
            X = X.select_dtypes(include=[np.number])

            # Fill NaN
            X = X.fillna(X.median())

            # Determine task type
            is_classification = y.dtype == "object" or y.nunique() < 20
            if is_classification:
                le_target = LabelEncoder()
                y = le_target.fit_transform(y.astype(str))

            # Select model
            if model_type == "logistic_regression":
                from sklearn.linear_model import LogisticRegression
                model = LogisticRegression(max_iter=1000)
            elif model_type == "linear_regression":
                from sklearn.linear_model import LinearRegression
                model = LinearRegression()
            elif model_type == "gradient_boosting":
                if is_classification:
                    from sklearn.ensemble import GradientBoostingClassifier
                    model = GradientBoostingClassifier()
                else:
                    from sklearn.ensemble import GradientBoostingRegressor
                    model = GradientBoostingRegressor()
            else:  # random_forest
                if is_classification:
                    from sklearn.ensemble import RandomForestClassifier
                    model = RandomForestClassifier(n_estimators=100)
                else:
                    from sklearn.ensemble import RandomForestRegressor
                    model = RandomForestRegressor(n_estimators=100)

            # Train/test split
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=42)
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)

            # Metrics
            metrics = {}
            if is_classification:
                metrics["accuracy"] = round(accuracy_score(y_test, y_pred), 4)
                metrics["f1_score"] = round(f1_score(y_test, y_pred, average="weighted"), 4)
                scoring = "accuracy"
            else:
                metrics["rmse"] = round(float(np.sqrt(mean_squared_error(y_test, y_pred))), 4)
                metrics["r2"] = round(float(r2_score(y_test, y_pred)), 4)
                scoring = "r2"

            # Cross-validation
            cv_scores = cross_val_score(model, X, y, cv=min(cv_folds, len(X)), scoring=scoring)
            metrics["cv_mean"] = round(float(cv_scores.mean()), 4)
            metrics["cv_std"] = round(float(cv_scores.std()), 4)

            # Feature importances
            importances = {}
            if hasattr(model, "feature_importances_"):
                for feat, imp in sorted(zip(X.columns, model.feature_importances_), key=lambda x: -x[1])[:10]:
                    importances[feat] = round(float(imp), 4)

            return {
                "output": f"Model trained: {model_type} ({'classification' if is_classification else 'regression'})",
                "task_type": "classification" if is_classification else "regression",
                "model_type": model_type,
                "metrics": metrics,
                "feature_importances": importances,
                "train_size": len(X_train),
                "test_size": len(X_test),
                "features_used": list(X.columns),
            }
        except Exception as e:
            return {"error": f"Training failed: {e}"}
