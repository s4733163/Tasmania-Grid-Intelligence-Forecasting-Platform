import sys
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import joblib

from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

FIGURES_DIR = os.path.join(SCRIPT_DIR, "figures")
MODELS_DIR = os.path.join(SCRIPT_DIR, "models")
LOG_FILE = os.path.join(SCRIPT_DIR, "training_renewable_gradient_boosting_log.txt")

os.makedirs(FIGURES_DIR, exist_ok=True)
os.makedirs(MODELS_DIR, exist_ok=True)


class _Tee:
    def __init__(self, *streams):
        self._streams = streams

    def write(self, data):
        for s in self._streams:
            s.write(data)
            s.flush()

    def flush(self):
        for s in self._streams:
            s.flush()


_log_file = open(LOG_FILE, "w")
sys.stdout = _Tee(sys.__stdout__, _log_file)


# -------------------------------------------------------------------
# 1. Load feature-engineered dataset
# -------------------------------------------------------------------
FEATURE_DATASET = os.path.join(SCRIPT_DIR, "feature_dataset.csv")

df = pd.read_csv(FEATURE_DATASET)

print("Feature dataset loaded successfully.")
print("Rows:", len(df))
print("Columns:", len(df.columns))


# -------------------------------------------------------------------
# 2. Basic verification
# -------------------------------------------------------------------
print("\nFirst 5 rows:")
print(df.head())

print("\nColumn names:")
print(df.columns.tolist())

print("\nMissing values:")
print(df.isnull().sum())


# -------------------------------------------------------------------
# 3. Confirm target column exists
# -------------------------------------------------------------------
TARGET_COLUMN = "target_renewable_next_hour"

if TARGET_COLUMN not in df.columns:
    raise SystemExit(f"{TARGET_COLUMN} not found in dataset.")

print(f"\nTarget column found: {TARGET_COLUMN}")


# -------------------------------------------------------------------
# 4. Define feature columns for renewable forecasting
# -------------------------------------------------------------------
feature_columns = [
    "hour",
    "day",
    "month",
    "day_of_week",
    "is_weekend",

    "demand_lag_1",
    "demand_lag_24",
    "demand_lag_168",
    "demand_rolling_24",

    "renewable_lag_1",
    "renewable_lag_24",
    "renewable_lag_168",
    "renewable_rolling_24",

    "price_lag_1",
    "price_lag_24",
    "price_lag_168",
    "price_rolling_24",
]

missing_features = [col for col in feature_columns if col not in df.columns]

if missing_features:
    raise SystemExit(f"Missing feature columns: {missing_features}")

print("\nAll feature columns found.")


# -------------------------------------------------------------------
# 5. Create X and y
# -------------------------------------------------------------------
X = df[feature_columns]
y = df[TARGET_COLUMN]

print("\nX shape:", X.shape)
print("y shape:", y.shape)

print("\nStep 1 complete: data is ready for train/test split.")


# -------------------------------------------------------------------
# 6. Time-based train/test split
# -------------------------------------------------------------------
train_size = int(len(df) * 0.8)

X_train = X.iloc[:train_size]
X_test = X.iloc[train_size:]

y_train = y.iloc[:train_size]
y_test = y.iloc[train_size:]

print("Training rows:", len(X_train))
print("Testing rows:", len(X_test))
print("Train period:", df.iloc[0]["timestamp"], "to", df.iloc[train_size - 1]["timestamp"])
print("Test period:", df.iloc[train_size]["timestamp"], "to", df.iloc[-1]["timestamp"])


# -------------------------------------------------------------------
# 7. Train Gradient Boosting Regressor
# -------------------------------------------------------------------
model = GradientBoostingRegressor(
    n_estimators=300,
    learning_rate=0.05,
    max_depth=4,
    subsample=0.9,
    random_state=42
)

print("\nTraining Gradient Boosting model...")
model.fit(X_train, y_train)

print("Model training complete.")


# -------------------------------------------------------------------
# 8. Make predictions on test data
# -------------------------------------------------------------------
y_pred = model.predict(X_test)


# -------------------------------------------------------------------
# 9. Evaluate model performance
# -------------------------------------------------------------------
mae = mean_absolute_error(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
r2 = r2_score(y_test, y_pred)

print("\n========== GRADIENT BOOSTING MODEL PERFORMANCE ==========")
print(f"MAE  : {mae:.2f} MW")
print(f"RMSE : {rmse:.2f} MW")
print(f"R²   : {r2:.4f}")


# -------------------------------------------------------------------
# 10. Save trained model
# -------------------------------------------------------------------
model_path = os.path.join(MODELS_DIR, "renewable_gradient_boosting.pkl")
joblib.dump(model, model_path)

print(f"\nModel saved to {model_path}")


# -------------------------------------------------------------------
# 11. Plot Feature Importance
# -------------------------------------------------------------------
feature_importance = pd.DataFrame({
    "Feature": X_train.columns,
    "Importance": model.feature_importances_
})

feature_importance = feature_importance.sort_values(
    by="Importance",
    ascending=False
)

print("\n========== FEATURE IMPORTANCE ==========")
print(feature_importance)

plt.figure(figsize=(10, 6))
plt.barh(feature_importance["Feature"], feature_importance["Importance"])
plt.xlabel("Importance")
plt.ylabel("Feature")
plt.title("Gradient Boosting Feature Importance")
plt.gca().invert_yaxis()
plt.tight_layout()
plt.savefig(os.path.join(FIGURES_DIR, "renewable_gradient_boosting_feature_importance.png"))
plt.show()


# -------------------------------------------------------------------
# 12. Compare Actual vs Predicted Renewable Generation
# -------------------------------------------------------------------
comparison = pd.DataFrame({
    "Timestamp": df.iloc[train_size:]["timestamp"].values,
    "Actual": y_test.values,
    "Predicted": y_pred
})

print("\nFirst 10 Predictions:")
print(comparison.head(10))

plt.figure(figsize=(14, 6))
plt.plot(comparison["Timestamp"], comparison["Actual"], label="Actual Renewable")
plt.plot(comparison["Timestamp"], comparison["Predicted"], label="Predicted Renewable")
plt.title("Actual vs Predicted Renewable Generation")
plt.xlabel("Time")
plt.ylabel("Renewable Generation (MW)")
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(FIGURES_DIR, "actual_vs_predicted_renewable_gradient_boosting.png"))
plt.show()


comparison_week = comparison.iloc[:168]

plt.figure(figsize=(14, 6))
plt.plot(comparison_week["Timestamp"], comparison_week["Actual"], label="Actual Renewable")
plt.plot(comparison_week["Timestamp"], comparison_week["Predicted"], label="Predicted Renewable")
plt.title("Actual vs Predicted Renewable Generation (First Week of Test Set)")
plt.xlabel("Time")
plt.ylabel("Renewable Generation (MW)")
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(FIGURES_DIR, "actual_vs_predicted_week_renewable_gradient_boosting.png"))
plt.show()


print(f"\nAll figures saved to: {FIGURES_DIR}")
print(f"Training log saved to: {LOG_FILE}")

_log_file.close()
sys.stdout = sys.__stdout__