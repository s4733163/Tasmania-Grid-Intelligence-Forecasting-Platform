# Renewable Generation Forecasting Report

---

## 1. Objective

The objective of this modelling exercise is to forecast Tasmania's next-hour renewable electricity generation using a supervised machine learning model trained on historical operational data. The model ingests engineered temporal features derived from historical renewable generation, electricity demand, and electricity price signals to produce a one-step-ahead prediction of renewable output expressed in megawatts (MW). Accurate short-horizon renewable generation forecasting is operationally significant for grid management: it informs dispatch decisions, determines how much thermal or import capacity must be held in reserve, and supports the balancing of variable generation against instantaneous load. Two candidate models are evaluated in this report — a Random Forest Regressor and a Gradient Boosting Regressor — with the aim of identifying the most appropriate baseline for the Tasmania Grid Intelligence and Forecasting Platform.

---

## 2. Dataset

Both models were trained and evaluated on the same feature-engineered dataset, `feature_dataset.csv`, which comprises **17,341 observations** and **26 columns** in total. Of these, **17 columns were selected as input features**, with the remaining columns serving as identifiers, raw measurements, or alternative forecast targets. The dataset is complete, containing no missing values across any column, which ensures that every observation contributes fully to model training and evaluation without the need for imputation.

The target variable for both models is `target_renewable_next_hour`, representing the mean renewable electricity generation (MW) in the hour immediately following each observation. This formulation is consistent with a one-step-ahead forecasting task in which the model must infer future renewable output from historical conditions available at the time of prediction.

A **chronological 80/20 train-test split** was applied to both models. The training set comprises **13,872 observations**, spanning the period from 5 July 2024 to 3 February 2026. The held-out test set comprises **3,469 observations**, covering the period from 3 February 2026 to 28 June 2026. Chronological partitioning was chosen deliberately over random splitting because electricity generation is a time-ordered process: randomly assigning observations to training and test sets would allow future data points to appear in the training set, creating data leakage in which the model implicitly accesses information that would not yet be available at the time of a real-world prediction. Chronological splitting enforces temporal causality and ensures that the evaluation reflects the model's ability to generalise to genuinely unseen future conditions — the scenario encountered in operational deployment.

---

## 3. Random Forest Regressor

### 3.1 Model Overview

A **Decision Tree** is a supervised learning algorithm that partitions the input feature space through a sequence of binary decisions, each chosen to minimise prediction error in the resulting subsets. While interpretable and fast to train, a single Decision Tree is prone to overfitting: without restriction, it will memorise the training data — including its noise — yielding high training accuracy but poor generalisation to unseen examples.

**Random Forest** addresses this limitation by constructing an ensemble of many independent Decision Trees, each trained on a different bootstrap sample of the training data. At every split within each tree, only a randomly selected subset of features is evaluated as candidates for the splitting rule. This dual randomisation — over observations and features — decorrelates the individual trees, preventing their errors from being systematically aligned. The final prediction is the average of the numerical outputs across all trees in the ensemble. Averaging across many independent but imperfect estimators substantially reduces prediction variance without proportionally increasing bias, producing a model that is considerably more robust than any single constituent tree.

Random Forest is well-suited to this forecasting problem because it handles tabular data with mixed feature types effectively, requires minimal hyperparameter tuning to produce competitive results, is naturally resistant to overfitting, and provides an interpretable measure of feature importance as a direct by-product of the training process.

### 3.2 Model Performance

The trained Random Forest model was evaluated on the held-out test set using three standard regression metrics.

**Mean Absolute Error (MAE): 66.14 MW**

MAE measures the average magnitude of prediction errors, expressed in the same unit as the target variable. It represents the arithmetic mean of the absolute differences between each predicted value and the corresponding actual value, treating all errors equally regardless of their size. An MAE of 66.14 MW indicates that the Random Forest model's next-hour renewable generation predictions deviate from the true values by approximately 66 MW on average. Examining the first ten test-period observations, where actual renewable generation ranges from approximately 869 MW to 1,003 MW, this error magnitude corresponds to relative errors broadly in the range of 6–8% for typical observations during the summer test period. While operationally useful as a general directional guide, this level of absolute error reflects the inherent difficulty of forecasting a generation source that responds to environmental and operational conditions not represented in the current feature set.

