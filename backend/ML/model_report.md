# Random Forest Demand Forecasting Report

---

## 1. Objective

The objective of this modelling exercise is to forecast Tasmania's next-hour electricity demand using a supervised machine learning model trained on historical operational data. The model ingests engineered temporal features derived from historical demand, renewable generation, and electricity price signals to produce a one-step-ahead prediction of grid demand expressed in megawatts (MW). Accurate short-horizon demand forecasting is operationally critical for grid management: it informs dispatch decisions, reserve scheduling, and the balancing of intermittent renewable generation against instantaneous load.

---

## 2. Training Dataset

The model was trained on the feature-engineered dataset `feature_dataset.csv`, which comprises **17,341 observations** and **26 columns** in total. Of these columns, **17 were selected as input features** for the model, with the remaining columns serving as identifiers, raw measurements, or alternative targets. The dataset contains no missing values across any of the 26 columns, eliminating the need for imputation and ensuring that all observations contribute fully to model training.

The target variable is `target_demand_next_hour`, representing the mean electricity demand (MW) in the hour immediately following each observation. This formulation is consistent with a one-step-ahead forecasting task where the model must generalise from known historical conditions to an unseen future interval.

A **chronological 80/20 train-test split** was applied rather than a random partition. The training set comprises **13,872 observations**, spanning the period from 5 July 2024 to 3 February 2026. The test set comprises **3,469 observations**, covering the period from 3 February 2026 to 28 June 2026. This chronological separation is a deliberate and necessary design choice for time-series forecasting. Random splitting would allow future observations to appear in the training set, creating data leakage whereby the model implicitly learns from information that would not yet be available at the time of prediction. Chronological splitting enforces temporal causality: the model is trained exclusively on data that precedes the test period, ensuring that evaluation accurately reflects the model's ability to generalise to unseen future conditions — the precise scenario encountered in operational deployment.

---

## 3. Model Selection

A **Decision Tree** is a supervised learning algorithm that partitions the feature space through a series of binary splits, each chosen to minimise prediction error within the resulting subsets. At each internal node, the algorithm selects the feature and threshold that most effectively separates the training samples, recursively subdividing until a stopping criterion is reached. The resulting structure resembles a flowchart of conditional rules, which makes individual trees interpretable and fast to train. However, single Decision Trees are prone to **overfitting**: when grown without restriction, a tree can memorise the training data — including its noise — achieving near-perfect training accuracy while failing to generalise to unseen examples. This high variance is a fundamental weakness of the single-tree approach.

**Random Forest** addresses this limitation through an ensemble strategy known as *bagging* (bootstrap aggregating). Rather than training a single tree on the full dataset, Random Forest constructs a large number of independent Decision Trees, each trained on a different bootstrap sample of the training data — a random subset drawn with replacement. Furthermore, at each split within each tree, only a random subset of the available features is considered as candidates for the splitting criterion. This dual source of randomness decorrelates the individual trees, ensuring that their errors are not systematically shared. The final prediction is produced by averaging the numerical outputs of all trees in the ensemble. Averaging across many independent but individually noisy predictors substantially reduces variance without proportionally increasing bias, yielding a model that is substantially more robust and better calibrated than any single constituent tree.

Random Forest was selected as the baseline model for this project because it is well-suited to tabular data with mixed feature types, requires minimal hyperparameter tuning to produce strong results, is naturally resistant to overfitting, and provides an interpretable measure of feature importance as a by-product of training. These properties make it an appropriate and well-established choice for an initial demand forecasting baseline.

---

## 4. Model Performance

The trained model was evaluated on the held-out test set using three standard regression metrics: Mean Absolute Error (MAE), Root Mean Squared Error (RMSE), and the coefficient of determination (R²).

**Mean Absolute Error (MAE): 35.30 MW**

MAE measures the average magnitude of prediction errors without regard to their direction, expressed in the same unit as the target variable. It is the arithmetic mean of the absolute differences between each predicted value and the corresponding actual value. An MAE of 35.30 MW indicates that, on average, the model's next-hour demand prediction deviates from the true demand by approximately 35.30 MW. Examining the first ten test-period predictions, where actual demand ranges from approximately 796 MW to 988 MW, this error magnitude corresponds to a relative error broadly in the range of 3–5% across typical observations during the summer test period. This level of accuracy is operationally meaningful: demand forecasts within this margin can support credible dispatch and reserve decisions without requiring excessive precautionary margins.

**Root Mean Squared Error (RMSE): 47.43 MW**

