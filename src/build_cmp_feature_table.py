from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_DATA = ROOT / "data" / "raw" / "synthetic_cmp_tool_data.csv"
FEATURE_TABLE = ROOT / "data" / "processed" / "cmp_feature_table.csv"
ALERT_TABLE = ROOT / "data" / "processed" / "cmp_alerts.csv"
TOOL_SUMMARY = ROOT / "reports" / "tool_health_summary.csv"

ROLLING_WINDOW = 6


REQUIRED_COLUMNS = {
    "timestamp",
    "tool_id",
    "pad_hours",
    "retaining_ring_hours",
    "platen_motor_current",
    "carrier_motor_current",
    "slurry_flow_rate",
    "downforce_pressure",
    "vibration",
    "temperature_c",
    "alarm_count",
    "wafer_removal_rate",
    "process_drift_nm",
    "maintenance_event",
    "maintenance_state",
}


def load_raw_data(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing raw data file: {path}. Run src/generate_synthetic_cmp_data.py first."
        )

    data = pd.read_csv(path, parse_dates=["timestamp"])
    missing_columns = REQUIRED_COLUMNS.difference(data.columns)
    if missing_columns:
        raise ValueError(f"Raw data is missing columns: {sorted(missing_columns)}")

    return data.sort_values(["tool_id", "timestamp"]).reset_index(drop=True)


def clean_data(data: pd.DataFrame) -> pd.DataFrame:
    cleaned = data.copy()

    non_negative_columns = [
        "pad_hours",
        "retaining_ring_hours",
        "platen_motor_current",
        "carrier_motor_current",
        "slurry_flow_rate",
        "vibration",
        "temperature_c",
        "alarm_count",
        "wafer_removal_rate",
        "process_drift_nm",
        "maintenance_event",
    ]
    for column in non_negative_columns:
        cleaned[column] = cleaned[column].clip(lower=0)

    cleaned["alarm_count"] = cleaned["alarm_count"].round().astype(int)
    cleaned["maintenance_event"] = cleaned["maintenance_event"].round().astype(int)
    return cleaned


def add_rolling_features(data: pd.DataFrame) -> pd.DataFrame:
    featured = data.copy()
    grouped = featured.groupby("tool_id", group_keys=False)

    rolling_columns = [
        "platen_motor_current",
        "carrier_motor_current",
        "slurry_flow_rate",
        "vibration",
        "temperature_c",
        "alarm_count",
        "wafer_removal_rate",
        "process_drift_nm",
    ]

    for column in rolling_columns:
        rolling_name = f"{column}_rolling_{ROLLING_WINDOW}h"
        featured[rolling_name] = grouped[column].transform(
            lambda series: series.rolling(ROLLING_WINDOW, min_periods=1).mean()
        )

    featured["pad_life_pct"] = (featured["pad_hours"] / 400 * 100).clip(0, 100)
    featured["retaining_ring_life_pct"] = (
        featured["retaining_ring_hours"] / 300 * 100
    ).clip(0, 100)
    featured["platen_current_delta_6h"] = (
        featured["platen_motor_current"]
        - featured["platen_motor_current_rolling_6h"]
    )
    featured["slurry_flow_delta_6h"] = (
        featured["slurry_flow_rate"]
        - featured["slurry_flow_rate_rolling_6h"]
    )
    featured["vibration_delta_6h"] = featured["vibration"] - featured["vibration_rolling_6h"]
    featured["removal_rate_delta_6h"] = (
        featured["wafer_removal_rate"]
        - featured["wafer_removal_rate_rolling_6h"]
    )
    featured["process_drift_delta_6h"] = (
        featured["process_drift_nm"]
        - featured["process_drift_nm_rolling_6h"]
    )
    featured["feature_platen_current_high"] = (
        featured["platen_motor_current"] > 22.0
    ).astype(int)
    featured["feature_carrier_current_high"] = (
        featured["carrier_motor_current"] > 14.5
    ).astype(int)
    featured["feature_slurry_flow_low"] = (
        featured["slurry_flow_rate"] < 190.0
    ).astype(int)
    featured["feature_vibration_high"] = (featured["vibration"] > 0.70).astype(int)
    featured["feature_pad_hours_high"] = (featured["pad_hours"] > 360.0).astype(int)
    featured["feature_alarm_burst"] = (featured["alarm_count"] >= 2).astype(int)
    featured["feature_removal_rate_low"] = (
        featured["wafer_removal_rate"] < 96.0
    ).astype(int)
    featured["feature_process_drift_high"] = (
        featured["process_drift_nm"] > 10.0
    ).astype(int)
    threshold_columns = [
        "feature_platen_current_high",
        "feature_carrier_current_high",
        "feature_slurry_flow_low",
        "feature_vibration_high",
        "feature_pad_hours_high",
        "feature_alarm_burst",
        "feature_removal_rate_low",
        "feature_process_drift_high",
    ]
    featured["sensor_threshold_count"] = featured[threshold_columns].sum(axis=1)

    return featured


