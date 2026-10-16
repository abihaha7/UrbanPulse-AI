# UrbanPulse AI — Forecasting Experiment Record

## Dataset
- Source: UCI Beijing Multi-Site Air Quality dataset
- Station analyzed: Aotizhongxin
- Raw station records: 35,064
- Time range: 0 to 35063
- Forecast horizon: One hour ahead

## Target
- Target variable: PM2.5 at the next hour
- Target construction: PM2.5 shifted by -1 hour
- Training target observations: 24,034
- Validation target observations: 5,217
- Test target observations: 5,225

## Chronological Split
- Training period: 2013-03-01 00:00:00 to 2015-12-18 15:00:00
- Validation period: 2015-12-18 16:00:00 to 2016-07-24 19:00:00
- Test period: 2016-07-24 20:00:00 to 2017-02-28 23:00:00
- Predictors: 20

## Models Evaluated
1. Persistence baseline: current-hour PM2.5 used as the next-hour forecast.
2. Original Random Forest: 100 trees, maximum depth 20, minimum leaf size 2.
3. Weighted Random Forest: same hyperparameters, with training sample weights
   increased for higher next-hour PM2.5 values.
4. Change-based Random Forest: predicts the one-hour PM2.5 change and adds
   the predicted change to current-hour PM2.5.

## Evaluation
- Metrics: MAE, RMSE, and R-squared.
- Additional analysis: performance by observed PM2.5 concentration band,
  extreme-pollution error bias, and individual high-pollution episodes.
- Exploratory extreme-pollution threshold: actual next-hour PM2.5 > 250 µg/m³.
- The concentration bands are analytical groupings, not official health categories.

### Common Evaluation Samples
- The test partition contains 5,225 valid next-hour PM2.5 targets.
- The four-model comparison uses 5,223 common observations after excluding two timestamps with missing current-hour PM2.5 values.
- All models in the reported overall comparison are evaluated on these same 5,223 observations to support a fair comparison.
- Pollution-band and extreme-pollution comparisons use this common evaluation set, grouped by observed next-hour PM2.5 concentration.

## Important Limitation
The test set was examined repeatedly during exploratory model comparisons.
Therefore, these results should not be treated as a completely untouched
final estimate after model selection. Further tuning should use training
and validation data, followed by evaluation on a fresh or otherwise
untouched chronological test period.

## Recorded
2026-10-09 18:54
