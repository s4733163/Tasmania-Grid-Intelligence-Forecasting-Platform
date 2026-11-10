import os
import time
from datetime import datetime, timedelta

import joblib
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client
from openelectricity import OEClient
from openelectricity.client import APIError
from openelectricity.types import MarketMetric


# ---------------------------------------------------------
# 1. Environment and constants
# ---------------------------------------------------------
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENELECTRICITY_API_KEY = os.getenv("OPENELECTRICITY_API_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_URL or SUPABASE_KEY missing")

if not OPENELECTRICITY_API_KEY:
    raise RuntimeError("OPENELECTRICITY_API_KEY missing")

TABLE_NAME = "energy_readings"
FORECAST_TABLE = "forecasts"

BATCH_SIZE = 500
CHUNK = timedelta(days=30)
SLEEP_SECONDS = 0.3
RETENTION = timedelta(days=730)
FORECAST_HOURS = 36

METRICS = [
    MarketMetric.DEMAND,
    MarketMetric.PRICE,
    MarketMetric.GENERATION_RENEWABLE,
]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

client = OEClient(
    api_key=OPENELECTRICITY_API_KEY,
    base_url="https://api.openelectricity.org.au/v4",
)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "ML", "models")

demand_model = joblib.load(os.path.join(MODELS_DIR, "demand_random_forest.pkl"))
renewable_model = joblib.load(os.path.join(MODELS_DIR, "renewable_random_forest.pkl"))


DEMAND_FEATURES = [
    "hour", "day", "month", "day_of_week", "is_weekend",
    "demand_lag_1", "demand_lag_24", "demand_lag_168", "demand_rolling_24",
]

RENEWABLE_FEATURES = [
    "hour", "day", "month", "day_of_week", "is_weekend",
    "demand_lag_1", "demand_lag_24", "demand_lag_168", "demand_rolling_24",
    "renewable_lag_1", "renewable_lag_24", "renewable_lag_168", "renewable_rolling_24",
    "price_lag_1", "price_lag_24", "price_lag_168", "price_rolling_24",
]


# ---------------------------------------------------------
# 2. Update actual data from OpenElectricity
# ---------------------------------------------------------
def update_energy_readings():
    latest_response = (
        supabase.table(TABLE_NAME)
        .select("*")
        .order("timestamp", desc=True)
        .limit(1)
        .execute()
    )

    latest = latest_response.data[0]["timestamp"] if latest_response.data else None

    if not latest:
        raise RuntimeError("No existing data in database. Run initial ETL first.")

    now = datetime.now().replace(minute=0, second=0, microsecond=0)

    start = pd.to_datetime(latest).to_pydatetime()

    if start.tzinfo is not None:
        start = start.astimezone(tz=None).replace(tzinfo=None)

    if start >= now:
        print("Already up to date.")
        return {"updated": False, "rows": 0}

    rows = []
    cursor = start

    print(f"Fetching new data from {cursor} to {now}")

    while cursor < now:
        chunk_end = min(cursor + CHUNK, now)

        try:
            response = client.get_market(
                network_code="NEM",
                metrics=METRICS,
                interval="1h",
                date_start=cursor,
                date_end=chunk_end,
                network_region="TAS1",
                primary_grouping="network_region",
            )
        except APIError as e:
            print(f"OpenElectricity API error: {e}")
            break

        for timeseries in response.data:
            metric = (
                timeseries.metric.value
                if hasattr(timeseries.metric, "value")
                else str(timeseries.metric)
            )

            for result in timeseries.results:
                region = result.name.split("_")[-1]

                for point in result.data:
                    rows.append({
                        "timestamp": point.timestamp,
                        "region": region,
                        "metric": metric,
                        "value": point.value,
                        "unit": timeseries.unit,
                    })

        cursor = chunk_end
        time.sleep(SLEEP_SECONDS)

    if not rows:
        print("No new rows returned.")
        return {"updated": False, "rows": 0}

    df_long = pd.DataFrame(rows).drop_duplicates(
        subset=["timestamp", "region", "metric"]
    )

    df = (
        df_long.pivot_table(
            index=["timestamp", "region"],
            columns="metric",
            values="value",
            aggfunc="first",
        )
        .reset_index()
        .sort_values("timestamp")
        .reset_index(drop=True)
    )

    df.columns.name = None

    df = df.rename(columns={
        "demand": "demand_mw",
        "price": "price_per_mwh",
        "generation_renewable": "renewable_mw",
    })

    df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.strftime(
        "%Y-%m-%dT%H:%M:%S%z"
    )

    df = df[
        ["timestamp", "region", "demand_mw", "price_per_mwh", "renewable_mw"]
    ]

    df = df.astype(object).where(pd.notnull(df), None)
    records = df.to_dict(orient="records")

    for i in range(0, len(records), BATCH_SIZE):
        batch = records[i:i + BATCH_SIZE]

        supabase.table(TABLE_NAME).upsert(
            batch,
            on_conflict="timestamp,region"
        ).execute()

    print(f"Inserted/updated {len(records)} rows.")
    return {"updated": True, "rows": len(records)}


# ---------------------------------------------------------
# 3. Prune old data
# ---------------------------------------------------------
def prune_old_data():
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    cutoff = (now - RETENTION).strftime("%Y-%m-%dT%H:%M:%S+00:00")

    deleted_total = 0

    while True:
        old_rows = (
            supabase.table(TABLE_NAME)
            .select("timestamp")
            .lt("timestamp", cutoff)
            .order("timestamp", desc=False)
            .limit(BATCH_SIZE)
            .execute()
        )

        if not old_rows.data:
            break

        batch_cutoff = old_rows.data[-1]["timestamp"]

        result = (
            supabase.table(TABLE_NAME)
            .delete()
            .lte("timestamp", batch_cutoff)
            .execute()
        )

        deleted_count = len(result.data) if result.data else len(old_rows.data)
        deleted_total += deleted_count

    print(f"Pruned {deleted_total} old rows.")
    return deleted_total