**Root Mean Squared Error (RMSE): 92.85 MW**

RMSE is the square root of the mean of squared prediction errors. By squaring individual errors before averaging, RMSE assigns disproportionately higher weight to large deviations, making it more sensitive to occasional extreme prediction failures than MAE. An RMSE of 92.85 MW is notably higher than the MAE of 66.14 MW, indicating that the error distribution is skewed: while the median error is substantially lower than the MAE, there are recurring large prediction errors — likely associated with sudden changes in renewable output that fall outside the range of patterns represented in historical lag features — that inflate the RMSE considerably above the MAE. The gap between the two metrics (approximately 27 MW) is substantially wider than the analogous gap observed in the demand forecasting model, which is consistent with the greater inherent variability and unpredictability of renewable generation.

**Coefficient of Determination (R²): 0.7410**

R² measures the proportion of variance in the target variable that is explained by the model. A value of 0.7410 indicates that the Random Forest explains approximately **74.1% of the variance** in next-hour renewable generation across the test period. While this constitutes a meaningful degree of predictive accuracy, it is notably lower than the R² of 0.8943 achieved by the demand forecasting model trained on the same dataset. This divergence is consistent with the expectation that renewable generation is fundamentally more difficult to predict than electricity demand using only historical operational features: demand is driven predominantly by stable behavioural and temporal patterns, whereas renewable generation responds to environmental and operational factors — hydro inflows, reservoir levels, dispatch decisions, and wind availability — that are not captured by the current feature set. The remaining 25.9% of unexplained variance represents the predictive headroom that additional features such as weather variables and operational data could potentially recover.

### 3.3 Feature Importance

The feature importance values derived from the Random Forest reveal a clear and interpretable hierarchy of predictive relevance. **`renewable_lag_1`** is the dominant predictor, with an importance score of 0.5863, accounting for approximately **58.6% of total predictive power**. This overwhelming dominance reflects the strong short-term inertia of renewable generation: the output recorded in the immediately preceding hour is by far the most informative signal for predicting the next hour's output. This is consistent with the gradual ramping behaviour of hydroelectric generation, which cannot change instantaneously, and with the persistence of weather patterns that sustain similar renewable output across consecutive hours.

**`hour`** is the second most important feature, contributing an importance score of 0.1073, approximately **10.7% of total predictive power**. The hour of day encodes systematic intra-day patterns in renewable generation — including daily variations in run-of-river hydro inflows and, to a lesser extent, any solar component — that the model exploits to improve prediction accuracy beyond what is provided by the immediate lag alone.

The remaining features, including `renewable_lag_24` (5.46%), `renewable_rolling_24` (3.84%), and various demand, price, and calendar variables, each contribute less than 5% individually. Their collective contribution is meaningful but modest, suggesting that the overwhelming majority of predictable signal in next-hour renewable generation is captured by the very recent generation history and the time of day. Demand and price lag features contribute marginally, reflecting the fact that while renewable generation and demand are related at a macro level, their short-horizon interaction is insufficiently structured to provide strong incremental predictive value.

### 3.4 Prediction Performance

Across the full five-month test period from February to June 2026, the Random Forest model broadly tracks the trajectory of actual renewable generation. The predicted series follows the overall level and seasonal variation of renewable output without systematic upward or downward drift, demonstrating that the model generalises to future conditions beyond the training window. The model correctly identifies the general temporal structure of renewable output and reproduces approximate diurnal cycles.

