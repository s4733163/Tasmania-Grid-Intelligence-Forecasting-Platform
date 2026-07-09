from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from cachetools import TTLCache
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:5174", "http://127.0.0.1:5174",
    ],
    allow_methods=["GET"],
    allow_headers=["*"],
)
CACHE_TTL = 300  # 1 hour

current_cache = TTLCache(maxsize=1, ttl=CACHE_TTL)
forecast_cache = TTLCache(maxsize=1, ttl=CACHE_TTL)
summary_cache = TTLCache(maxsize=1, ttl=CACHE_TTL)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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
    X_latest_renewable = latest_row[RENEWABLE_FEATURES].to_frame().T
    X_latest_demand = latest_row[DEMAND_FEATURES].to_frame().T

    return df, latest_row, X_latest_renewable, X_latest_demand


def risk_level(coverage):
    if coverage >= 90:
        return "Low"
    if coverage >= 75:
        return "Medium"
    return "High"



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

FORECAST_HOURS = 36


def generate_forecast():
    df, latest_row, X_latest_renewable, X_latest_demand = build_latest_feature_row()

    response = {"value": []}
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

        supabase.table("forecasts").upsert(
            forecast_record,
            on_conflict="forecast_timestamp"
        ).execute()

        response["value"].append(forecast_record)

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
        "message": "36-hour forecast generated and stored successfully.",
        "latest_actual_timestamp": str(latest_row["timestamp"]),
        "forecast_hours": FORECAST_HOURS,
        "count": len(response["value"]),
        "value": response["value"],
    }


@app.get("/")
def root():
    return {"message": "Tasmania Grid Intelligence API is running"}

@app.get("/forecasts")
def get_forecasts():
    if "value" in forecast_cache:
        return forecast_cache["value"]

    response = (
        supabase.table("forecasts")
        .select("*")
        .order("forecast_timestamp", desc=True)
        .limit(36)
        .execute()
    )

    rows = response.data

    rows = sorted(
        rows,
        key=lambda x: x["forecast_timestamp"]
    )

    result = {
        "count": len(rows),
        "value": rows,
    }

    forecast_cache["value"] = result
    return result


@app.get("/summary")
def get_summary():
    if "value" in summary_cache:
        return summary_cache["value"]

    response = (
        supabase.table("forecasts")
        .select("*")
        .order("forecast_timestamp", desc=True)
        .limit(36)
        .execute()
    )

    forecasts = response.data

    df = pd.DataFrame(forecasts)

    peak_idx = df["predicted_demand_mw"].idxmax()
    peak_renewable_idx = df["predicted_renewable_mw"].idxmax()
    low_idx = df["predicted_renewable_mw"].idxmin()
    price_idx = df["estimated_price_per_mwh"].idxmax()

    result = {

        "peak_demand": {
            "value_mw": round(df.loc[peak_idx, "predicted_demand_mw"], 2),
            "timestamp": df.loc[peak_idx, "forecast_timestamp"]
        },

        "peak_renewable": {
            "value_mw": round(df.loc[peak_renewable_idx, "predicted_renewable_mw"], 2),
            "timestamp": df.loc[peak_renewable_idx, "forecast_timestamp"]
        },

        "lowest_renewable": {
            "value_mw": round(df.loc[low_idx, "predicted_renewable_mw"], 2),
            "timestamp": df.loc[low_idx, "forecast_timestamp"]
        },

        "highest_price": {
            "value_per_mwh": round(df.loc[price_idx, "estimated_price_per_mwh"], 2),
            "timestamp": df.loc[price_idx, "forecast_timestamp"]
        },

        "average_demand_mw":
            round(df["predicted_demand_mw"].mean(), 2),

        "average_renewable_mw":
            round(df["predicted_renewable_mw"].mean(), 2),

        "average_price_per_mwh":
            round(df["estimated_price_per_mwh"].mean(), 2),

        "average_renewable_coverage_percent":
            round(df["renewable_coverage_percent"].mean(), 2),

        "highest_risk":
            df["risk_level"].max()
    }

    summary_cache["value"] = result
    return result

@app.get("/current")
def get_current():
    if "value" in current_cache:
        return current_cache["value"]

    response = (
        supabase.table("energy_readings")
        .select("*")
        .order("timestamp", desc=True)
        .limit(1)
        .execute()
    )

    latest = response.data[0]

    result = {
        "timestamp": latest["timestamp"],
        "region": latest["region"],
        "current_demand_mw": round(float(latest["demand_mw"]), 2),
        "current_renewable_mw": round(float(latest["renewable_mw"]), 2),
        "current_price_per_mwh": round(float(latest["price_per_mwh"]), 2),
        "renewable_coverage_percent": round(
            float(latest["renewable_mw"]) / float(latest["demand_mw"]) * 100,
            2
        )
    }

    current_cache["value"] = result
    return result


@app.get("/health")
def health():

    try:

        energy = (
            supabase.table("energy_readings")
            .select("timestamp")
            .order("timestamp", desc=True)
            .limit(1)
            .execute()
        )

        forecasts = (
            supabase.table("forecasts")
            .select("forecast_timestamp")
            .order("forecast_timestamp", desc=True)
            .limit(1)
            .execute()
        )

        latest_energy = (
            energy.data[0]["timestamp"]
            if energy.data else None
        )

        latest_forecast = (
            forecasts.data[0]["forecast_timestamp"]
            if forecasts.data else None
        )

        return {
            "status": "healthy",
            "latest_energy_reading": latest_energy,
            "latest_forecast": latest_forecast,
            "models_loaded": True
        }

    except Exception as e:

        return {
            "status": "unhealthy",
            "error": str(e)
        }