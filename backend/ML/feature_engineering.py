import os
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client


# -------------------------------------------------------------------
# 1. Load environment variables
# -------------------------------------------------------------------
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TABLE_NAME = "energy_readings"

if not SUPABASE_URL or not SUPABASE_KEY:
    raise SystemExit("SUPABASE_URL or SUPABASE_KEY not found in .env")


# -------------------------------------------------------------------
# 2. Connect to Supabase
# -------------------------------------------------------------------
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# -------------------------------------------------------------------
# 3. Fetch all data from Supabase (batch by batch)
# -------------------------------------------------------------------
FETCH_BATCH = 1000

print("Fetching data from Supabase...")

all_rows = []
offset = 0

while True:
    response = (
        supabase.table(TABLE_NAME)
        .select("*")
        .order("timestamp", desc=False)
        .range(offset, offset + FETCH_BATCH - 1)
        .execute()
    )

    if not response.data:
        break

    all_rows.extend(response.data)
    print(f"  Fetched {len(all_rows)} rows so far...")

    if len(response.data) < FETCH_BATCH:
        break

    offset += FETCH_BATCH

df = pd.DataFrame(all_rows)

if df.empty:
    raise SystemExit("No data found in energy_readings table.")

print(f"Loaded {len(df)} rows from Supabase.")

# -------------------------------------------------------------------
# 4. Convert timestamp into datetime format
# -------------------------------------------------------------------
df["timestamp"] = pd.to_datetime(df["timestamp"])

# -------------------------------------------------------------------
# 5. Create time-based features
# -------------------------------------------------------------------
df["hour"] = df["timestamp"].dt.hour
df["day"] = df["timestamp"].dt.day
df["month"] = df["timestamp"].dt.month
df["day_of_week"] = df["timestamp"].dt.dayofweek
df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)


# -------------------------------------------------------------------
# 6. Create demand lag features manually using for loop
# -------------------------------------------------------------------
demand_lag_1 = []
demand_lag_24 = []
demand_lag_168 = []
demand_rolling_24 = []

for index in range(len(df)):
    if index < 168:
        demand_lag_1.append(None)
        demand_lag_24.append(None)
        demand_lag_168.append(None)
        demand_rolling_24.append(None)
    else:
        demand_lag_1.append(df.iloc[index - 1]["demand_mw"])
        demand_lag_24.append(df.iloc[index - 24]["demand_mw"])
        demand_lag_168.append(df.iloc[index - 168]["demand_mw"])

        previous_24_hours = df.iloc[index - 24:index]["demand_mw"]
        demand_rolling_24.append(previous_24_hours.mean())

df["demand_lag_1"] = demand_lag_1
df["demand_lag_24"] = demand_lag_24
df["demand_lag_168"] = demand_lag_168
df["demand_rolling_24"] = demand_rolling_24


# -------------------------------------------------------------------
# 7. Create renewable generation features using shift
# -------------------------------------------------------------------
df["renewable_lag_1"] = df["renewable_mw"].shift(1)
df["renewable_lag_24"] = df["renewable_mw"].shift(24)
df["renewable_lag_168"] = df["renewable_mw"].shift(168)

df["renewable_rolling_24"] = (
    df["renewable_mw"]
    .shift(1)
    .rolling(window=24)
    .mean()
)


# -------------------------------------------------------------------
# 8. Create price features using shift
# -------------------------------------------------------------------
df["price_lag_1"] = df["price_per_mwh"].shift(1)
df["price_lag_24"] = df["price_per_mwh"].shift(24)
df["price_lag_168"] = df["price_per_mwh"].shift(168)

df["price_rolling_24"] = (
    df["price_per_mwh"]
    .shift(1)
    .rolling(window=24)
    .mean()
)


# -------------------------------------------------------------------
# 9. Create target variables
# -------------------------------------------------------------------
# Demand model target: demand one hour in the future
df["target_demand_next_hour"] = df["demand_mw"].shift(-1)

# Renewable model target: renewable generation one hour in the future
df["target_renewable_next_hour"] = df["renewable_mw"].shift(-1)


# -------------------------------------------------------------------
# 10. Remove incomplete rows
# -------------------------------------------------------------------
# The first 168 rows are removed because weekly lag features are not available.
# The final row is removed because next-hour target values are not available.
feature_df = df.dropna().reset_index(drop=True)


# -------------------------------------------------------------------
# 11. Save feature-engineered dataset
# -------------------------------------------------------------------
feature_df.to_csv("feature_dataset.csv", index=False)

print("Original rows:", len(df))
print("Feature rows:", len(feature_df))
print("Feature dataset saved to feature_dataset.csv")