However, the prediction errors are visibly larger and less consistent than those observed in the corresponding demand forecasting model. Sudden increases or decreases in renewable generation — which may reflect changes in hydro dispatch, rainfall-driven changes in run-of-river availability, or other operational events — are not fully anticipated by the model. The predicted series exhibits the characteristic smoothing behaviour associated with ensemble averaging: extreme peaks and troughs in actual renewable output are underestimated and overestimated, respectively, as the prediction reverts toward the historical distribution of outputs seen in training. This smoothing effect is more pronounced for renewable generation than for demand, reflecting the greater frequency and magnitude of abrupt changes in renewable output.

Examining only the first 168 hours of the test period provides a higher-resolution view of the model's predictive behaviour at the scale of individual daily cycles. At this resolution, the model's tracking of the diurnal renewable generation pattern is clearly visible, and the general trajectory of actual output is followed closely across the first several days. The first ten test-period predictions illustrate representative model behaviour: actual renewable output on the afternoon of 3 February 2026 ranges from approximately 869 MW to 1,003 MW across the first ten hours, and the model's predictions track this range with errors that, while larger than those observed in the demand model, are broadly proportional to the increased variability of the target variable. The week-level view also confirms that the smoothing of extremes noted at the full-test-set scale is already apparent within the first 168 hours.

---

## 4. Gradient Boosting Regressor

### 4.1 Model Overview

**Gradient Boosting** is a sequential ensemble learning method that constructs a series of weak learners — typically shallow Decision Trees — where each successive tree is trained to correct the residual errors left by the combination of all preceding trees. Unlike Random Forest, which builds its constituent trees independently in parallel and averages their outputs, Gradient Boosting trains each new tree in a directed manner by fitting it to the negative gradient of a loss function computed on the current ensemble's residuals. This iterative correction mechanism allows Gradient Boosting to progressively reduce both bias and variance across training iterations, often achieving superior accuracy on structured tabular data compared with Random Forest, particularly when there is residual predictive structure in the errors that a single round of tree-building fails to capture.

The key distinction from Random Forest is the dependence between successive trees: each tree is informed by the failures of all preceding trees, creating a targeted correction process rather than the independent averaging that characterises Random Forest. This makes Gradient Boosting potentially more expressive on complex datasets but also more sensitive to overfitting and hyperparameter choices. In this study, the Gradient Boosting model was evaluated using default hyperparameter settings as a direct comparison to the Random Forest baseline, without hyperparameter optimisation.

### 4.2 Model Performance

**Mean Absolute Error (MAE): 67.22 MW**

An MAE of 67.22 MW indicates that the Gradient Boosting model's average prediction error is approximately 67 MW per hour. This value is marginally higher than the Random Forest MAE of 66.14 MW — a difference of 1.08 MW, equivalent to approximately 1.6% of the Random Forest MAE. The Gradient Boosting model therefore produces slightly larger typical prediction errors than Random Forest under the current default configuration, suggesting that the sequential correction mechanism of Gradient Boosting does not provide a consistent advantage over Random Forest for the median prediction case on this dataset.

**Root Mean Squared Error (RMSE): 91.72 MW**

An RMSE of 91.72 MW represents a modest improvement over the Random Forest RMSE of 92.85 MW — a reduction of 1.13 MW, or approximately 1.2%. The lower RMSE indicates that Gradient Boosting produces slightly fewer or smaller large prediction errors compared with Random Forest. Since RMSE is more sensitive than MAE to outlier errors, this marginal improvement suggests that the sequential residual correction in Gradient Boosting provides a small but measurable benefit in reducing the magnitude of the most extreme prediction failures, even as the typical error (measured by MAE) is marginally worse.

**Coefficient of Determination (R²): 0.7473**

An R² of 0.7473 indicates that the Gradient Boosting model explains approximately **74.7% of the variance** in next-hour renewable generation across the test period. This represents a marginal improvement of 0.0063 over the Random Forest R² of 0.7410. While Gradient Boosting explains a slightly higher proportion of the variance in renewable output, the practical significance of this improvement is limited: the two models are statistically very close in their overall explanatory power, and both fall substantially short of the R² achieved by the demand forecasting model (0.8943), reinforcing that renewable generation is inherently more difficult to forecast under the current feature set regardless of which ensemble method is employed.