RMSE is the square root of the mean of squared prediction errors. By squaring the errors before averaging, RMSE disproportionately penalises large deviations, making it sensitive to outliers and occasional large prediction failures. An RMSE of 47.43 MW, which is notably higher than the MAE of 35.30 MW, confirms that the error distribution is not uniform: while the typical error is approximately 35 MW, there are occasional larger deviations that inflate the RMSE beyond the MAE. This divergence is consistent with the known behaviour of ensemble averaging models, which tend to underestimate extreme peaks and troughs by averaging across constituent trees — a characteristic discussed further in Section 6. The gap between MAE and RMSE (approximately 12 MW) is moderate and suggests that large errors, though present, are not excessively frequent.

**Coefficient of Determination (R²): 0.8943**

R² measures the proportion of variance in the target variable that is explained by the model. A value of 1.0 would indicate perfect prediction, while a value of 0.0 would indicate that the model performs no better than predicting the mean of the target at every time step. An R² of 0.8943 indicates that the Random Forest model explains approximately **89.4% of the variance** in next-hour electricity demand across the test period. This is a strong result for a baseline model trained without weather data or external calendar information, and it demonstrates that the temporal and lag-based features constructed during the feature engineering phase carry substantial predictive information. The remaining 10.6% of unexplained variance likely arises from demand drivers not captured by the current feature set, including temperature conditions, wind and solar resource variability, public holidays, and unexpected operational events.

Taken together, the three metrics indicate that the Random Forest model delivers accurate and reliable next-hour demand forecasts and constitutes a strong baseline from which to benchmark more sophisticated modelling approaches.

---

## 5. Feature Importance


The feature importance values derived from the trained Random Forest reveal a clear hierarchy of predictive relevance among the 17 input features, and this hierarchy is strongly consistent with the temporal structure of electricity demand.

**`demand_lag_24`** is by far the dominant predictor, with an importance score of 0.5576, accounting for more than **55% of the model's total predictive power**. This feature represents the demand recorded exactly 24 hours prior to the forecast interval. Its dominance reflects the profound daily periodicity of electricity consumption: households and businesses follow broadly similar schedules from one day to the next, meaning that what the grid demanded at a given hour yesterday is the single most informative signal for what it will demand at the same hour today. This finding directly corroborates the strong autocorrelation at a 24-hour lag that was identified during the exploratory data analysis (EDA), where the demand time series exhibited clear and persistent diurnal cycles.

**`demand_lag_1`** is the second most important feature, with an importance score of 0.1932, contributing approximately **19.3%** of predictive power. This feature captures the demand in the immediately preceding hour. Its importance reflects the strong short-term inertia in electricity consumption: demand does not jump discontinuously between consecutive hours, and knowing the current level of demand provides a strong prior for the next hour. The combined dominance of `demand_lag_24` and `demand_lag_1` — accounting for over 75% of total feature importance between them — confirms that electricity demand is fundamentally a lag-driven process at sub-daily timescales.

**`hour`** is the third most important feature, contributing an importance score of 0.1215, approximately **12.1%** of total predictive power. The hour of day encodes the systematic intra-day demand cycle directly: morning ramp-up, midday plateau, evening peak, and overnight trough are stable structural patterns that the model learns through this single feature. The prominence of `hour` further reinforces the EDA finding that hourly demand cycles are among the most robust and consistent patterns in the Tasmanian grid data.

The remaining features — including `demand_rolling_24`, `demand_lag_168`, and the various renewable generation and electricity price lags — each contribute less than 5% individually. The 24-hour rolling mean of demand (`demand_rolling_24`, 4.30%) provides a smoothed baseline that captures recent trends beyond the single 24-hour lag. The weekly lag `demand_lag_168` (1.75%) captures day-of-week structure, reflecting the fact that, for example, Monday demand tends to resemble the preceding Monday.

The renewable generation and electricity price features collectively contribute less than 7% of total importance across all their lag and rolling variants. This limited contribution is consistent with the weak correlations between renewable generation, electricity price, and contemporaneous demand that were identified during EDA. While renewable generation and price are clearly related to supply-side dynamics, they are not strong independent drivers of demand, and their lag features do not substantially improve predictions beyond what is already captured by historical demand signals alone.

The negligible importance of `is_weekend` (0.0446%) is somewhat surprising but can be understood in the context of the other features already present: `day_of_week` and `hour` together already capture the weekend demand pattern implicitly, leaving little residual information for `is_weekend` to contribute uniquely.

---

## 6. Prediction Performance

### Full Test Set



