import sys
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# All outputs are anchored to the directory that contains this script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

FIGURES_DIR = os.path.join(SCRIPT_DIR, "figures")
MODELS_DIR  = os.path.join(SCRIPT_DIR, "models")
LOG_FILE    = os.path.join(SCRIPT_DIR, "training_log.txt")

os.makedirs(FIGURES_DIR, exist_ok=True)
os.makedirs(MODELS_DIR,  exist_ok=True)


# Tee stdout so every print goes to the terminal AND to training_log.txt
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


_log_file   = open(LOG_FILE, "w")
sys.stdout  = _Tee(sys.__stdout__, _log_file)


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
TARGET_COLUMN = "target_demand_next_hour"

if TARGET_COLUMN not in df.columns:
    raise SystemExit(f"{TARGET_COLUMN} not found in dataset.")

print(f"\nTarget column found: {TARGET_COLUMN}")


# -------------------------------------------------------------------
# 4. Define feature columns for demand forecasting
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
X_test  = X.iloc[train_size:]

y_train = y.iloc[:train_size]
y_test  = y.iloc[train_size:]

print("Training rows:", len(X_train))
print("Testing rows:", len(X_test))
print("Train period:", df.iloc[0]["timestamp"], "to", df.iloc[train_size - 1]["timestamp"])
print("Test period:", df.iloc[train_size]["timestamp"], "to", df.iloc[-1]["timestamp"])

# -------------------------------------------------------------------
# 7. Train Random Forest Regressor
# -------------------------------------------------------------------
model = RandomForestRegressor(
    n_estimators=100,
    random_state=42,
    n_jobs=-1
)

print("\nTraining Random Forest model...")
model.fit(X_train, y_train)

print("Model training complete.")


# -------------------------------------------------------------------
# 8. Make predictions on test data
# -------------------------------------------------------------------
y_pred = model.predict(X_test)


# -------------------------------------------------------------------
# 9. Evaluate model performance
# -------------------------------------------------------------------
mae  = mean_absolute_error(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
r2   = r2_score(y_test, y_pred)

print("\n========== MODEL PERFORMANCE ==========")
print(f"MAE  : {mae:.2f} MW")
print(f"RMSE : {rmse:.2f} MW")
print(f"R²   : {r2:.4f}")


# -------------------------------------------------------------------
# 10. Save trained model
# -------------------------------------------------------------------
joblib.dump(model, os.path.join(MODELS_DIR, "demand_random_forest.pkl"))

print(f"\nModel saved to {os.path.join(MODELS_DIR, 'demand_random_forest.pkl')}")

# -------------------------------------------------------------------
# 11. Plot Feature Importance
# -------------------------------------------------------------------
feature_importance = pd.DataFrame({
    "Feature":    X_train.columns,
    "Importance": model.feature_importances_
})

feature_importance = feature_importance.sort_values(by="Importance", ascending=False)

print("\n========== FEATURE IMPORTANCE ==========")
print(feature_importance)

plt.figure(figsize=(10, 6))
plt.barh(feature_importance["Feature"], feature_importance["Importance"])
plt.xlabel("Importance")
plt.ylabel("Feature")
plt.title("Random Forest Feature Importance")
plt.gca().invert_yaxis()
plt.tight_layout()
plt.savefig(os.path.join(FIGURES_DIR, "feature_importance.png"))
plt.show()

# -------------------------------------------------------------------
# 12. Compare Actual vs Predicted Demand
# -------------------------------------------------------------------
comparison = pd.DataFrame({
    "Timestamp": df.iloc[train_size:]["timestamp"].values,
    "Actual":    y_test.values,
    "Predicted": y_pred
})

print("\nFirst 10 Predictions:")
print(comparison.head(10))

plt.figure(figsize=(14, 6))
plt.plot(comparison["Timestamp"], comparison["Actual"],    label="Actual Demand")
plt.plot(comparison["Timestamp"], comparison["Predicted"], label="Predicted Demand")
plt.title("Actual vs Predicted Electricity Demand")
plt.xlabel("Time")
plt.ylabel("Demand (MW)")
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(FIGURES_DIR, "actual_vs_predicted.png"))
plt.show()

comparison_week = comparison.iloc[:168]

plt.figure(figsize=(14, 6))
plt.plot(comparison_week["Timestamp"], comparison_week["Actual"],    label="Actual Demand")
plt.plot(comparison_week["Timestamp"], comparison_week["Predicted"], label="Predicted Demand")
plt.title("Actual vs Predicted Demand (First Week of Test Set)")
plt.xlabel("Time")
plt.ylabel("Demand (MW)")
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(FIGURES_DIR, "actual_vs_predicted_week.png"))
plt.show()

print(f"\nAll figures saved to: {FIGURES_DIR}")
print(f"Training log saved to: {LOG_FILE}")

_log_file.close()
sys.stdout = sys.__stdout__
