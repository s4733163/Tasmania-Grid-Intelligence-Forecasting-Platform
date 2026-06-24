import os
import time
from datetime import datetime, timedelta

import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client
from openelectricity import OEClient
from openelectricity.client import APIError
from openelectricity.types import MarketMetric

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
api_key = os.getenv("OPENELECTRICITY_API_KEY")

TABLE_NAME = "energy_readings"
BATCH_SIZE = 500
CHUNK = timedelta(days=30)
SLEEP_SECONDS = 0.3
RETENTION = timedelta(days=730)

METRICS = [
    MarketMetric.DEMAND,
    MarketMetric.PRICE,
    MarketMetric.GENERATION_RENEWABLE,
]

if not SUPABASE_URL or not SUPABASE_KEY:
    raise SystemExit("SUPABASE_URL or SUPABASE_KEY not found in .env")

if not api_key:
    raise SystemExit("OPENELECTRICITY_API_KEY not found in .env")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

client = OEClient(
    api_key=api_key,
    base_url="https://api.openelectricity.org.au/v4",
)

# -------------------------------------------------------------------
# 1. Determine the fetch window
# -------------------------------------------------------------------
response = (
    supabase.table(TABLE_NAME)
    .select("*")
    .order("timestamp", desc=True)
    .limit(1)
    .execute()
)

latest = response.data[0]["timestamp"] if response.data else None

if not latest:
    raise SystemExit("No existing data in the database. Run the initial ETL first.")

now = datetime.now()
now = now.replace(minute=0, second=0, microsecond=0)

start = pd.to_datetime(latest).to_pydatetime()
if start.tzinfo is not None:
    start = start.astimezone(tz=None).replace(tzinfo=None)

if start >= now:
    print("Already up to date. No new data to fetch.")
    raise SystemExit(0)

# -------------------------------------------------------------------
# 2. Fetch new data from the Open Electricity API
# -------------------------------------------------------------------
rows = []
cursor = start

print(f"Fetching new data from {cursor} → {now}")

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
        print(f"Stopped at {cursor.date()} → {chunk_end.date()}: {e}")
        break

    for timeseries in response.data:
        for result in timeseries.results:
            region = result.name.split("_")[-1]

            for point in result.data:
                rows.append({
                    "timestamp": point.timestamp,
                    "region": region,
                    "metric": timeseries.metric,
                    "value": point.value,
                    "unit": timeseries.unit,
                })

    print(f"Fetched {cursor.date()} → {chunk_end.date()} ({len(rows)} rows so far)")

    cursor = chunk_end
    time.sleep(SLEEP_SECONDS)

if not rows:
    print("No new data to insert.")
else:
    # -------------------------------------------------------------------
    # 3. Transform and insert into the database
    # -------------------------------------------------------------------
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

    df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.strftime("%Y-%m-%dT%H:%M:%S%z")

    df = df[["timestamp", "region", "demand_mw", "price_per_mwh", "renewable_mw"]]
    df = df.where(pd.notnull(df), None)

    records = df.to_dict(orient="records")

    print(f"Inserting {len(records)} new rows into {TABLE_NAME}...")

    for i in range(0, len(records), BATCH_SIZE):
        batch = records[i : i + BATCH_SIZE]

        supabase.table(TABLE_NAME).upsert(
            batch, on_conflict="timestamp,region"
        ).execute()

        print(f"Inserted batch {i // BATCH_SIZE + 1}: {len(batch)} rows")

    print("New data inserted successfully.")

# -------------------------------------------------------------------
# 4. Prune old entries beyond the 2-year retention window
# -------------------------------------------------------------------
cutoff = (now - RETENTION).strftime("%Y-%m-%dT%H:%M:%S+00:00")

print(f"Pruning entries older than {cutoff}...")

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

    print(f"Deleted batch: {deleted_count} rows (total deleted: {deleted_total})")

print(f"Pruning complete. Removed {deleted_total} rows older than {cutoff}.")