### 4.3 Feature Importance

The Gradient Boosting model assigns an even greater concentration of predictive importance to **`renewable_lag_1`** than the Random Forest, with an importance score of 0.6556 — approximately **65.6% of total predictive power**. This represents an increase of approximately seven percentage points relative to the Random Forest's assignment of 58.6% to the same feature, indicating that the sequential correction mechanism of Gradient Boosting has concentrated its predictive reliance on the most immediately informative signal even more heavily than the bagging approach of Random Forest.

**`hour`** remains the second most important feature, with an importance score of 0.1539, representing approximately **15.4% of total predictive power** — an increase from the 10.7% assigned by Random Forest. Together, `renewable_lag_1` and `hour` account for over 80% of the Gradient Boosting model's total importance, compared with approximately 69% for the same two features in the Random Forest. This greater concentration of importance on the top two features in the Gradient Boosting model suggests that the sequential learning process identified these two features as sufficient to capture the bulk of predictable signal, leaving comparatively little residual structure for the remaining 15 features to explain.

The remaining features — including `renewable_lag_24` (3.96%), `renewable_rolling_24` (3.71%), and various demand and price lags — contribute less than 2% each, and the contributions are generally smaller for Gradient Boosting than for Random Forest. The near-zero importance of `is_weekend` (0.00001) further confirms that weekday versus weekend distinctions carry no meaningful information for renewable generation forecasting under the current feature set.

### 4.4 Prediction Performance

Across the full five-month test period, the Gradient Boosting model's predicted series closely resembles the Random Forest output in its overall character: both models track the general level and seasonal trajectory of actual renewable generation without systematic drift, and both exhibit smoothing of extreme values. The marginal improvement in RMSE observed in the quantitative metrics is not dramatically apparent from visual inspection of the full test-set figure; the two models produce broadly similar prediction traces at this scale, and their shared inability to anticipate abrupt changes in renewable output is clearly visible in both.

At the weekly resolution, the Gradient Boosting model again closely tracks the diurnal and short-term patterns in renewable generation with similar fidelity to the Random Forest. The first ten test-period predictions for the Gradient Boosting model show somewhat larger absolute deviations from actual values compared with the Random Forest in the early hours of the test period — consistent with the marginally higher MAE — before converging toward similar accuracy over subsequent hours. The smoothing of extreme values is present in the Gradient Boosting predictions as it is in the Random Forest, and the model's general trajectory closely follows the actual series across the first week of the test period.

---

## 5. Model Comparison

The two models are compared directly in the following table using the exact metrics reported in the training logs.

| Metric | Random Forest | Gradient Boosting | Difference |
|:---|:---:|:---:|:---:|
| MAE (MW) | 66.14 | 67.22 | +1.08 (GB worse) |
| RMSE (MW) | 92.85 | 91.72 | −1.13 (GB better) |
| R² | 0.7410 | 0.7473 | +0.0063 (GB better) |

The experimental results reveal that neither model is unambiguously superior across all three metrics. Random Forest achieves a lower MAE, indicating smaller typical prediction errors. Gradient Boosting achieves a lower RMSE and a higher R², indicating a marginal reduction in large prediction errors and a slightly higher proportion of explained variance. All three differences are small in absolute terms: the MAE gap is 1.08 MW (approximately 1.6%), the RMSE gap is 1.13 MW (approximately 1.2%), and the R² gap is 0.0063 (less than one percentage point). The overall predictive performance of the two models is therefore very similar under the default hyperparameter configurations used in this study.

The modest nature of the Gradient Boosting improvement is consistent with the structure of the forecasting problem. The dominant predictive feature — `renewable_lag_1` — accounts for the majority of explainable variance in both models, leaving limited residual structure for the sequential correction mechanism of Gradient Boosting to exploit. When a single feature carries approximately 60–66% of predictive importance, the incremental benefit of a more sophisticated ensemble method is inherently bounded: both models have already captured the same primary signal, and the remaining features contain insufficient structure to create meaningful separation between approaches. Gradient Boosting's advantage would likely be more pronounced if the feature set were richer, or if hyperparameter optimisation were applied to allow the model to fully express its capacity.

