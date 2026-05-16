# CMP Predictive Maintenance Case Study

## Project Summary

I built a CMP predictive maintenance workflow that simulates CMP tool sensor data, detects abnormal equipment trends, predicts maintenance risk, and translates the results into technician-focused maintenance checks.

The project is designed around a practical fab equipment question:

> Which CMP tool is showing early signs of degradation, and what should a technician check first?

## Problem

CMP tools can show warning signs before a maintenance event or process issue becomes obvious. Trends such as increasing motor current, rising vibration, lower slurry flow, pad wear, retaining ring usage, alarm bursts, or pressure drift can point to equipment degradation.

If those signs are not caught early, the tool may create downtime, scrap risk, process instability, or extra troubleshooting time. The goal of this project was to turn CMP-style equipment signals into clear maintenance risk indicators.

## Data

The project uses synthetic CMP equipment data so it can be shared publicly without exposing proprietary fab data.

This case study does not include real equipment logs, employer-owned process data, customer information, recipes, tool exports, or confidential maintenance records. All data and tool behavior are simulated for portfolio demonstration purposes.

Dataset summary:

- Rows analyzed: 3,240
- Tools simulated: CMP-01, CMP-02, CMP-03
- Time range: hourly readings across 45 days per tool
- Alert rows found by baseline rules: 586
- Simulated maintenance events: 6

Key signals included:

- Pad usage hours
- Retaining ring usage hours
- Platen motor current
- Carrier motor current
- Slurry flow rate
- Downforce pressure
- Vibration
- Temperature
- Alarm count
- Wafer removal rate
- Process drift
- Maintenance event flag
- Maintenance state label: normal, warning, maintenance_needed

Maintenance labels:

```text
normal                2758
maintenance_needed     366
warning                116
```

## Method

The workflow has five parts:

1. Generate synthetic CMP equipment data.
2. Clean the data and build rolling trend features.
3. Create rule-based alerts that a technician can understand.
4. Train a machine learning model to classify maintenance risk.
5. Build a dashboard that shows tool health, alert reasons, predictions, and recommended checks.

The rule-based alerts focused on practical CMP troubleshooting patterns:

- High platen motor current plus elevated vibration
- Low slurry flow
- High pad usage plus elevated vibration
- Downforce pressure outside the expected range
- Multiple alarms in the same hour
- Removal-rate or process-drift abnormality

The synthetic data also includes post-maintenance reset behavior, so pad hours and retaining ring hours drop after scheduled maintenance events. The model was trained on sensor readings, usage counters, process signals, and rolling six-hour trend features. Rule alert columns and recommended action text were excluded from model training so the model learned from equipment behavior instead of memorizing the hand-built rule outputs.

## Results

The latest tool health summary shows all three tools back in normal monitoring after maintenance reset behavior:

| Tool | Current Risk | Maintenance State | Rule Points | Key Issue |
| --- | --- | --- | ---: | --- |
| CMP-01 | Normal | normal | 0 | Continue normal monitoring |
| CMP-02 | Normal | normal | 0 | Continue normal monitoring |
| CMP-03 | Normal | normal | 0 | Continue normal monitoring |

Historical rule alert counts by tool:

| Tool | High | Medium | Low | Normal |
| --- | ---: | ---: | ---: | ---: |
| CMP-01 | 115 | 52 | 46 | 867 |
| CMP-02 | 84 | 57 | 48 | 891 |
| CMP-03 | 71 | 53 | 60 | 896 |

The predictive model reached 99.9% test accuracy on a stratified train-test split after adding explainable domain-threshold sensor features.

Model classification results:

```text
maintenance_needed precision: 1.00, recall: 1.00, f1-score: 1.00
normal             precision: 1.00, recall: 1.00, f1-score: 1.00
warning            precision: 1.00, recall: 0.97, f1-score: 0.98
overall accuracy:  0.999
```

Top model features:

1. Sensor threshold count
2. Process drift rolling six-hour average
3. Retaining ring hours
4. Retaining ring life percentage
5. Wafer removal rate rolling six-hour average
6. Pad hours
7. Process drift

These features make practical sense for CMP maintenance because process drift, removal rate, consumable wear, motor load, vibration, and slurry delivery are all useful indicators of tool condition.

## Technician Action Plan

For high-risk tools such as CMP-02 and CMP-03:

1. Inspect slurry delivery flow, filters, and lines.
2. Check platen drive behavior, carrier load, and vibration source.
3. Inspect pad life, pad conditioner performance, and retaining ring condition.
4. Review recent alarms and tool event logs.
5. Check removal-rate drift, endpoint data, and process recipe inputs.
6. Verify sensor readings against expected equipment ranges before returning the tool to normal operation.

For medium-risk tools such as CMP-01:

1. Continue monitoring slurry flow and vibration trend.
2. Check pad and retaining ring usage.
3. Schedule preventive maintenance if high motor current and vibration persist.

## Dashboard

Live dashboard:

```text
https://cmp-predictive-maintenance.streamlit.app
```

The Streamlit dashboard shows:

- Current tool priority
- Risk level by tool
- Recommended technician checks
- Sensor trend charts
- Recent alert rows
- Model predictions
- Model confidence and technician review priority
- Feature importance
- Model metrics

Run it locally with:

```powershell
streamlit run .\src\dashboard.py --server.port 8502
```

## What This Project Demonstrates

This project demonstrates:

- Understanding of CMP equipment signals, process drift, and consumable-driven maintenance risk
- Ability to build a data pipeline from raw data to technician-readable outputs
- Rule-based troubleshooting logic for abnormal CMP tool behavior
- Basic machine learning for maintenance risk classification
- Model confidence scoring for technician review priority
- Clear communication through reports and a dashboard
- Awareness that explainable alerts are more useful to technicians than black-box predictions alone

## Interview Explanation

I would explain the project this way:

> I built a CMP predictive maintenance project that simulates tool sensor data, maintenance resets, removal-rate drift, and process drift. It identifies abnormal trends and recommends maintenance checks before failures cause downtime. I started with rule-based alerts for conditions a technician would recognize, like high motor current with rising vibration, low slurry flow, or process drift. Then I trained a simple model to classify tool states as normal, warning, or maintenance-needed. Finally, I built a dashboard that shows tool health, recent alerts, sensor trends, model predictions, confidence, and recommended technician actions.

## Limitations And Next Improvements

The current dataset is synthetic, so the model result should be treated as a project demonstration rather than a production-ready fab model.

Good next improvements would be:

- Add dashboard exports for technician handoff.
- Add false-alarm review thresholds and alert suppression after PM.
- Connect the dashboard to real equipment logs or exported historian data.
