import os
from datetime import datetime

import pandas as pd
import matplotlib.pyplot as plt
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
        .order("timestamp")
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
# 4. Setup output directory for figures and report
# -------------------------------------------------------------------
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "figures")
os.makedirs(OUTPUT_DIR, exist_ok=True)

REPORT_PATH = os.path.join(OUTPUT_DIR, "eda_report.txt")


# -------------------------------------------------------------------
# 5. Convert timestamp into datetime format
# -------------------------------------------------------------------
df["timestamp"] = pd.to_datetime(df["timestamp"])


# -------------------------------------------------------------------
# 6. Build the report
# -------------------------------------------------------------------
report_lines = []


def section(title):
    report_lines.append("")
    report_lines.append("=" * 60)
    report_lines.append(f"  {title}")
    report_lines.append("=" * 60)


def write(text=""):
    report_lines.append(str(text))


section("REPORT METADATA")
write(f"Generated at : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
write(f"Source table  : {TABLE_NAME}")
write(f"Total rows    : {len(df)}")
write(f"Date range    : {df['timestamp'].min()} → {df['timestamp'].max()}")


# -------------------------------------------------------------------
# 7. Dataset overview
# -------------------------------------------------------------------
section("DATASET OVERVIEW")
write(f"Shape: {df.shape[0]} rows x {df.shape[1]} columns")
write()
write("Column Types:")
write(df.dtypes.to_string())
write()
write("First 5 Rows:")
write(df.head().to_string())
write()
write("Summary Statistics:")
write(df[["demand_mw", "renewable_mw", "price_per_mwh"]].describe().to_string())


# -------------------------------------------------------------------
# 8. Missing value check
# -------------------------------------------------------------------
section("MISSING VALUES")
write(df.isnull().sum().to_string())


# -------------------------------------------------------------------
# 9. Duplicate check
# -------------------------------------------------------------------
section("DUPLICATE CHECK")

duplicate_rows = df.duplicated().sum()
duplicate_timestamp_region = df.duplicated(
    subset=["timestamp", "region"]
).sum()

write(f"Duplicate full rows            : {duplicate_rows}")
write(f"Duplicate timestamp-region rows : {duplicate_timestamp_region}")


# -------------------------------------------------------------------
# 10. Create time-based columns for analysis
# -------------------------------------------------------------------
df["hour"] = df["timestamp"].dt.hour
df["day_of_week"] = df["timestamp"].dt.dayofweek
df["month"] = df["timestamp"].dt.month
df["is_weekend"] = df["day_of_week"].isin([5, 6])


# -------------------------------------------------------------------
# 11. Renewable coverage
# -------------------------------------------------------------------
df["renewable_coverage_percent"] = (
    df["renewable_mw"] / df["demand_mw"]
) * 100

section("RENEWABLE COVERAGE")
write(df["renewable_coverage_percent"].describe().to_string())


# -------------------------------------------------------------------
# 12. Correlation matrix
# -------------------------------------------------------------------
correlation = df[
    ["demand_mw", "renewable_mw", "price_per_mwh"]
].corr()

section("CORRELATION MATRIX")
write(correlation.to_string())


# -------------------------------------------------------------------
# 13. Hourly demand pattern
# -------------------------------------------------------------------
hourly_demand = df.groupby("hour")["demand_mw"].mean()

section("AVERAGE DEMAND BY HOUR")
write(hourly_demand.to_string())


# -------------------------------------------------------------------
# 14. Monthly demand pattern
# -------------------------------------------------------------------
monthly_demand = df.groupby("month")["demand_mw"].mean()

section("AVERAGE DEMAND BY MONTH")
write(monthly_demand.to_string())


# -------------------------------------------------------------------
# 15. Weekday vs weekend demand
# -------------------------------------------------------------------
weekend_demand = df.groupby("is_weekend")["demand_mw"].mean()

section("WEEKDAY VS WEEKEND DEMAND")
write(f"Weekday average : {weekend_demand[False]:.2f} MW")
write(f"Weekend average : {weekend_demand[True]:.2f} MW")


# -------------------------------------------------------------------
# 16. Write report to file
# -------------------------------------------------------------------
report_text = "\n".join(report_lines)

with open(REPORT_PATH, "w") as f:
    f.write(report_text)

print(f"Report saved to: {os.path.abspath(REPORT_PATH)}")


# -------------------------------------------------------------------
# 17. Generate and save figures
# -------------------------------------------------------------------
print("Generating figures...")

plt.figure(figsize=(15, 5))
plt.plot(df["timestamp"], df["demand_mw"])
plt.title("Tasmania Electricity Demand Over Time")
plt.xlabel("Time")
plt.ylabel("Demand (MW)")
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "demand_over_time.png"))
plt.close()

