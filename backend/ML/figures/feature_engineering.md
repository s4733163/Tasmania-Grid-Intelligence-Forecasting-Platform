# Feature Engineering

Feature engineering is the process of transforming raw data into meaningful input variables that improve the predictive performance of machine learning models. It sits between Exploratory Data Analysis (EDA) and model training as the critical bridge that converts human understanding of the data into a numerical form that algorithms can learn from.

In the context of the Tasmania Grid Intelligence & Forecasting Platform, the raw `energy_readings` dataset contains hourly snapshots of the Tasmanian electricity grid — demand, renewable generation, and wholesale price — but each observation exists in isolation. A single row tells the model *what is happening now*, but provides no information about *what happened before* or *when this observation occurred*. Without temporal context and historical memory, a forecasting model cannot learn the patterns that drive future electricity demand and renewable output.

Feature engineering solves this by constructing three classes of derived variables:

1. **Time-based features** — encode *when* an observation occurred (hour, day, month, weekday/weekend).
2. **Lag features** — encode *what happened previously* at strategically chosen intervals (1 hour, 24 hours, 168 hours).
3. **Rolling average features** — encode *recent trends* by smoothing short-term noise over a 24-hour window.

These engineered features, combined with the original variables, form the complete input dataset for training the demand and renewable generation forecasting models.

```
┌─────────────────────┐
│   Raw Supabase      │
│   energy_readings   │
│   (17,510 rows)     │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Time-Based Feature │
│     Extraction      │
│  (hour, month, etc) │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│   Lag Feature        │
│   Construction       │
│  (1h, 24h, 168h)    │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Rolling Average     │
│   Computation        │
│  (24h window)        │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Target Variable     │
│   Creation           │
│  (1h forward shift)  │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Drop Incomplete     │
│   Rows (dropna)      │
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  Feature Dataset     │
│  (ML-ready output)   │
│  feature_dataset.csv │
└─────────────────────┘
```

---

# Input Dataset

The raw dataset is retrieved from the `energy_readings` table in Supabase. It contains **17,510 hourly observations** covering the period from **24 June 2024 to 24 June 2026**, all sourced from the **TAS1** region (Tasmania) within the Australian National Electricity Market (NEM).

Each record contains the following fields:

| Column | Description | Unit |
|---|---|---|
| `timestamp` | The date and hour of the observation | UTC datetime |
| `region` | NEM region identifier (always `TAS1`) | — |
| `demand_mw` | Total electricity demand for the interval | MW |
| `renewable_mw` | Total renewable electricity generation | MW |
| `price_per_mwh` | Wholesale spot electricity price | $/MWh |

These five variables describe the **current state** of the Tasmanian electricity grid at each hour. However, they do not contain any information about what the grid looked like one hour ago, one day ago, or one week ago. They also do not encode *when* the observation occurred — the timestamp is stored as a datetime object, not as a set of numerical features that a model can interpret.

For a forecasting model to predict future demand or renewable output, it needs access to:

- **Temporal position** — Is it 3 AM or 6 PM? Is it July (winter) or January (summer)?
- **Recent history** — What was demand one hour ago? Is it rising or falling?
- **Cyclical history** — What was demand at this same hour yesterday, or this same day last week?

The feature engineering pipeline constructs all of these from the raw dataset.

---

# Time-Based Features

Time-based features are extracted directly from the `timestamp` column. They encode the temporal position of each observation as discrete numerical values, allowing the model to learn demand and generation patterns that recur at specific times, days, or seasons.

## Feature Definitions

| Feature | Derivation | Value Range | Description |
|---|---|---|---|
| `hour` | `timestamp.dt.hour` | 0–23 | The hour of the day |
| `day` | `timestamp.dt.day` | 1–31 | The day of the month |
| `month` | `timestamp.dt.month` | 1–12 | The calendar month |
| `day_of_week` | `timestamp.dt.dayofweek` | 0 (Mon) – 6 (Sun) | The day of the week |
| `is_weekend` | `day_of_week ∈ {5, 6}` | 0 or 1 | Binary weekend indicator |

## Why Each Feature Was Created

### Hour

The EDA revealed a clear **twin-peak daily demand pattern** in Tasmania:

- **Morning peak** at 08:00 (~1,207 MW) driven by residential and commercial activity.
- **Evening peak** at 21:00 (~1,156 MW) driven by household heating and lighting.
- **Overnight trough** at 03:00–04:00 (~975 MW) when activity is minimal.

