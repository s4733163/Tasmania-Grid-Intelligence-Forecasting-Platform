from datetime import datetime, timedelta
import os
import time

import pandas as pd
from dotenv import load_dotenv
from openelectricity import OEClient
from openelectricity.client import APIError
from openelectricity.types import MarketMetric


# -------------------------------------------------------------------
# Load environment variables
# -------------------------------------------------------------------
# The Open Electricity API key is stored in the .env file so that it
# is not hardcoded directly inside the source code.
load_dotenv()

api_key = os.getenv("OPENELECTRICITY_API_KEY")

if not api_key:
    raise SystemExit("OPENELECTRICITY_API_KEY not found. Please check your .env file.")


# -------------------------------------------------------------------
# Initialise Open Electricity API client
# -------------------------------------------------------------------
# This client is used to fetch historical electricity market data from
# the Open Electricity API.
client = OEClient(
    api_key=api_key,
    base_url="https://api.openelectricity.org.au/v4",
)


# -------------------------------------------------------------------
# ETL configuration
# -------------------------------------------------------------------
# We are fetching Tasmania electricity market data for the last 2 years.
#
# Required metrics:
# - DEMAND: actual electricity demand in MW
# - PRICE: wholesale electricity price in $/MWh
# - GENERATION_RENEWABLE: renewable electricity generation in MW
#
# Data is fetched in 30-day chunks to avoid large API requests.
METRICS = [
    MarketMetric.DEMAND,
    MarketMetric.PRICE,
    MarketMetric.GENERATION_RENEWABLE,
]

CHUNK = timedelta(days=30)
LOOKBACK = timedelta(days=730)
SLEEP_SECONDS = 0.3
OUTPUT_CSV = "tas1_market_raw.csv"


# -------------------------------------------------------------------
# Define extraction window
# -------------------------------------------------------------------
# The script starts from the current date and works backwards until it
# reaches the 2-year lookback target.
now = datetime.now()
target = now - LOOKBACK

rows = []
cursor = now


# -------------------------------------------------------------------
# Extract data from Open Electricity API
# -------------------------------------------------------------------
# Each API request fetches up to 30 days of hourly data for Tasmania.
# The loop continues backwards until the full 2-year period is covered.
while cursor > target:
    chunk_start = max(cursor - CHUNK, target)
    chunk_end = cursor

    try:
        response = client.get_market(
            network_code="NEM",
            metrics=METRICS,
            interval="1h",
            date_start=chunk_start,
            date_end=chunk_end,
            network_region="TAS1",
            primary_grouping="network_region",
        )

    except APIError as e:
        print(f"Stopped at {chunk_start.date()} → {chunk_end.date()}: {e}")
        break

    # ----------------------------------------------------------------
    # Flatten API response
    # ----------------------------------------------------------------
    # The API returns nested time-series objects. This section converts
    # them into a simple row-based format suitable for Pandas and CSV.
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

    print(f"Fetched {chunk_start.date()} → {chunk_end.date()} ({len(rows)} rows so far)")

    # Move the cursor backwards to fetch the previous 30-day period.
    cursor = chunk_start

    # Small delay to avoid hitting API rate limits.
    time.sleep(SLEEP_SECONDS)


# -------------------------------------------------------------------
# Transform data into long format
# -------------------------------------------------------------------
# Remove duplicate records where timestamp, region, and metric are the same.
df_long = pd.DataFrame(rows).drop_duplicates(
    subset=["timestamp", "region", "metric"]
)


# -------------------------------------------------------------------
# Transform data into wide format
# -------------------------------------------------------------------
# Convert rows like:
# timestamp | metric | value
#
# into:
# timestamp | demand_mw | price_per_mwh | renewable_mw
df = (
    # Take the values in the metric column and turn them into individual columns.
    # Each timestamp-region combination should become one row.
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


# -------------------------------------------------------------------
# Load output into CSV landing file
# -------------------------------------------------------------------
# This CSV acts as a raw landing file. It can be loaded into Supabase
# and reused later for ML model training.
df.to_csv(
    OUTPUT_CSV,
    index=False,
    date_format="%Y-%m-%dT%H:%M:%S%z",
)


# -------------------------------------------------------------------
# Print summary
# -------------------------------------------------------------------
print(f"\nWrote {len(df)} rows × {df.shape[1]} cols → {os.path.abspath(OUTPUT_CSV)}")
print(df.head())