plt.figure(figsize=(15, 5))
plt.plot(df["timestamp"], df["renewable_mw"])
plt.title("Tasmania Renewable Generation Over Time")
plt.xlabel("Time")
plt.ylabel("Renewable Generation (MW)")
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "renewable_over_time.png"))
plt.close()

plt.figure(figsize=(15, 5))
plt.plot(df["timestamp"], df["price_per_mwh"])
plt.title("Tasmania Electricity Price Over Time")
plt.xlabel("Time")
plt.ylabel("Price ($/MWh)")
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "price_over_time.png"))
plt.close()

plt.figure(figsize=(8, 5))
plt.hist(df["demand_mw"].dropna(), bins=50)
plt.title("Distribution of Electricity Demand")
plt.xlabel("Demand (MW)")
plt.ylabel("Frequency")
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "demand_distribution.png"))
plt.close()

plt.figure(figsize=(8, 5))
plt.hist(df["renewable_mw"].dropna(), bins=50)
plt.title("Distribution of Renewable Generation")
plt.xlabel("Renewable Generation (MW)")
plt.ylabel("Frequency")
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "renewable_distribution.png"))
plt.close()

plt.figure(figsize=(6, 5))
plt.imshow(correlation)
plt.xticks(range(len(correlation.columns)), correlation.columns, rotation=45)
plt.yticks(range(len(correlation.columns)), correlation.columns)
plt.title("Correlation Matrix")
for i in range(len(correlation.columns)):
    for j in range(len(correlation.columns)):
        plt.text(j, i, f"{correlation.iloc[i, j]:.2f}", ha="center", va="center")
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "correlation_matrix.png"))
plt.close()

plt.figure(figsize=(10, 5))
plt.plot(hourly_demand.index, hourly_demand.values, marker="o")
plt.title("Average Demand by Hour of Day")
plt.xlabel("Hour of Day")
plt.ylabel("Average Demand (MW)")
plt.xticks(range(0, 24))
plt.grid(True)
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "demand_by_hour.png"))
plt.close()

plt.figure(figsize=(10, 5))
plt.plot(monthly_demand.index, monthly_demand.values, marker="o")
plt.title("Average Demand by Month")
plt.xlabel("Month")
plt.ylabel("Average Demand (MW)")
plt.xticks(range(1, 13))
plt.grid(True)
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "demand_by_month.png"))
plt.close()

plt.figure(figsize=(6, 5))
plt.bar(["Weekday", "Weekend"], weekend_demand.values)
plt.title("Average Demand: Weekday vs Weekend")
plt.xlabel("Day Type")
plt.ylabel("Average Demand (MW)")
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "weekday_vs_weekend.png"))
plt.close()

plt.figure(figsize=(15, 5))
plt.plot(df["timestamp"], df["renewable_coverage_percent"])
plt.title("Renewable Coverage Over Time")
plt.xlabel("Time")
plt.ylabel("Renewable Coverage (%)")
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "renewable_coverage.png"))
plt.close()


# -------------------------------------------------------------------
# 18. Final summary
# -------------------------------------------------------------------
print("\nAll outputs saved to:", os.path.abspath(OUTPUT_DIR))
for f in sorted(os.listdir(OUTPUT_DIR)):
    print(f"  - {f}")