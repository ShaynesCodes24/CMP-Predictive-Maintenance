# CMP Predictive Maintenance Demo Script

## 30-Second Pitch

I built a CMP predictive maintenance project that simulates tool sensor data, detects abnormal equipment trends, predicts maintenance risk, and turns the results into technician-focused maintenance checks.

The project is built around a fab equipment question:

> Which CMP tool is drifting, how urgent is it, and what should a technician check first?

It includes a full workflow: synthetic CMP data generation, feature engineering, rule-based fault alerts, a maintenance risk model, a Streamlit dashboard, and a case study.

Live dashboard:
https://cmp-predictive-maintenance.streamlit.app

## 60-Second Version

This project focuses on Chemical Mechanical Planarization equipment health. I simulated hourly sensor readings for three CMP tools, including platen motor current, carrier current, slurry flow, downforce pressure, vibration, pad hours, retaining ring hours, wafer removal rate, process drift, alarms, and maintenance events.

I built rule-based alerts for conditions a technician would recognize, such as high motor current with elevated vibration, low slurry flow, high pad usage, pressure drift, alarm bursts, and removal-rate drift. Then I trained a random forest model to classify each tool state as normal, warning, or maintenance-needed.

The dashboard shows current tool priority, recent alerts, sensor trends, maintenance event resets, model predictions, model confidence, feature importance, and recommended technician checks.

Live dashboard:
https://cmp-predictive-maintenance.streamlit.app

## Dashboard Walkthrough

1. Start with the Executive Summary.
   - Point out the current normal/warning/maintenance-needed tool count.
   - Mention the total maintenance events and latest recommended action.

2. Show Current Tool Priority.
   - Explain that each tool has a rule risk level and rule points.
   - Mention that the latest state is normal because the synthetic tools have gone through post-maintenance reset behavior.

3. Show Recommended Technician Checks.
   - Explain that the goal is not just to predict a label.
   - The output tells a technician what to inspect: slurry delivery, motor/vibration source, pad condition, retaining ring condition, process drift, endpoint data, and alarms.

4. Show Sensor Trend.
   - Pick `platen_motor_current`, `vibration`, `wafer_removal_rate`, or `process_drift_nm`.
   - Explain that vertical markers show maintenance events.
   - Point out how risk rises before maintenance and resets afterward.

5. Show Recent Alerts.
   - Explain that alert rows are filtered down from the full feature table.
   - These rows are the practical troubleshooting queue.

6. Show Model Predictions.
   - Explain predicted state, probability columns, model confidence, and review priority.
   - Point out that confidence helps decide whether something needs urgent review or normal monitoring.

7. Show Feature Importance.
   - Explain that the strongest feature is `sensor_threshold_count`, followed by process drift, retaining ring life, wafer removal rate trend, and pad life.
   - Tie this back to CMP equipment behavior.

## How To Explain 99.9% Accuracy

Say this clearly:

> The model reached 99.877% test accuracy on synthetic data. I do not treat that as a production claim. The high score makes sense because the data is synthetic and I added explainable domain-threshold features that match the way the labels are generated. In a real fab environment, I would validate the model against real equipment logs, maintenance history, false alarms, and technician feedback.

That answer is important because it shows judgment. You are not pretending synthetic model accuracy equals production readiness.

## Technician Relevance

This project connects to CMP equipment technician work because it focuses on:

- Preventive maintenance
- Tool availability
- Consumable wear
- Slurry delivery checks
- Motor current and vibration trends
- Alarm review
- Process drift and removal-rate stability
- Turning data into practical troubleshooting actions

## Interview Q&A Prep

### Why did you choose CMP?

CMP is a critical semiconductor process where tool stability matters. Mechanical motion, slurry delivery, pad condition, retaining ring wear, pressure control, and endpoint behavior can all affect process performance and downtime.

### What problem were you solving?

I wanted to identify abnormal tool behavior before it becomes downtime. The project turns sensor trends into early warnings and technician action recommendations.

### Why use both rules and machine learning?

Rules are easier for technicians to trust because they map directly to known equipment behavior. The model adds pattern recognition across multiple signals. Together they make the output more explainable.

### What does the dashboard show?

It shows current tool priority, recent alerts, sensor trends, maintenance reset events, recommended checks, model predictions, confidence, and feature importance.

### What would you improve with real fab data?

I would connect equipment logs, maintenance work orders, process drift data, and alarm history. Then I would validate the alert thresholds with technicians and engineers to reduce false alarms.

### What does this project show about you?

It shows that I can learn equipment behavior, work with data, build a practical Python workflow, think like a technician, and communicate findings clearly.

## Resume Bullets

- Built a CMP predictive maintenance project using Python to simulate tool sensor data, detect abnormal equipment trends, and recommend technician maintenance checks.
- Created rule-based alerts for CMP conditions including high motor current, vibration increase, low slurry flow, pad wear, retaining ring wear, alarm bursts, and process drift.
- Trained a maintenance risk model to classify CMP tool states as normal, warning, or maintenance-needed, with model confidence and feature-importance reporting.
- Developed and deployed a Streamlit dashboard showing tool priority, sensor trends, maintenance events, recent alerts, model predictions, and technician action recommendations.

## Short Closing Statement

This project shows that I can connect equipment behavior, data analysis, and technician decision-making. The most important part is not just the model accuracy. It is that the output explains what changed, why it matters, and what maintenance check should happen next.