def add_alert_rules(data: pd.DataFrame) -> pd.DataFrame:
    alerted = data.copy()

    alerted["alert_motor_vibration"] = (
        (alerted["platen_motor_current"] >= 22.0) & (alerted["vibration"] >= 0.70)
    )
    alerted["alert_slurry_flow"] = alerted["slurry_flow_rate"] <= 190.0
    alerted["alert_pad_wear"] = (
        (alerted["pad_hours"] >= 360.0) & (alerted["vibration"] >= 0.65)
    )
    alerted["alert_pressure_drift"] = ~alerted["downforce_pressure"].between(4.0, 4.4)
    alerted["alert_alarm_burst"] = alerted["alarm_count"] >= 2
    alerted["alert_process_drift"] = (
        (alerted["wafer_removal_rate"] <= 96.0)
        | (alerted["process_drift_nm"] >= 10.0)
    )

    alert_columns = [
        "alert_motor_vibration",
        "alert_slurry_flow",
        "alert_pad_wear",
        "alert_pressure_drift",
        "alert_alarm_burst",
        "alert_process_drift",
    ]
    alerted["rule_risk_points"] = alerted[alert_columns].sum(axis=1)

    alerted["rule_risk_level"] = np.select(
        [
            alerted["rule_risk_points"] >= 3,
            alerted["rule_risk_points"] == 2,
            alerted["rule_risk_points"] == 1,
        ],
        ["high", "medium", "low"],
        default="normal",
    )

    alerted["recommended_action"] = alerted.apply(build_recommended_action, axis=1)
    return alerted


def build_recommended_action(row: pd.Series) -> str:
    actions = []
    if row["alert_motor_vibration"]:
        actions.append("Check platen drive, carrier load, vibration source")
    if row["alert_slurry_flow"]:
        actions.append("Inspect slurry delivery flow, filters, and lines")
    if row["alert_pad_wear"]:
        actions.append("Inspect pad life, conditioner performance, retaining ring")
    if row["alert_pressure_drift"]:
        actions.append("Verify downforce pressure control and sensor calibration")
    if row["alert_alarm_burst"]:
        actions.append("Review recent alarms and tool event log")
    if row["alert_process_drift"]:
        actions.append("Check removal-rate drift, endpoint data, and process recipe inputs")

    if not actions:
        return "Continue normal monitoring"
    return "; ".join(actions)


def write_outputs(featured: pd.DataFrame) -> None:
    FEATURE_TABLE.parent.mkdir(parents=True, exist_ok=True)
    TOOL_SUMMARY.parent.mkdir(parents=True, exist_ok=True)

    featured.to_csv(FEATURE_TABLE, index=False)

    alert_rows = featured[featured["rule_risk_level"] != "normal"].copy()
    alert_rows.to_csv(ALERT_TABLE, index=False)

    latest_by_tool = (
        featured.sort_values("timestamp")
        .groupby("tool_id", as_index=False)
        .tail(1)
        .sort_values("tool_id")
    )
    summary_columns = [
        "tool_id",
        "timestamp",
        "maintenance_state",
        "rule_risk_level",
        "rule_risk_points",
        "pad_life_pct",
        "retaining_ring_life_pct",
        "platen_motor_current",
        "slurry_flow_rate",
        "vibration",
        "wafer_removal_rate",
        "process_drift_nm",
        "alarm_count",
        "maintenance_event",
        "recommended_action",
    ]
    latest_by_tool[summary_columns].to_csv(TOOL_SUMMARY, index=False)


def main() -> None:
    raw = load_raw_data(RAW_DATA)
    cleaned = clean_data(raw)
    featured = add_rolling_features(cleaned)
    alerted = add_alert_rules(featured)
    write_outputs(alerted)

    print(f"Wrote feature table: {FEATURE_TABLE}")
    print(f"Wrote alert table: {ALERT_TABLE}")
    print(f"Wrote tool summary: {TOOL_SUMMARY}")
    print(f"Rows processed: {len(alerted):,}")
    print(f"Alert rows: {(alerted['rule_risk_level'] != 'normal').sum():,}")


if __name__ == "__main__":
    main()