The `hour` feature allows the model to learn these intra-day patterns. Without it, the model would have no way to distinguish a 3 AM observation from a 6 PM observation — two points that differ by approximately 230 MW in average demand.

### Day

The `day` feature captures the position within the month. While daily patterns are less pronounced than hourly or seasonal ones, certain billing cycles, industrial schedules, and end-of-month demand variations can introduce subtle patterns that improve forecasting accuracy.

### Month

The EDA identified **strong seasonal demand variation** in Tasmania:

| Season | Representative Month | Avg Demand (MW) |
|---|---|---|
| Winter (peak) | July | 1,260.92 |
| Summer (trough) | February | 948.10 |

Peak winter demand exceeds the summer trough by approximately **33%**, driven almost entirely by heating load. The `month` feature gives the model direct access to this seasonal signal, enabling it to adjust predictions based on the time of year.

### Day of Week

The EDA found a small but consistent difference between weekday and weekend demand:

| Day Type | Avg Demand (MW) |
|---|---|
| Weekday | 1,067.63 |
| Weekend | 1,048.92 |

The ~1.8% difference reflects reduced commercial and industrial activity on weekends. The `day_of_week` feature allows the model to learn day-specific demand profiles across all seven days, capturing any variation between Monday and Friday as well.

### Weekend Flag

The `is_weekend` feature is a binary simplification of `day_of_week` that explicitly separates weekdays (0) from weekends (1). While `day_of_week` already encodes this information implicitly, the binary flag provides a direct, interpretable signal that tree-based models and linear models can use without needing to learn the mapping from {5, 6} → weekend.

---

# Lag Features

Lag features capture the historical values of a variable at specific past time steps. In time-series forecasting, the most important predictor of a future value is often its own past values — a principle known as **autocorrelation**. Lag features make this historical information explicitly available to the model.

## Concept

A lag feature shifts a variable backward by a fixed number of time steps. For example, `demand_lag_1` at time *t* contains the demand value from time *t − 1* (one hour ago). The model can then learn relationships such as: *"If demand was high one hour ago, it is likely to remain high now."*

Three lag intervals were selected based on the dominant cycles identified during EDA:

| Lag Interval | Hours | Captures |
|---|---|---|
| 1 hour | 1 | Immediate system continuity |
| 24 hours | 24 | Daily recurring cycle |
| 168 hours | 168 (7 × 24) | Weekly recurring behaviour |

## Demand Lag Features

| Feature | Definition | Rationale |
|---|---|---|
| `demand_lag_1` | Demand at *t − 1* | Electricity demand changes gradually hour-to-hour. The previous hour's demand is the strongest single predictor of the current hour, capturing immediate system inertia. |
| `demand_lag_24` | Demand at *t − 24* | The EDA showed a twin-peak daily demand profile. This lag tells the model what demand looked like at the same hour yesterday, capturing the daily cycle directly. |
| `demand_lag_168` | Demand at *t − 168* | Weekday and weekend demand differ. This lag captures what demand was at the same hour, on the same day of the week, one week ago — encoding weekly periodicity. |

```
Example: demand_lag construction for a Wednesday 10:00 observation

demand_lag_1   →  Wednesday 09:00   (1 hour ago)
demand_lag_24  →  Tuesday 10:00     (same hour yesterday)
demand_lag_168 →  Wednesday 10:00   (same hour, same weekday, last week)
```

## Renewable Generation Lag Features

| Feature | Definition | Rationale |
|---|---|---|
| `renewable_lag_1` | Renewable output at *t − 1* | Renewable generation (primarily hydro and wind in Tasmania) has short-term persistence — output one hour ago strongly predicts output now. |
| `renewable_lag_24` | Renewable output at *t − 24* | Weather patterns and hydro dispatch schedules often repeat on a daily basis. The 24-hour lag captures this daily pattern. |
| `renewable_lag_168` | Renewable output at *t − 168* | Weekly hydro storage management and weather system cycles introduce 7-day periodicity in renewable output. |

The EDA showed that renewable generation is substantially more volatile than demand (standard deviation of 288 MW vs. 157 MW), with a bimodal distribution reflecting distinct high-output and low-output operating regimes. Lag features are especially important for renewable forecasting because they provide the model with information about *which regime* the system was recently operating in.

## Wholesale Price Lag Features

| Feature | Definition | Rationale |
|---|---|---|
| `price_lag_1` | Price at *t − 1* | Price exhibits short-term persistence during stable market conditions. The immediate prior price is a strong indicator of the current price level. |
| `price_lag_24` | Price at *t − 24* | Market conditions and generator bidding behaviour tend to produce similar prices at the same hour across consecutive days. |
| `price_lag_168` | Price at *t − 168* | Weekly industrial demand patterns and generator maintenance schedules create 7-day price cycles. |

