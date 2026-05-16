# CMP Predictive Maintenance Project Plan

## Career Target

Use this project to support applications for CMP equipment technician roles, especially roles involving semiconductor manufacturing equipment, preventive maintenance, troubleshooting, tool availability, and process support.

## Project Story

"I built a CMP predictive maintenance project that simulates tool sensor data, identifies abnormal equipment trends, and recommends maintenance checks before failures cause downtime."

## Technical Milestones

### Milestone 1: CMP Equipment Research

- Learn the main CMP modules: platen, carrier head, slurry delivery, pad conditioning, endpoint/process monitoring, and wafer handling.
- Document common maintenance items: pad wear, retaining ring wear, slurry delivery issues, conditioner wear, pressure drift, vibration, motor current changes, leaks, and sensor faults.
- Create a short technician glossary in `reports/cmp_glossary.md`.

### Milestone 2: Dataset

- Start with synthetic CMP equipment data.
- Include multiple tools, shifts, sensor readings, alarm counts, usage hours, and maintenance events.
- Label rows with normal operation, warning state, and maintenance-needed state.

### Milestone 3: Baseline Rules

- Build rule-based alerts that a technician would understand.
- Examples:
  - High motor current plus rising vibration
  - Low slurry flow plus removal-rate drift
  - High pad usage hours plus conditioner instability

### Milestone 4: Predictive Model

- Train a simple model to predict maintenance risk.
- Prioritize explainability over complexity.
- Show feature importance so the output is useful for troubleshooting.

### Milestone 5: Dashboard

- Build a small dashboard showing:
  - Tool health score
  - Recent alarms
  - Sensor trends
  - Recommended maintenance checks
  - Risk level by tool

### Milestone 6: Job-Ready Writeup

- Write a one-page case study:
  - Problem
  - Data used
  - Method
  - Results
  - Technician action plan
  - What this shows about your readiness for CMP equipment work

## Resume Bullet Drafts

- Built a CMP predictive maintenance project using Python to detect abnormal tool behavior from simulated sensor, alarm, and maintenance data.
- Created rule-based and machine-learning maintenance risk indicators for CMP equipment conditions such as motor current drift, slurry flow instability, vibration increase, and pad usage.
- Developed technician-focused documentation translating model outputs into practical maintenance checks and troubleshooting actions.

## Interview Talking Points

- Why CMP downtime matters in semiconductor manufacturing
- How sensor drift can reveal equipment degradation before failure
- Why explainable alerts are more useful to technicians than black-box predictions
- How preventive maintenance supports tool availability, yield, and safety

