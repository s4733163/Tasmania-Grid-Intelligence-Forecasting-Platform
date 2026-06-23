import os
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client

# -------------------------------------------------------------------
# Load environment variables
# -------------------------------------------------------------------
# Supabase credentials are stored in the .env file so that sensitive
# information is not hardcoded directly in the source code.
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# -------------------------------------------------------------------
# ETL configuration
# -------------------------------------------------------------------
# CSV_FILE:
# Historical Tasmania energy market dataset generated during the
# extraction phase from the Open Electricity API.
#
# TABLE_NAME:
# Destination table in Supabase.
#
# BATCH_SIZE:
# Number of records inserted per request to avoid excessively large
# payloads and improve insertion reliability.
CSV_FILE = "tas1_market_raw.csv"
TABLE_NAME = "energy_readings"
BATCH_SIZE = 500

# Validate required environment variables before continuing.
if not SUPABASE_URL or not SUPABASE_KEY:
    raise SystemExit("SUPABASE_URL or SUPABASE_KEY not found in .env")

# -------------------------------------------------------------------
# Create Supabase client
# -------------------------------------------------------------------
# Establish a connection to the Supabase PostgreSQL database.
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# -------------------------------------------------------------------
# Read extracted CSV dataset
# -------------------------------------------------------------------
# Load the transformed Tasmania energy market dataset into a Pandas
# DataFrame for preprocessing before database insertion.
df = pd.read_csv(CSV_FILE)

# -------------------------------------------------------------------
# Standardise timestamp format
# -------------------------------------------------------------------
# Convert timestamps into a consistent ISO-8601 format that can be
# safely inserted into the TIMESTAMPTZ column in PostgreSQL.
df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.strftime("%Y-%m-%dT%H:%M:%S%z")

# -------------------------------------------------------------------
# Select required database columns
# -------------------------------------------------------------------
# Keep only the columns that exist in the destination table.
# This avoids accidentally inserting unnecessary fields.
df = df[
    [
        "timestamp",
        "region",
        "demand_mw",
        "price_per_mwh",
        "renewable_mw",
    ]
]

# -------------------------------------------------------------------
# Handle missing values
# -------------------------------------------------------------------
# Convert Pandas NaN values into Python None values so PostgreSQL can
# store them as NULL.
df = df.where(pd.notnull(df), None)

# Convert DataFrame rows into dictionaries for Supabase insertion.
records = df.to_dict(orient="records")

print(f"Preparing to insert {len(records)} rows into {TABLE_NAME}...")

# -------------------------------------------------------------------
# Load data into Supabase
# -------------------------------------------------------------------
# Records are inserted in batches to reduce request size and improve
# performance.
#
# Upsert is used so that if a record with the same
# (timestamp, region) already exists, it is updated rather than
# creating a duplicate row.
for i in range(0, len(records), BATCH_SIZE):
    batch = records[i : i + BATCH_SIZE]

    response = (
        supabase.table(TABLE_NAME)
        .upsert(batch, on_conflict="timestamp,region")
        .execute()
    )

    print(f"Inserted batch {i // BATCH_SIZE + 1}: {len(batch)} rows")

# -------------------------------------------------------------------
# ETL load complete
# -------------------------------------------------------------------
# At this stage the historical Tasmania energy market dataset has been
# successfully loaded into Supabase and is ready for analysis,
# forecasting model training, and dashboard visualisation.
print("CSV data loaded into Supabase successfully.")