Although price is not a direct prediction target in the current platform, price lag features serve as important **contextual inputs** for the demand and renewable models. The EDA revealed that demand and price have a positive correlation (0.20), and extreme price events (up to $11,873/MWh) often coincide with periods of constrained supply or unusually high demand. Including price history gives the model additional context about market stress conditions.

---

# Rolling Average Features

While lag features capture values at specific past time steps, rolling averages capture the **general trend** over a recent window. They smooth out short-term fluctuations and provide the model with a measure of where the system has been trending, rather than where it was at a single point.

## Concept

A rolling average computes the mean of a variable over a sliding window of consecutive past observations. For this project, a **24-hour rolling window** is applied to demand, renewable generation, and wholesale price.

The rolling average is computed on the **shifted** series (i.e., starting from *t − 1*), ensuring that the current hour's value is excluded from the average. This prevents data leakage — the model only sees information that would genuinely be available at prediction time.

```
Rolling Average Computation (24-hour window)

Time t:   rolling_avg = mean(value[t-24], value[t-23], ..., value[t-1])
                        └──────────── 24 values ────────────────┘

The current value at time t is NOT included.
```

## Feature Definitions

| Feature | Definition | Rationale |
|---|---|---|
| `demand_rolling_24` | Mean demand over the previous 24 hours | Captures whether demand has been generally high or low over the past day. Smooths out the twin-peak daily pattern to reveal the underlying demand level — useful for distinguishing a winter day (high baseline) from a summer day (low baseline). |
| `renewable_rolling_24` | Mean renewable output over the previous 24 hours | Smooths the high volatility in renewable generation. Given the bimodal distribution identified in EDA, this feature helps the model assess whether the system is currently in a high-output or low-output regime. |
| `price_rolling_24` | Mean price over the previous 24 hours | Captures the recent market price environment. Since the EDA showed extreme price spikes can exceed $11,000/MWh while the median is ~$91/MWh, the rolling average provides a stable measure of prevailing market conditions, dampening the effect of isolated spikes. |

## Why a 24-Hour Window

The 24-hour window was selected because it aligns with the fundamental daily cycle in electricity markets:

- It spans exactly one complete demand cycle (overnight trough → morning peak → midday → evening peak → overnight).
- It is long enough to smooth out within-day volatility but short enough to remain responsive to multi-day shifts in weather, demand, or generation.
- It matches the natural planning horizon of grid operators, who typically assess system conditions over a rolling 24-hour period.

---

# Target Variables

## Supervised Learning

The forecasting models in this platform are trained using **supervised learning**, where each training example consists of a set of input features (the predictors) and a known output value (the target). During training, the model learns the relationship between inputs and target. During inference, the model uses current inputs to predict the target — a value that has not yet been observed.

## Target Construction

The prediction targets are created by shifting the raw demand and renewable generation columns **one step forward** in time using `shift(-1)`. This means that at every row, the target contains the value from the **next hour** — the value the model is trained to predict.

| Feature | Definition | Purpose |
|---|---|---|
| `target_demand_next_hour` | `demand_mw` at time *t + 1* | Prediction target for the Electricity Demand Forecasting Model |
| `target_renewable_next_hour` | `renewable_mw` at time *t + 1* | Prediction target for the Renewable Generation Forecasting Model |

## How the Shift Creates the Prediction Target

The following table illustrates how a forward shift transforms the dataset into a supervised learning format:

| Row | Timestamp | demand_mw | hour | demand_lag_1 | ... | target_demand_next_hour |
|---|---|---|---|---|---|---|
| 1 | 2024-07-05 14:00 | 1,334.41 | 14 | 1,370.63 | ... | **1,303.82** |
| 2 | 2024-07-05 15:00 | 1,303.82 | 15 | 1,334.41 | ... | **1,290.70** |
| 3 | 2024-07-05 16:00 | 1,290.70 | 16 | 1,303.82 | ... | **1,256.33** |
| ... | ... | ... | ... | ... | ... | ... |
| *last* | 2026-06-24 23:00 | *value* | 23 | *value* | ... | **NaN** |

Each row represents the complete information available to the model **at prediction time** — temporal position, historical lags, and rolling trends. The target column contains the value **one hour into the future** that the model learns to predict. The final row has no target because no observation exists at *t + 1*.

