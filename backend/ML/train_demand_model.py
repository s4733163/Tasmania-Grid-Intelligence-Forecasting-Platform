import pandas as pd


# -------------------------------------------------------------------
# 1. Load feature-engineered dataset
# -------------------------------------------------------------------
FEATURE_DATASET = "feature_dataset.csv"

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
X_test = X.iloc[train_size:]

y_train = y.iloc[:train_size]
y_test = y.iloc[train_size:]

print("Training rows:", len(X_train))
print("Testing rows:", len(X_test))
print("Train period:", df.iloc[0]["timestamp"], "to", df.iloc[train_size - 1]["timestamp"])
print("Test period:", df.iloc[train_size]["timestamp"], "to", df.iloc[-1]["timestamp"])