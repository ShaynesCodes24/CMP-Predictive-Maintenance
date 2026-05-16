# CMP Predictive Maintenance Project

Portfolio project for demonstrating semiconductor equipment technician skills with a focus on Chemical Mechanical Planarization (CMP) tool health, fault detection, predictive maintenance, and technician-ready communication.

![CMP Tool Health Dashboard](reports/images/dashboard_preview.png)

## Project Story

I built a CMP predictive maintenance workflow that simulates tool sensor data, identifies abnormal equipment trends, predicts maintenance risk, and recommends practical maintenance checks before failures cause downtime.

The project answers:

- Which CMP tool is showing abnormal behavior?
- Which sensor trends suggest degradation?
- What maintenance action should be checked first?
- How urgent is the issue?
- How would early detection reduce downtime or scrap risk?

## Why This Matters

CMP tools rely on stable mechanical motion, slurry delivery, pressure control, consumable condition, and process monitoring. A tool can begin drifting before a hard fault occurs. Rising motor current, elevated vibration, low slurry flow, alarm bursts, and worn consumables can all point toward maintenance risk.

This project turns those equipment signals into technician-focused outputs:

- Rule-based alerts that are easy to explain
- A machine learning model for maintenance risk classification
- A dashboard for tool health review
- A case study written for interviews and portfolio review

## Data And Confidentiality

This project uses synthetic CMP-style equipment data only. It does not include proprietary fab data, real equipment logs, customer information, employer-owned process data, recipes, tool exports, or confidential maintenance records.

The model accuracy and dashboard outputs should be understood as a portfolio demonstration of predictive maintenance workflow design, not as a production fab model.

## Usage Rights

This project is shared for portfolio and educational review. All rights are reserved. See `LICENSE` for details.

## Current Results

Latest tool priority:

| Tool | Current Risk | Maintenance State | Rule Points | Recommended Focus |
| --- | --- | --- | ---: | --- |
| CMP-01 | Normal | normal | 0 | Continue normal monitoring after PM reset |
| CMP-02 | Normal | normal | 0 | Continue normal monitoring after PM reset |
| CMP-03 | Normal | normal | 0 | Continue normal monitoring after PM reset |

Dataset and alert summary:

- 3,240 synthetic CMP sensor rows
- 3 simulated CMP tools
- 586 rule-based alert rows
- 6 simulated maintenance events with post-maintenance reset behavior
- Labels: normal, warning, maintenance_needed

Model summary:

- Model: Random forest classifier
- Test accuracy: 99.9%
- Target: `maintenance_state`
- Top features: sensor threshold count, process drift trend, retaining ring life, wafer removal rate trend, pad life

## Dashboard

The Streamlit dashboard shows:

- Current tool priority
- Risk level by tool
- Recommended technician checks
- Sensor trend charts
- Maintenance event timeline
- Recent alert rows
- Model predictions
- Model confidence and technician review priority
- Feature importance
- Model metrics
- Downloadable CSV exports for technician handoff

### Live Dashboard

This app is ready to deploy on Streamlit Community Cloud. Use this repository,
the `main` branch, and `app.py` as the main file path.

Recommended public app URL:

```text
https://cmp-predictive-maintenance.streamlit.app
```

After deployment, share that Streamlit link with recruiters, hiring managers,
or portfolio viewers so they can interact with the filters, charts, tables, and
downloads directly in the browser.

Launch it with:

```powershell
.\.venv\Scripts\Activate.ps1
streamlit run .\src\dashboard.py --server.port 8502
```

Then open:

```text
http://localhost:8502
```

Deploy it publicly:

1. Push this repository to GitHub.
2. Open Streamlit Community Cloud and create a new app.
3. Select `ShaynesCodes24/CMP-Predictive-Maintenance`.
4. Select the `main` branch.
5. Set the main file path to `app.py`.
6. Choose `cmp-predictive-maintenance` as the app URL if it is available.
7. Deploy the app, then replace any placeholder dashboard links with the final
   `streamlit.app` URL.

## Project Outputs

