from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
FEATURE_TABLE = ROOT / "data" / "processed" / "cmp_feature_table.csv"
REPORT = ROOT / "reports" / "maintenance_alert_report.md"

ALERT_LABELS = {
    "alert_motor_vibration": "High motor current with elevated vibration",
    "alert_slurry_flow": "Low slurry flow",
    "alert_pad_wear": "High pad usage with elevated vibration",
    "alert_pressure_drift": "Downforce pressure outside normal range",
    "alert_alarm_burst": "Multiple alarms in the same hour",
    "alert_process_drift": "Removal rate or process drift outside normal range",
}

RISK_ORDER = {
    "high": 0,
    "medium": 1,
    "low": 2,
    "normal": 3,
}


def load_feature_table(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing feature table: {path}. Run src/build_cmp_feature_table.py first."
        )

    data = pd.read_csv(path, parse_dates=["timestamp"])
    return data.sort_values(["tool_id", "timestamp"]).reset_index(drop=True)


def active_alerts(row: pd.Series) -> list[str]:
    return [label for column, label in ALERT_LABELS.items() if bool(row[column])]


def format_action_list(action_text: str) -> list[str]:
    return [action.strip() for action in action_text.split(";") if action.strip()]


def latest_tool_rows(data: pd.DataFrame) -> pd.DataFrame:
    latest = data.groupby("tool_id", as_index=False).tail(1).copy()
    latest["risk_sort"] = latest["rule_risk_level"].map(RISK_ORDER)
    return latest.sort_values(["risk_sort", "rule_risk_points", "tool_id"], ascending=[True, False, True])


def build_tool_section(tool_id: str, tool_data: pd.DataFrame) -> list[str]:
    latest = tool_data.tail(1).iloc[0]
    recent_alerts = tool_data[tool_data["rule_risk_level"] != "normal"].tail(5)
    alert_reasons = active_alerts(latest)
    actions = format_action_list(latest["recommended_action"])

    lines = [
        f"## {tool_id}",
        "",
        f"- Current risk: **{latest['rule_risk_level'].upper()}** ({latest['rule_risk_points']} rule points)",
        f"- Maintenance label: **{latest['maintenance_state']}**",
        f"- Latest reading: {latest['timestamp']}",
        f"- Pad life used: {latest['pad_life_pct']:.1f}%",
        f"- Retaining ring life used: {latest['retaining_ring_life_pct']:.1f}%",
        f"- Latest maintenance event flag: {int(latest['maintenance_event'])}",
        "",
        "### Why It Was Flagged",
        "",
    ]

    if alert_reasons:
        lines.extend([f"- {reason}" for reason in alert_reasons])
    else:
        lines.append("- No active rule alerts on the latest reading.")

    lines.extend(["", "### Latest Sensor Snapshot", ""])
    lines.extend(
        [
            f"- Platen motor current: {latest['platen_motor_current']:.2f} A",
            f"- Carrier motor current: {latest['carrier_motor_current']:.2f} A",
            f"- Slurry flow rate: {latest['slurry_flow_rate']:.2f}",
            f"- Downforce pressure: {latest['downforce_pressure']:.3f}",
            f"- Vibration: {latest['vibration']:.3f}",
            f"- Wafer removal rate: {latest['wafer_removal_rate']:.2f}",
            f"- Process drift: {latest['process_drift_nm']:.2f} nm",
            f"- Alarm count: {int(latest['alarm_count'])}",
            "",
            "### Recommended Technician Checks",
            "",
        ]
    )

    lines.extend([f"- {action}" for action in actions])

    lines.extend(["", "### Recent Alert Evidence", ""])
    if recent_alerts.empty:
        lines.append("- No recent alert rows for this tool.")
    else:
        for _, row in recent_alerts.iterrows():
            reasons = ", ".join(active_alerts(row)) or "No active rule"
            lines.append(
                f"- {row['timestamp']}: {row['rule_risk_level']} risk, "
                f"{int(row['rule_risk_points'])} points - {reasons}"
            )

    lines.append("")
    return lines


def build_report(data: pd.DataFrame) -> str:
    latest = latest_tool_rows(data)
    alert_count = int((data["rule_risk_level"] != "normal").sum())
    latest_high = latest[latest["rule_risk_level"] == "high"]["tool_id"].tolist()

    lines = [
        "# CMP Maintenance Alert Report",
        "",
        "This report translates the rule-based CMP equipment alerts into technician-focused maintenance checks.",
        "",
        "## Overall Status",
        "",
        f"- Rows analyzed: {len(data):,}",
        f"- Alert rows found: {alert_count:,}",
        f"- Tools reviewed: {data['tool_id'].nunique()}",
        f"- Tools currently high risk: {', '.join(latest_high) if latest_high else 'None'}",
        "",
        "## Tool Priority",
        "",
    ]

    for _, row in latest.iterrows():
        lines.append(
            f"- {row['tool_id']}: {row['rule_risk_level'].upper()} risk, "
            f"{int(row['rule_risk_points'])} rule points, "
            f"maintenance state: {row['maintenance_state']}"
        )

    lines.append("")

    for tool_id, tool_data in data.groupby("tool_id", sort=True):
        lines.extend(build_tool_section(tool_id, tool_data))

    return "\n".join(lines)


def main() -> None:
    data = load_feature_table(FEATURE_TABLE)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(build_report(data), encoding="utf-8")
    print(f"Wrote maintenance alert report: {REPORT}")


if __name__ == "__main__":
    main()
