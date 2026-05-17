# How I Would Explain This Project In An Interview

I built a CMP predictive maintenance system that simulates semiconductor tool sensor data, detects abnormal equipment trends, estimates maintenance risk, and converts those signals into technician-focused troubleshooting guidance.

CMP tools matter because wafer polishing depends on stable mechanical motion, slurry delivery, downforce pressure, pad condition, retaining ring condition, and removal-rate control. Small drift in those signals can lead to defects, downtime, scrap risk, or yield loss.

The project monitors platen motor current, carrier motor current, slurry flow, downforce pressure, pad usage, retaining ring usage, vibration, temperature, alarms, wafer removal rate, process drift, and maintenance reset events.

The alert system combines explainable rule-based checks with a machine learning model. The rules flag technician-readable problems such as high vibration, low slurry flow, pad wear, pressure drift, alarm bursts, and process drift. The model classifies tool state as normal, warning, or maintenance-needed.

A technician would use the dashboard to identify the priority tool, review probable root causes, follow recommended checks, compare before-vs-after maintenance behavior, and generate a shift handoff note for the next technician or engineer.

The strongest next improvements would be connecting the workflow to real historian or equipment log exports, validating thresholds with technicians and process engineers, adding false-alarm review, and tracking whether recommended actions actually reduce downtime or scrap.
