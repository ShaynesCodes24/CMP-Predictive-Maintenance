# CMP Maintenance Risk Model Metrics

This model predicts the CMP maintenance state from sensor readings, usage counters, and rolling trend features.

## Training Setup

- Training rows: 2,430
- Test rows: 810
- Split method: stratified 75/25 train-test split
- Model: Random forest classifier with balanced class weights
- Target: maintenance_state
- Excluded from training: rule alert columns and recommended_action text
- Added domain-threshold sensor features for explainable maintenance boundaries.
- Prediction outputs include model confidence and a technician review priority.
- Note: A pure time-based split was tested first, but the early timeline only contained normal rows. The stratified split is better for this starter demo because it lets the model learn all three states.
- Exact test accuracy: 99.877%

## Class Counts

### Training

```text
maintenance_state
normal                2069
maintenance_needed     274
warning                 87
```

### Test

```text
maintenance_state
normal                689
maintenance_needed     92
warning                29
```

## Classification Report

```text
                    precision    recall  f1-score   support

maintenance_needed       1.00      1.00      1.00        92
            normal       1.00      1.00      1.00       689
           warning       1.00      0.97      0.98        29

          accuracy                           1.00       810
         macro avg       1.00      0.99      0.99       810
      weighted avg       1.00      1.00      1.00       810

```

## Confusion Matrix

Rows are actual labels. Columns are predicted labels.

| index | maintenance_needed | normal | warning |
| --- | --- | --- | --- |
| maintenance_needed | 92 | 0 | 0 |
| normal | 0 | 689 | 0 |
| warning | 0 | 1 | 28 |

## Top Feature Importance

| feature | importance |
| --- | --- |
| sensor_threshold_count | 0.2008861676649468 |
| process_drift_nm_rolling_6h | 0.09889206949227974 |
| retaining_ring_hours | 0.08197100636342514 |
| retaining_ring_life_pct | 0.08089537322513768 |
| wafer_removal_rate_rolling_6h | 0.0731507447231287 |
| pad_hours | 0.06800914388217313 |
| process_drift_nm | 0.06640832461787577 |
| pad_life_pct | 0.06338329053310926 |
| vibration_rolling_6h | 0.04856462198937812 |
| wafer_removal_rate | 0.03711446100576032 |

## Technician Interpretation

The strongest model inputs show which equipment trends are most useful for estimating maintenance risk. High-importance features are good candidates for dashboard trend charts and technician review.
