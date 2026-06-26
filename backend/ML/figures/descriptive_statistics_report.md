# Tasmania Grid Intelligence — Descriptive Statistics Report

**Generated:** 25 June 2026
**Data Source:** `energy_readings` table (Supabase)
**Region:** TAS1 (Tasmania, NEM)
**Period:** 24 June 2024 — 24 June 2026 (2 years)
**Granularity:** Hourly
**Total Records:** 17,510

---

## 1. Dataset Quality

The dataset is clean and ready for modelling.

| Check | Result |
|---|---|
| Missing values | 0 across all columns |
| Duplicate rows | 0 |
| Duplicate timestamp-region pairs | 0 |

All 17,510 hourly readings contain complete values for demand, renewable generation, and wholesale price. No imputation or cleaning was required.

---

## 2. Summary Statistics

| Metric | Mean | Std Dev | Min | 25th | Median | 75th | Max |
|---|---|---|---|---|---|---|---|
| Demand (MW) | 1,062.30 | 156.78 | 587.74 | 952.35 | 1,041.88 | 1,157.37 | 1,743.57 |
| Renewable Gen (MW) | 1,050.60 | 288.24 | 451.88 | 824.66 | 1,025.36 | 1,227.81 | 2,089.22 |
| Price ($/MWh) | 94.28 | 186.58 | -54.53 | 46.25 | 90.93 | 120.70 | 11,873.37 |

**Key observations:**

- **Demand** is relatively stable, centred around 1,062 MW with moderate variation (std dev ~15% of mean). The distribution is approximately normal with a slight right skew, reflecting occasional winter peaks.
- **Renewable generation** averages 1,051 MW — nearly equal to demand — but is far more volatile (std dev ~27% of mean). The wider spread reflects Tasmania's dependence on variable hydro and wind output.The dataset also contains several high renewable generation outliers, representing periods when renewable output significantly exceeded normal levels and, in some cases, local electricity demand. During these periods, the combination of high renewable generation and relatively low demand can contribute to oversupply in the market, which may result in negative wholesale electricity prices.
- **Price** has a median of $90.93/MWh, but extreme spikes increase the mean to $94.28/MWh and the maximum to $11,873.37/MWh. The distribution is heavily right-skewed, with most hourly prices below $121/MWh. These high price spikes are clear outliers; however, they represent real electricity market events rather than errors in the data. They are likely caused by periods of high demand, limited electricity supply, or transmission constraints, and have been retained for further analysis and model development.

---

## 3. Demand Trends

### 3.1 Demand Over Time

Demand follows a clear **seasonal cycle**, peaking during the Australian winter months (June-August) and falling to its lowest during summer (December-February). This is consistent with increased heating load in cooler months. The pattern repeats consistently across both years in the dataset.

### 3.2 Average Demand by Month

| Month | Avg Demand (MW) |
|---|---|
| July (peak) | 1,260.92 |
| June | 1,192.75 |
| August | 1,171.59 |
| February (trough) | 948.10 |
| December | 947.37 |

Peak winter demand (July, 1,261 MW) is roughly **33% higher** than the summer low (December, 947 MW), highlighting the strong seasonal heating effect in Tasmania.

### 3.3 Average Demand by Hour of Day

The daily demand profile shows a **twin-peak pattern**:

- **Morning peak** at 08:00 (~1,207 MW) driven by residential and commercial activity starting the day.
- **Evening peak** at 21:00 (~1,156 MW) corresponding to household heating and lighting in the evening.
- **Overnight trough** at 03:00–04:00 (~975 MW) when most activity is minimal.

The morning peak slightly exceeds the evening peak, suggesting commercial and industrial loads contribute significantly.

### 3.4 Weekday vs Weekend Demand

| Day Type | Avg Demand (MW) |
|---|---|
| Weekday | 1,067.63 |
| Weekend | 1,048.92 |

Weekday demand is only ~1.8% higher than weekend demand. This small difference indicates that Tasmania's demand is primarily driven by residential heating and base industrial load rather than commercial office activity.

---

## 4. Renewable Generation

### 4.1 Renewable Generation Over Time


Renewable output fluctuates significantly between ~450 MW and ~2,089 MW. The variation is driven by hydro inflows and wind conditions, both of which are weather-dependent. There is no strong upward or downward trend, suggesting installed renewable capacity has remained relatively stable over the period.

### 4.2 Renewable Generation Distribution


The distribution is **bimodal**, with clusters around 700–800 MW and 1,000–1,100 MW. This suggests two distinct operating regimes — lower output during dry or calm periods, and higher output when hydro and wind conditions are favourable.

### 4.3 Renewable Coverage


| Statistic | Renewable Coverage (%) |
|---|---|
| Mean | 99.60% |
| Median | 102.76% |
| Min | 41.61% |
| Max | 185.41% |

On average, Tasmania's renewable generation covers **virtually 100% of its demand**. The median exceeds 100%, meaning that in more than half of all hours, renewables produce more electricity than Tasmania consumes — with the surplus exported via the Basslink interconnector to mainland Australia.

Coverage drops to a minimum of ~42% during periods of low hydro/wind, indicating that import capacity remains essential for grid reliability.

---

## 5. Wholesale Electricity Price

### 5.1 Price Over Time


Prices are generally stable below $200/MWh, but the time series reveals **occasional extreme spikes** exceeding $2,000/MWh. The most prominent events occurred around:

- **August 2024** — spike to ~$11,873/MWh
- **June–July 2025** — spike to ~$11,000/MWh
- **January 2026** — spike to ~$2,000/MWh

These events are likely driven by supply shortfalls (low renewable output coinciding with high demand), interconnector constraints, or market bidding behaviour. The presence of **negative prices** (min: -$54.53/MWh) indicates occasional oversupply, when generators pay to remain dispatched.So the market doesn't intentionally set negative prices to keep generators running; rather, the bidding process can result in negative prices under those conditions.

---

## 6. Correlations



| Variable Pair | Correlation |
|---|---|
| Demand — Renewable Gen | 0.37 |
| Demand — Price | 0.20 |
| Renewable Gen — Price | 0.09 |

- **Demand and renewables** have a moderate positive correlation (0.37). Both tend to be higher during winter, creating alignment between supply and demand peaks — a favourable characteristic for grid stability.
- **Demand and price** are weakly correlated (0.20). While higher demand generally pushes prices up, the relationship is dominated by supply-side factors (generation availability, interconnector flows).For example, periods of high demand may still experience relatively stable prices if there is sufficient renewable generation available to meet the increased electricity demand.
- **Renewables and price** are nearly uncorrelated (0.09). This suggests that renewable output alone does not significantly suppress prices in Tasmania, likely because hydro generation can be strategically dispatched to capture higher-price periods.

---

## 7. Key Takeaways

1. **Data quality is excellent** — no missing values, no duplicates, and a complete 2-year hourly record suitable for time-series modelling.
2. **Strong seasonality** in demand (winter peaks ~33% above summer troughs) provides a clear signal for forecasting models.
3. **Dual daily peaks** (morning and evening) should be captured by hourly features in any demand forecasting model.
4. **Renewable coverage averages ~100%**, making Tasmania one of the most renewable-heavy grids globally. However, the wide range (42%–185%) means supply variability is a key risk factor.
5. **Price spikes are rare but extreme** (max ~$11,873/MWh), heavily skewing the distribution. Forecasting models should consider log-transforming price or treating spike events separately.
6. **Weak correlation between renewables and price** suggests that hydro dispatch strategy and interconnector dynamics are more important price drivers than raw renewable output.

---

*Report generated from the Tasmania Grid Intelligence Forecasting Platform EDA pipeline.*

