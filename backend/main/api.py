from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from cachetools import TTLCache
import os
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
CACHE_TTL = 300  # 5 minutes

current_cache = TTLCache(maxsize=1, ttl=CACHE_TTL)
forecast_cache = TTLCache(maxsize=1, ttl=CACHE_TTL)
summary_cache = TTLCache(maxsize=1, ttl=CACHE_TTL)



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

    if "High" in df["risk_level"].values:
        highest_risk = "High"
    elif "Medium" in df["risk_level"].values:
        highest_risk = "Medium"
    else:
        highest_risk = "Low"

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
            highest_risk
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
        }

    except Exception as e:

        return {
            "status": "unhealthy",
            "error": str(e)
        }