---
name: modeling
description: Machine learning model training — feature engineering, model selection, cross-validation, and evaluation
triggers:
  - model
  - train a model
  - predict
  - classification
  - regression
  - machine learning
  - ml pipeline
  - feature engineering
allowed-tools: jupyter_execute model_train dataset_profile read_file write_file
user-invocable: true
level: 2
metadata:
  pack: data_science
  version: "1.0"
---

## ML Modeling Workflow

When building a predictive model:

### Step 1: Problem Definition
- Identify: classification or regression?
- Define the target variable
- Determine evaluation metric (accuracy, F1, RMSE, R², etc.)

### Step 2: Feature Engineering
- Handle missing values (imputation strategy based on data type)
- Encode categorical variables (one-hot, label, target encoding)
- Scale numeric features if needed (StandardScaler, MinMaxScaler)
- Create interaction features if domain knowledge suggests them
- Remove low-variance or highly correlated features

### Step 3: Train-Test Split
- Use 80/20 or 70/30 split with random_state for reproducibility
- For time series: use temporal split (no shuffle)
- Stratify for imbalanced classification

### Step 4: Model Training
- Start with a baseline (logistic regression / linear regression)
- Try ensemble methods (Random Forest, Gradient Boosting)
- Use cross-validation (5-fold) for robust evaluation
- Use `model_train` tool for automated training with metrics

### Step 5: Evaluation
- Classification: accuracy, precision, recall, F1, confusion matrix, ROC-AUC
- Regression: RMSE, MAE, R², residual plots
- Feature importance analysis
- Compare models side by side

### Step 6: Report
- Best model with key metrics
- Feature importance ranking
- Recommendations for improvement
- Save model and predictions to workspace