The full test-set comparison spans the period from 3 February 2026 to 28 June 2026 — approximately five months of unseen future data covering the transition from the Tasmanian summer through to the onset of winter. Across this extended horizon, the model tracks the actual demand trajectory with considerable fidelity. The predicted series follows the overall level and trend of actual demand, correctly identifying periods of elevated and suppressed demand without systematic drift or divergence over time. This sustained accuracy over a five-month test window demonstrates that the model generalises well to future, unseen conditions rather than merely interpolating within the training period.

The model accurately captures the recurring daily demand cycles, reproducing the characteristic oscillations associated with morning ramp-up and evening peaks with correct timing and approximate magnitude. The structural regularity of these cycles — encoded in the model through `demand_lag_24` and `hour` — is clearly learned and reproduced faithfully across diverse ambient conditions throughout the test period.

However, a consistent characteristic of the predictions is the slight **smoothing of extreme values**: the highest demand peaks and the lowest overnight troughs tend to be modestly underestimated and overestimated, respectively. This behaviour is an inherent property of the Random Forest ensemble mechanism. Because the final prediction is the average of 100 individual tree predictions, each trained on a different bootstrap sample, the ensemble tends to produce predictions that converge toward the central tendency of the training distribution. Unusual or extreme demand events — which by definition are rare in the training data — are therefore assigned a prediction that partially reverts toward more typical values, producing the smoothing effect observed in the figures. This is not a failure of the model per se, but rather a fundamental trade-off of ensemble averaging: reduced variance at the cost of reduced sensitivity to extremes.

### First Week of Test Set



Examining only the first 168 hours (one week) of the test period provides a higher-resolution view of the model's predictive behaviour at the scale of individual demand cycles. At this resolution, the model's accurate reproduction of the daily demand pattern becomes clearly visible: the predicted series rises and falls in close alignment with the actual series across each 24-hour cycle, with the timing of morning increases and evening declines closely matched. The first 10 test-period predictions, reproduced in the training log, are illustrative: actual demand on the afternoon of 3 February 2026 rises from approximately 796 MW at 14:00 to a peak of approximately 988 MW at 19:00, and the model's predictions track this trajectory closely, with individual errors predominantly in the range of 25–45 MW.

The week-level view also confirms that the smoothing of extremes noted for the full test set is already present in the first week: the model's predicted peak at the 18:00–20:00 evening window is slightly lower than the actual peak, and the overnight trough is slightly elevated relative to the actual minimum. This pattern is consistent and expected given the ensemble averaging mechanism discussed above.

---

## 7. Relationship to Exploratory Data Analysis

The Random Forest model's learned behaviour closely reflects the structural patterns that were identified during the exploratory data analysis phase of this project. The EDA established several key empirical observations about the Tasmanian electricity demand time series, and the modelling results confirm that these patterns are not only statistically present in the data but sufficiently stable and consistent to be exploited for accurate forecasting.

The **strong daily demand cycle** identified during EDA — characterised by elevated demand during morning and evening periods and suppressed demand overnight — is directly captured by the model through the dominance of `demand_lag_24` and the significant contribution of `hour`. These two features collectively encode the diurnal rhythm of electricity consumption, and their combined importance of approximately 68% of total predictive power is a quantitative reflection of how fundamental this daily cycle is to the forecasting task.

The EDA also identified **seasonal variation** in demand, with higher demand observed during winter months consistent with Tasmania's predominantly heating-driven electricity consumption. The model's ability to sustain accurate predictions across the February-to-June test period — capturing the transition from summer to autumn and the beginning of the winter uplift — suggests that the seasonal signal is at least partially encoded through the `month`, `day`, and weekly lag features, even if their individual importance scores are modest. The persistence of predictive accuracy over this seasonal transition is encouraging for operational deployment.

The **similarity between contemporaneous demand and the demand from the preceding 24 hours** was one of the most prominent findings of the EDA, reflected in the strong 24-hour autocorrelation of the demand series. The overwhelming dominance of `demand_lag_24` as the single most important feature is the model's operationalisation of this relationship: the algorithm has independently discovered and heavily weighted the same lag structure that manual autocorrelation analysis revealed.

The **limited predictive contribution of renewable generation and electricity price**, reflected in the low feature importance scores assigned to all renewable and price lag features, is consistent with the weak correlations between these variables and contemporaneous demand identified during EDA. Renewable generation in Tasmania is primarily hydroelectric, which is dispatchable and responds to demand rather than driving it. Electricity price, while correlated with demand at a macro level, exhibits considerable noise at the hourly timescale driven by market dynamics unrelated to underlying consumption patterns. The EDA finding that neither variable was a strong linear predictor of demand is confirmed by the Random Forest's assignment of less than 7% collective importance to these feature groups.