---

## 6. Why Renewable Generation Is More Difficult to Predict

The comparatively lower accuracy achieved across both renewable generation models — with R² values of approximately 0.74, against 0.89 for the demand forecasting model — reflects a fundamental difference in the nature of the target variable rather than a shortcoming specific to the modelling approach.

Electricity demand is driven predominantly by human behavioural patterns: household and commercial consumption follows stable diurnal cycles, day-of-week rhythms, and seasonal trends that are well-represented by temporal and lag features. Renewable electricity generation in Tasmania is driven primarily by hydroelectric facilities, supplemented to a lesser extent by wind generation. Hydroelectric output depends on a complex combination of factors including rainfall and river inflows, reservoir storage levels, inter-reservoir transfer decisions, maintenance schedules, and broader dispatch decisions made by generation operators. Wind generation is additionally dependent on prevailing atmospheric conditions. None of these factors are present in the current feature set, and none can be reliably inferred from historical demand, price, or generation lags alone.

The consequence is that while historical renewable generation provides a meaningful prior for near-term output — explaining why `renewable_lag_1` dominates feature importance — sudden changes in dispatch, unexpected variations in hydro availability, or shifts in wind resource cannot be anticipated by a model that has access only to the recent operational history. These unobserved drivers create residual variance that neither model can explain, placing a ceiling on achievable accuracy that is substantially lower than the ceiling for demand forecasting.

The **Basslink interconnector**, which links Tasmania's electricity grid to the mainland National Electricity Market, adds a further layer of complexity. Fluctuations in Basslink flow affect the balance between Tasmanian renewable generation and export, influencing observed renewable output in ways that are not captured by any feature currently in the dataset. Generator availability and planned maintenance outages introduce additional step-change discontinuities in renewable output that historical lag features cannot anticipate.

The modest predictive contribution of demand lags, price lags, and rolling averages across both models further reflects the limited statistical association between these variables and renewable generation at the hourly timescale — a finding that is consistent with the exploratory data analysis findings discussed in Section 7.

---

## 7. Relationship to Exploratory Data Analysis

The machine learning results align closely with the empirical observations established during the exploratory data analysis (EDA) phase of this project, and the performance gap between the renewable generation and demand forecasting models can be traced directly to the distributional properties identified at that stage.

EDA revealed that **renewable generation exhibited considerably greater variability than electricity demand** across the historical data. While demand followed stable and predictable diurnal and seasonal patterns — rising in the morning, peaking in the evening, falling overnight, and increasing in winter — renewable generation fluctuated over a much wider range, reflecting the responsiveness of hydroelectric dispatch to operational and hydrological conditions rather than fixed consumption patterns. EDA further demonstrated that **renewable generation could exceed electricity demand** during periods of favourable conditions, and could also **fall well below demand** during constrained periods. This wide and irregular range of outputs is fundamentally at odds with the kind of lag-based prediction that works well for demand, where tomorrow closely resembles today.

The machine learning results validate these EDA findings precisely. The demand forecasting model, operating on a target variable with strong temporal regularity, achieved an R² of 0.8943. The renewable generation models, operating on a target variable with substantially greater variability and weaker temporal structure, achieved R² values of 0.7410 and 0.7473 respectively — a consistent quantitative confirmation that the greater variability identified in EDA translates directly into lower forecasting accuracy.

The feature importance results also corroborate the EDA findings. The dominance of `renewable_lag_1` in both models — at 58.6% and 65.6% respectively — is the quantitative operationalisation of the strong short-term autocorrelation in renewable generation that EDA would have identified through autocorrelation analysis. The relatively limited predictive contribution of demand lags and price lags is consistent with the weak correlations between these variables and renewable generation observed during EDA: although demand and price are related to renewable generation at a macroeconomic level, these relationships are insufficiently stable at the hourly timescale to provide strong predictive signal. Feature engineering transformed the temporal and lagged relationships identified through EDA into numerical inputs that both models could exploit, and the achieved performance reflects both the value of those features and the hard limits imposed by the absence of environmental and operational data.