- `reports/cmp_predictive_maintenance_case_study.md`: job-ready case study
- `reports/demo_script.md`: interview and dashboard presentation script
- `reports/social_launch_kit.md`: LinkedIn post, GitHub topics, and demo video script
- `reports/maintenance_alert_report.md`: technician-focused alert report
- `reports/model_metrics.md`: model performance and interpretation
- `reports/model_feature_importance.csv`: feature importance values
- `reports/tool_health_summary.csv`: latest tool health snapshot
- `data/raw/synthetic_cmp_tool_data.csv`: generated synthetic CMP sensor data
- `data/processed/cmp_feature_table.csv`: cleaned feature table
- `data/processed/cmp_alerts.csv`: rule-based alert rows
- `data/processed/cmp_model_predictions.csv`: model predictions
- `models/cmp_maintenance_risk_model.joblib`: trained model artifact

## Project Workflow

```text
Synthetic CMP data
  -> Cleaned feature table
  -> Technician-readable rule alerts
  -> Maintenance risk model
  -> Dashboard and case study
```

## Equipment Signals Modeled

- Platen motor current
- Carrier motor current
- Slurry flow rate
- Downforce pressure
- Pad usage hours
- Retaining ring usage hours
- Vibration
- Tool temperature
- Alarm count
- Wafer removal rate
- Process drift
- Maintenance event flag
- Maintenance state

## Rule-Based Alert Examples

The baseline alert logic checks for CMP conditions a technician could reason through:

- High platen motor current with elevated vibration
- Low slurry flow
- High pad usage with elevated vibration
- Downforce pressure outside expected range
- Multiple alarms in the same hour
- Removal-rate or process-drift abnormality

These rules produce practical recommended actions such as checking slurry delivery, platen drive behavior, carrier load, vibration source, pad condition, conditioner performance, retaining ring wear, removal-rate drift, endpoint data, process recipe inputs, and recent alarm history.

## How To Run The Project

Run the full project pipeline and launch the dashboard:

```powershell
.\run_project.ps1
```

Run the pipeline without opening the dashboard:

```powershell
.\run_project.ps1 -NoDashboard
```

Skip dependency installation if packages are already installed:

```powershell
.\run_project.ps1 -SkipInstall
```

Manual steps are listed below for transparency.

Create and activate the virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Generate synthetic CMP data:

```powershell
python .\src\generate_synthetic_cmp_data.py
```

Build the cleaned feature table and rule alert outputs:

```powershell
python .\src\build_cmp_feature_table.py
```

Generate the technician maintenance alert report:

```powershell
python .\src\generate_maintenance_alert_report.py
```

Train the maintenance risk model:

```powershell
python .\src\train_maintenance_risk_model.py
```

Launch the dashboard:

```powershell
streamlit run .\src\dashboard.py --server.port 8502
```

## Project Structure

```text
CMP-Predictive-Maintenance/
  data/
    raw/
      synthetic_cmp_tool_data.csv
    processed/
      cmp_feature_table.csv
      cmp_alerts.csv
      cmp_model_predictions.csv
  models/
    cmp_maintenance_risk_model.joblib
  reports/
    cmp_glossary.md
    cmp_predictive_maintenance_case_study.md
    demo_script.md
    social_launch_kit.md
    maintenance_alert_report.md
    model_feature_importance.csv
    model_metrics.md
    tool_health_summary.csv
  src/
    build_cmp_feature_table.py
    dashboard.py
    generate_maintenance_alert_report.py
    generate_synthetic_cmp_data.py
    train_maintenance_risk_model.py
  run_project.ps1
  .gitignore
  LICENSE
  PROJECT_PLAN.md
  README.md
  requirements.txt
```

## Interview Talking Point

I would describe the project this way:

> I built a CMP predictive maintenance project that simulates tool sensor data, identifies abnormal trends, and recommends maintenance checks before failures cause downtime. I started with rule-based alerts for conditions a technician would recognize, like high motor current with rising vibration or low slurry flow. Then I trained a simple model to classify tool states as normal, warning, or maintenance-needed. Finally, I built a dashboard that shows tool health, recent alerts, sensor trends, model predictions, and recommended technician actions.

## Limitations

This project uses synthetic data, so the model result should be treated as a portfolio demonstration rather than a production fab model. A real deployment would need real equipment logs, maintenance event history, process context, validation with engineers and technicians, and controls for false alarms.

## Next Improvements

- Add false-alarm review thresholds and alert suppression after PM.
- Connect the dashboard to exported historian or equipment log data.