```
Information Flow at Prediction Time

     Past                          Now                     Future
─────┬──────┬──────┬──────────────┬──────────────────────────┬─────
     │      │      │              │                          │
   t-168  t-24   t-1             t                         t+1
     │      │      │              │                          │
  lag_168 lag_24 lag_1    current features         TARGET (predicted)
     │      │      │              │                          │
     └──────┴──────┴──── INPUT ───┘                   OUTPUT
```

---

# Handling Missing Values

Feature engineering intentionally introduces missing values (`NaN`) in two regions of the dataset. These are **expected structural gaps**, not data quality issues — the original dataset contains zero missing values.

## Sources of Missing Values

### Lag Feature Warm-Up Period (First 168 Rows)

Lag features require historical data that does not exist at the beginning of the dataset. For example:

| Feature | Requires Data From | Available At Row |
|---|---|---|
| `demand_lag_1` | *t − 1* | Row 2 (row 1 has no predecessor) |
| `demand_lag_24` | *t − 24* | Row 25 |
| `demand_lag_168` | *t − 168* | Row 169 |
| `demand_rolling_24` | *t − 24* through *t − 1* | Row 169 (requires lag_1 + 24-hour window) |

The most restrictive feature is the 168-hour lag, which means the **first 168 rows** cannot have complete feature vectors.

### Target Variable (Final Row)

The forward-shifted target `shift(-1)` creates a `NaN` in the **last row** of the dataset because there is no observation at *t + 1* for the final timestamp.

## Removal Strategy

All rows containing any `NaN` value are removed using `dropna()`:

```
Original dataset:    17,510 rows
- Warm-up removal:     -168 rows  (first 168 rows, incomplete lag features)
- Target removal:        -1 row   (final row, no future value available)
                     ──────────
Feature dataset:     17,341 rows
```

This removal is safe because:

1. The dropped rows carry **no usable information** — a model cannot learn from incomplete inputs or missing targets.
2. The loss of 169 rows out of 17,510 represents less than **1%** of the dataset, with negligible impact on model training.
3. No data from the core observation period is discarded — only the structural edges created by the feature engineering process itself.

---

# Final Feature Dataset

The completed feature dataset is saved to `feature_dataset.csv` and contains the following columns, grouped by category:

## Time Features

| Feature | Type | Description |
|---|---|---|
| `hour` | Integer (0–23) | Hour of the day |
| `day` | Integer (1–31) | Day of the month |
| `month` | Integer (1–12) | Calendar month |
| `day_of_week` | Integer (0–6) | Day of the week (Monday = 0) |
| `is_weekend` | Binary (0/1) | Weekend indicator |

## Demand Features

| Feature | Type | Description |
|---|---|---|
| `demand_mw` | Float | Current hour electricity demand |
| `demand_lag_1` | Float | Demand 1 hour ago |
| `demand_lag_24` | Float | Demand 24 hours ago |
| `demand_lag_168` | Float | Demand 168 hours (1 week) ago |
| `demand_rolling_24` | Float | Mean demand over previous 24 hours |

## Renewable Features

| Feature | Type | Description |
|---|---|---|
| `renewable_mw` | Float | Current hour renewable generation |
| `renewable_lag_1` | Float | Renewable output 1 hour ago |
| `renewable_lag_24` | Float | Renewable output 24 hours ago |
| `renewable_lag_168` | Float | Renewable output 168 hours (1 week) ago |
| `renewable_rolling_24` | Float | Mean renewable output over previous 24 hours |

## Price Features

| Feature | Type | Description |
|---|---|---|
| `price_per_mwh` | Float | Current hour wholesale price |
| `price_lag_1` | Float | Price 1 hour ago |
| `price_lag_24` | Float | Price 24 hours ago |
| `price_lag_168` | Float | Price 168 hours (1 week) ago |
| `price_rolling_24` | Float | Mean price over previous 24 hours |

## Target Variables

| Feature | Type | Description |
|---|---|---|
| `target_demand_next_hour` | Float | Electricity demand at *t + 1* |
| `target_renewable_next_hour` | Float | Renewable generation at *t + 1* |

## Dataset Summary

| Property | Value |
|---|---|
| Total rows | ~17,341 |
| Total feature columns | 20 |
| Target columns | 2 |
| Time span | July 2024 — June 2026 |
| Temporal resolution | Hourly |
| Region | TAS1 (Tasmania) |

---

# Relationship Between EDA and Feature Engineering

Every feature in this pipeline was motivated by a specific finding from the Exploratory Data Analysis stage. Feature engineering does not add information that is not already present in the data — it restructures existing information into a form that machine learning algorithms can exploit.