Feature engineering played a critical intermediary role in translating the qualitative patterns observed during EDA into quantitative inputs that the model can exploit. The transformation of raw demand, renewable, and price time series into lag features and rolling averages — informed directly by the autocorrelation structures revealed in EDA — is what enables the Random Forest to learn the temporal relationships that underpin accurate forecasting.

---

## 8. Model Limitations

Despite its strong baseline performance, the Random Forest model is subject to several limitations that should be acknowledged when interpreting its predictions in an operational context.

The model's reliance on historical demand patterns means that it is inherently **dependent on the stability of those patterns**. During periods when electricity consumption deviates significantly from its historical norms — such as during extreme weather events, public holidays, major industrial disruptions, or significant changes in the composition of connected load — the model's predictions may be less accurate. Because Random Forest cannot extrapolate beyond the range of values seen in training, demand levels that are genuinely novel will be assigned predictions that revert toward more typical historical values, potentially understating the magnitude of unusual events.

The absence of **weather data** is a notable limitation for a Tasmanian demand forecasting application. Tasmania's electricity consumption is strongly influenced by ambient temperature, particularly through residential and commercial heating and cooling loads. Temperature and its interaction with the time of day and season are among the most powerful drivers of demand variability that cannot be fully captured by historical demand lags alone. Incorporating temperature forecasts or observations into the feature set would likely reduce both MAE and RMSE and improve the model's ability to anticipate demand spikes associated with cold snaps or heatwaves.

The current feature set contains **no public holiday information**. Public holidays significantly alter the temporal pattern of electricity consumption: the diurnal demand profile on a public holiday more closely resembles a Sunday than a weekday, and the `day_of_week` feature alone cannot distinguish a public holiday Monday from a regular Monday. This limitation will produce systematic prediction errors on public holidays where historical demand lags reflect the preceding weekday pattern.

There is no representation of **Basslink operational status** or unexpected generator outages. The Basslink interconnector, which links Tasmania's electricity grid to the mainland National Electricity Market, has a material influence on effective demand as seen by Tasmanian generators. Changes in interconnector flows due to operational events, congestion, or planned maintenance can alter the relationship between the measured features and the target variable in ways that the current model cannot anticipate.

Finally, the model provides a **point prediction** without a probabilistic confidence interval. For grid operations, understanding the uncertainty around a forecast is as important as the forecast itself. An ensemble approach such as Random Forest can produce prediction intervals through the distribution of individual tree predictions, but this output is not currently extracted or reported.

---

## 9. Conclusion

The Random Forest Regressor trained in this study demonstrates strong baseline performance on the task of one-hour-ahead electricity demand forecasting for the Tasmanian grid. An R² of 0.8943 — indicating that the model explains approximately 89.4% of the variance in next-hour demand across an unseen five-month test period — represents a meaningful and deployable level of accuracy for a model trained on temporal and lag-based features alone. The MAE of 35.30 MW and RMSE of 47.43 MW confirm that typical prediction errors are moderate in magnitude and that the model generalises reliably to future conditions beyond the training period.

The analysis of feature importance establishes that the model's predictive power is predominantly derived from the 24-hour demand lag and, to a lesser extent, the one-hour demand lag and the hour of day. This finding directly corroborates the patterns identified during exploratory data analysis and validates the feature engineering decisions that translated those observations into the model's input representation. Feature engineering was not merely a preprocessing step but a critical determinant of model performance: without the lag and rolling features constructed from the raw time series, the model would lack access to the temporal structure that constitutes the majority of its predictive signal.

The model's tendency to smooth extreme demand values is an expected property of ensemble averaging and represents the principal source of residual prediction error. This smoothing effect is particularly relevant for operational planning scenarios requiring accurate peak demand estimation, and it motivates the inclusion of probabilistic prediction capabilities in future modelling iterations.

Several directions present themselves for future development. Gradient Boosting frameworks — including XGBoost and LightGBM — are known to achieve superior performance relative to Random Forest on many tabular regression tasks through sequential tree construction that directly targets residual errors, and they should be evaluated as next-step alternatives. The incorporation of weather variables, particularly temperature forecasts, would address the single most significant gap in the current feature set. The addition of a public holiday indicator and a binary variable encoding Basslink operational status would reduce systematic errors during atypical operating periods. Together, these enhancements would build upon the strong foundation established by this baseline model and move the platform progressively toward production-grade forecasting accuracy.