---

## 8. Final Model Selection

Based on the experimental results presented in this report, **Random Forest is recommended as the Version 1 baseline model for renewable generation forecasting** in the Tasmania Grid Intelligence and Forecasting Platform.

The grounds for this recommendation are as follows. The two models perform at virtually the same level across all three evaluation metrics. Gradient Boosting achieves a marginally lower RMSE (91.72 MW versus 92.85 MW) and a marginally higher R² (0.7473 versus 0.7410), but Random Forest achieves a marginally lower MAE (66.14 MW versus 67.22 MW). None of these differences is operationally significant: the absolute improvements offered by Gradient Boosting amount to approximately 1 MW in RMSE and 0.6 percentage points in R². Against these marginal gains, Random Forest offers meaningful practical advantages.

Random Forest is substantially simpler to train, to interpret, and to diagnose when predictions are poor. Its feature importance outputs are stable and well-understood. Its training process is embarrassingly parallelisable, making retraining computationally efficient as new data arrives. Gradient Boosting, by contrast, is a sequential algorithm with a larger and more sensitive set of hyperparameters: learning rate, tree depth, subsampling rate, and the number of estimators interact in ways that require careful tuning to realise its potential advantage. Under the default hyperparameter settings used in this study, that potential is clearly not being realised — Gradient Boosting's marginal improvement in R² and RMSE is outweighed by the additional complexity it introduces without a corresponding performance benefit.

It is worth noting that this recommendation is specific to the current experimental conditions. A fully optimised Gradient Boosting model — with learning rate, tree depth, and regularisation parameters tuned through systematic search — might achieve a more substantial improvement over the Random Forest baseline. The recommendation for Random Forest in Version 1 should therefore be understood as a practical choice for the current feature set and training configuration, with the expectation that Gradient Boosting becomes the primary candidate for evaluation once hyperparameter optimisation is undertaken as part of future model development.

---

## 9. Limitations

Both models are subject to a set of limitations that constrain the achievable forecasting accuracy and should be considered when interpreting the results in an operational context.

The most significant limitation is the **absence of weather variables** from the feature set. Temperature, rainfall, and wind speed are primary drivers of renewable generation in Tasmania — rainfall drives hydro inflows and reservoir replenishment, while wind speed directly determines wind generation output. Without access to these variables, the models cannot anticipate changes in renewable output that originate from changes in weather conditions, forcing reliance on historical generation lags as an indirect and imperfect proxy.

Similarly, there is no information on **hydro reservoir storage levels** or **hydro inflows** in the current dataset. These operational variables directly govern the dispatchable capacity of the hydroelectric fleet and the decisions made by generation operators. Changes in reservoir levels following dry or wet periods can produce sustained changes in renewable output that historical generation lags will not fully capture until the change has already begun to manifest.

**Basslink interconnector operational status** is absent from the feature set. Planned outages, deratings, or changes in Basslink flow direction can materially affect observed renewable generation in Tasmania by altering the incentives and constraints facing Tasmanian generators. Without this information, the models cannot anticipate step-changes in renewable output associated with interconnector events.

No information on **generator outages or maintenance schedules** is available. A significant unplanned generator outage can reduce renewable output substantially and instantaneously in a way that no lag-based model can predict from prior history.

Neither model has undergone **hyperparameter optimisation**. Both were trained using default scikit-learn hyperparameter settings, which may not represent the optimal configuration for either algorithm on this specific dataset. It is likely that systematic hyperparameter tuning — particularly for the Gradient Boosting model, where learning rate, tree depth, and subsampling rate have a significant effect on performance — would improve the achieved metrics for both models.

Finally, both models produce only **one-step-ahead predictions**: a single forecast for the next hour. Operational grid management often requires forecasts over longer horizons, and the current architecture does not support multi-step forecasting directly.