The following table maps each EDA insight to the feature(s) it motivated:

| EDA Finding | Feature Created | Rationale |
|---|---|---|
| Twin-peak daily demand profile (morning at 08:00, evening at 21:00) | `hour` | Encodes the intra-day position so the model can learn hour-specific demand levels. |
| Strong seasonal demand cycle (winter peak ~33% above summer trough) | `month` | Allows the model to adjust predictions based on seasonal heating load. |
| Weekday demand ~1.8% higher than weekend | `day_of_week`, `is_weekend` | Captures the small but consistent weekly pattern in commercial and industrial demand. |
| Demand follows gradual hour-to-hour transitions | `demand_lag_1` | The previous hour is the strongest single predictor of the next hour. |
| Demand repeats daily patterns | `demand_lag_24` | Same-hour-yesterday demand captures the daily cycle directly. |
| Weekday vs weekend demand differences persist week-to-week | `demand_lag_168` | Same-hour, same-weekday demand from last week captures weekly periodicity. |
| Renewable generation is highly volatile (std dev 288 MW) | `renewable_lag_1`, `renewable_lag_24`, `renewable_lag_168` | Lag features provide the model with information about the current operating regime. |
| Renewable distribution is bimodal (high vs low output regimes) | `renewable_rolling_24` | The 24-hour average indicates which regime the system has been operating in. |
| Price exhibits extreme spikes (max $11,873/MWh) with stable baseline | `price_lag_1`, `price_lag_24`, `price_lag_168` | Price history provides context about current market stress conditions. |
| Price spikes are transient but the baseline is stable | `price_rolling_24` | The rolling average dampens spike effects and reveals the prevailing price level. |
| Demand and price are positively correlated (0.20) | All price features as inputs to demand model | Price context improves demand prediction by signalling market stress periods. |

```
EDA → Feature Engineering Pipeline

┌──────────────────────────────┐      ┌──────────────────────────────┐
│         EDA Insights         │      │     Engineered Features      │
├──────────────────────────────┤      ├──────────────────────────────┤
│                              │      │                              │
│  Hourly demand patterns   ───┼──▶   │  hour                        │
│                              │      │                              │
│  Seasonal variation       ───┼──▶   │  month                       │
│                              │      │                              │
│  Weekday/weekend gap      ───┼──▶   │  day_of_week, is_weekend     │
│                              │      │                              │
│  Gradual demand changes   ───┼──▶   │  demand_lag_1                │
│                              │      │                              │
│  Daily demand cycle       ───┼──▶   │  demand_lag_24               │
│                              │      │                              │
│  Weekly demand pattern    ───┼──▶   │  demand_lag_168              │
│                              │      │                              │
│  Renewable volatility     ───┼──▶   │  renewable_lag_1/24/168      │
│                              │      │                              │
│  Bimodal renewable output ───┼──▶   │  renewable_rolling_24        │
│                              │      │                              │
│  Price spikes & baseline  ───┼──▶   │  price_lag_1/24/168          │
│                              │      │                              │
│  Stable price environment ───┼──▶   │  price_rolling_24            │
│                              │      │                              │
└──────────────────────────────┘      └──────────────────────────────┘
```

This direct linkage between analysis and engineering ensures that every feature has an empirical justification — no features were created speculatively.

---

# Outcome

The feature engineering pipeline transforms 17,510 raw hourly electricity market observations into a machine-learning-ready dataset of approximately 17,341 complete rows, each containing 20 input features and 2 prediction targets.

The engineered dataset encodes three distinct types of information:

| Information Type | Features | What It Captures |
|---|---|---|
| **Temporal position** | hour, day, month, day_of_week, is_weekend | *When* the observation occurred |
| **Historical state** | All lag features (1h, 24h, 168h) | *What happened before* at key intervals |
| **Recent trends** | All rolling average features (24h) | *Where the system is heading* |

Together, these features provide each observation with sufficient context for a machine learning model to learn the complex, multi-scale patterns that govern electricity demand and renewable generation in Tasmania.

This feature dataset serves as the direct input for training two forecasting models:

1. **Electricity Demand Forecasting Model** — predicts `target_demand_next_hour` using all 20 input features.
2. **Renewable Generation Forecasting Model** — predicts `target_renewable_next_hour` using all 20 input features.

Both models consume the same feature set, allowing a unified data pipeline and consistent feature engineering logic across the platform.

---

*Document generated for the Tasmania Grid Intelligence & Forecasting Platform.*
