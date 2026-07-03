from fastapi import FastAPI
import os
import joblib
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="Tasmania Grid Intelligence API")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE_DIR, "ML", "models")

demand_model = joblib.load(os.path.join(MODELS_DIR, "demand_random_forest.pkl"))
renewable_model = joblib.load(os.path.join(MODELS_DIR, "renewable_random_forest.pkl"))

FEATURE_COLUMNS = [
    "hour", "day", "month", "day_of_week", "is_weekend",
    "demand_lag_1", "demand_lag_24", "demand_lag_168", "demand_rolling_24",
    "renewable_lag_1", "renewable_lag_24", "renewable_lag_168", "renewable_rolling_24",
    "price_lag_1", "price_lag_24", "price_lag_168", "price_rolling_24",
]


def build_latest_feature_row():
    response = (
        supabase.table("energy_readings")
        .select("*")
        .order("timestamp", desc=True)
        .limit(200)
        .execute()
    )

    df = pd.DataFrame(response.data)

    if df.empty or len(df) < 169:
        raise RuntimeError("Not enough data to create lag features.")

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

    latest_row = df.dropna().iloc[-1]
    X_latest = latest_row[FEATURE_COLUMNS].to_frame().T

    return latest_row, X_latest


def risk_level(coverage):
    if coverage >= 90:
        return "Low"
    if coverage >= 75:
        return "Medium"
    return "High"


@app.get("/")
def root():
    return {"message": "Tasmania Grid Intelligence API is running"}


@app.get("/predict")
def predict():
    latest_row, X_latest = build_latest_feature_row()

    demand = float(demand_model.predict(X_latest)[0])
    renewable = float(renewable_model.predict(X_latest)[0])

    coverage = renewable / demand * 100

    forecast_timestamp =  latest_row["timestamp"] + pd.Timedelta(hours=1)

    return {
        "latest_timestamp": str(latest_row["timestamp"]),
        "current_demand_mw": round(float(latest_row["demand_mw"]), 2),
        "current_renewable_mw": round(float(latest_row["renewable_mw"]), 2),
        "current_price_per_mwh": round(float(latest_row["price_per_mwh"]), 2),
        "predicted_next_hour_demand_mw": round(demand, 2),
        "predicted_next_hour_renewable_mw": round(renewable, 2),
        "renewable_coverage_percent": round(coverage, 2),
        "risk_level": risk_level(coverage),
        "forecast_timestamp": str(forecast_timestamp)
        
    }