# ---------------------------------------------------------
# 4. Feature engineering
# ---------------------------------------------------------
def rebuild_features(df):
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.sort_values("timestamp").reset_index(drop=True)

    df["hour"] = df["timestamp"].dt.hour
    df["day"] = df["timestamp"].dt.day
    df["month"] = df["timestamp"].dt.month
    df["day_of_week"] = df["timestamp"].dt.dayofweek
    df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)

    df["demand_lag_1"] = df["demand_mw"].shift(1)
    df["demand_lag_24"] = df["demand_mw"].shift(24)
    df["demand_lag_168"] = df["demand_mw"].shift(168)
    df["demand_rolling_24"] = df["demand_mw"].shift(1).rolling(24).mean()

    df["renewable_lag_1"] = df["renewable_mw"].shift(1)
    df["renewable_lag_24"] = df["renewable_mw"].shift(24)
    df["renewable_lag_168"] = df["renewable_mw"].shift(168)
    df["renewable_rolling_24"] = df["renewable_mw"].shift(1).rolling(24).mean()

    df["price_lag_1"] = df["price_per_mwh"].shift(1)
    df["price_lag_24"] = df["price_per_mwh"].shift(24)
    df["price_lag_168"] = df["price_per_mwh"].shift(168)
    df["price_rolling_24"] = df["price_per_mwh"].shift(1).rolling(24).mean()

    return df


def build_latest_feature_row():
    response = (
        supabase.table(TABLE_NAME)
        .select("*")
        .order("timestamp", desc=True)
        .limit(200)
        .execute()
    )

    df = pd.DataFrame(response.data)

    if df.empty or len(df) < 169:
        raise RuntimeError("Not enough data to create lag features.")

    df = rebuild_features(df)

    latest_row = df.dropna(
        subset=list(set(DEMAND_FEATURES + RENEWABLE_FEATURES))
    ).iloc[-1]

    X_latest_demand = latest_row[DEMAND_FEATURES].to_frame().T
    X_latest_renewable = latest_row[RENEWABLE_FEATURES].to_frame().T

    return df, latest_row, X_latest_demand, X_latest_renewable


# ---------------------------------------------------------
# 5. Forecasting
# ---------------------------------------------------------
def risk_level(coverage):
    if coverage >= 90:
        return "Low"
    if coverage >= 75:
        return "Medium"
    return "High"


def generate_forecast():
    df, latest_row, X_latest_demand, X_latest_renewable = build_latest_feature_row()

    forecast_rows = []
    current_timestamp = latest_row["timestamp"]

    for _ in range(FORECAST_HOURS):
        demand = float(demand_model.predict(X_latest_demand)[0])
        renewable = float(renewable_model.predict(X_latest_renewable)[0])

        forecast_timestamp = current_timestamp + pd.Timedelta(hours=1)

        average_price = (
            df.loc[df["hour"] == forecast_timestamp.hour, "price_per_mwh"]
            .tail(30)
            .mean()
        )

        coverage = renewable / demand * 100

        forecast_record = {
            "forecast_timestamp": forecast_timestamp.isoformat(),
            "forecast_date": forecast_timestamp.date().isoformat(),
            "predicted_demand_mw": round(demand, 2),
            "predicted_renewable_mw": round(renewable, 2),
            "estimated_price_per_mwh": round(float(average_price), 2),
            "renewable_coverage_percent": round(coverage, 2),
            "risk_level": risk_level(coverage),
        }

        supabase.table(FORECAST_TABLE).upsert(
            forecast_record,
            on_conflict="forecast_timestamp"
        ).execute()

        forecast_rows.append(forecast_record)

        new_row = pd.DataFrame([{
            "timestamp": forecast_timestamp,
            "region": "TAS1",
            "demand_mw": demand,
            "renewable_mw": renewable,
            "price_per_mwh": average_price,
        }])

        df = pd.concat([df, new_row], ignore_index=True)
        df = df.tail(200).reset_index(drop=True)
        df = rebuild_features(df)

        latest_row = df.dropna(
            subset=list(set(DEMAND_FEATURES + RENEWABLE_FEATURES))
        ).iloc[-1]

        X_latest_demand = latest_row[DEMAND_FEATURES].to_frame().T
        X_latest_renewable = latest_row[RENEWABLE_FEATURES].to_frame().T

        current_timestamp = forecast_timestamp

    return {
        "forecast_hours": FORECAST_HOURS,
        "count": len(forecast_rows),
        "value": forecast_rows,
    }


# ---------------------------------------------------------
# 6. main function to run everything
# ---------------------------------------------------------
def main_handler():
    print("Starting scheduled ETL + forecast job...")

    update_result = update_energy_readings()
    deleted_rows = prune_old_data()
    forecast_result = generate_forecast()

    print("Scheduled job complete.")

    return {
        "statusCode": 200,
        "body": {
            "message": "ETL and forecast generation completed successfully.",
            "energy_update": update_result,
            "deleted_rows": deleted_rows,
            "forecast": {
                "forecast_hours": forecast_result["forecast_hours"],
                "count": forecast_result["count"],
            },
        },
    }

main_handler()