---

## 10. Future Improvements

Several concrete directions for future development could materially improve the forecasting accuracy of the renewable generation model.

The highest-priority improvement would be the **integration of weather data**, including temperature, rainfall, and wind speed, through connection to a meteorological API or the Bureau of Meteorology's gridded datasets. Weather variables would provide direct observational signals for the two primary drivers of Tasmanian renewable generation — hydro inflows and wind output — that are currently absent from the feature set.

**Hydro reservoir storage and inflow data**, if made available through the relevant generation operator or regulatory disclosures, would provide direct operational context for the dispatchable renewable fleet. This would allow the model to condition its predictions on the current hydro storage state rather than relying solely on the recent generation history.

**Basslink operational data** — including planned outage schedules and real-time interconnector flows — should be incorporated as a feature. Changes in Basslink operation create predictable step-changes in Tasmanian renewable generation that the current model cannot anticipate but that would be straightforward to encode if the data were available.

Evaluation of **XGBoost and LightGBM** — two highly optimised implementations of gradient boosting that offer improved performance, faster training, and built-in regularisation compared with scikit-learn's Gradient Boosting implementation — would be a natural next step. These frameworks are widely used in operational forecasting and have demonstrated consistent performance advantages over standard implementations on large tabular datasets.

**Hyperparameter optimisation** using grid search, random search, or Bayesian optimisation should be applied to both models before any definitive performance comparison is drawn. The current results reflect default configurations and understate the potential performance of both algorithms, particularly Gradient Boosting.

**Time-series cross-validation** — using multiple chronological train-test folds rather than a single split — would provide more robust and less variance-sensitive performance estimates, allowing more confident conclusions about which model genuinely outperforms the other.

Finally, extending the forecasting architecture to support **multi-step predictions** beyond the next hour would significantly expand the operational utility of the platform, enabling generation planning over two-, four-, and twenty-four-hour horizons.

---

## 11. Conclusion

This report has evaluated two supervised machine learning models — Random Forest and Gradient Boosting — for the task of one-hour-ahead renewable electricity generation forecasting for the Tasmanian grid. Both models were trained on identical feature-engineered datasets using the same chronological 80/20 train-test split, enabling direct comparison of their predictive performance.

Random Forest achieved an MAE of 66.14 MW, an RMSE of 92.85 MW, and an R² of 0.7410. Gradient Boosting achieved an MAE of 67.22 MW, an RMSE of 91.72 MW, and an R² of 0.7473. Across these three metrics, neither model is unambiguously superior: Gradient Boosting marginally reduces larger prediction errors and explains a fractionally higher proportion of output variance, while Random Forest achieves a marginally lower average prediction error. The performance gap between the two models is small and does not constitute a substantive argument for choosing one over the other on accuracy grounds alone.

Both models confirm that renewable generation forecasting is inherently more challenging than electricity demand forecasting under the current feature set. The R² values of approximately 0.74, compared with 0.89 for the demand model, reflect the greater variability and environmental sensitivity of renewable generation — a finding directly consistent with the patterns identified during exploratory data analysis. Historical renewable generation and the time of day carry the majority of predictable signal, but the residual variability introduced by hydro dispatch decisions, inflow conditions, and wind resource cannot be recovered from operational history alone.

Both models successfully capture the general temporal behaviour of renewable generation, tracking the overall level and diurnal pattern of output across an unseen five-month test period. Their limitations are structural: they are bounded by the absence of weather, hydrological, and operational data that governs the drivers of renewable output that lie outside historical generation lags. Addressing these limitations through data integration and expanded feature engineering represents the most direct path to improved forecasting accuracy in subsequent versions of the platform.

Random Forest is recommended as the Version 1 baseline model, given the near-identical performance of both approaches and the practical advantages that Random Forest offers in terms of simplicity, interpretability, and computational efficiency. Gradient Boosting remains a strong candidate for re-evaluation once hyperparameter optimisation has been performed and additional explanatory features have been incorporated into the modelling pipeline.
