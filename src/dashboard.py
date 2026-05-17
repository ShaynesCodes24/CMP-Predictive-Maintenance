from pathlib import Path
from html import escape

import altair as alt
import pandas as pd
import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
FEATURE_TABLE = ROOT / "data" / "processed" / "cmp_feature_table.csv"
ALERT_TABLE = ROOT / "data" / "processed" / "cmp_alerts.csv"
TOOL_SUMMARY = ROOT / "reports" / "tool_health_summary.csv"
MODEL_PREDICTIONS = ROOT / "data" / "processed" / "cmp_model_predictions.csv"
FEATURE_IMPORTANCE = ROOT / "reports" / "model_feature_importance.csv"
MODEL_METRICS = ROOT / "reports" / "model_metrics.md"

RISK_COLORS = {
    "normal": "#2a9d8f",
    "low": "#8ab17d",
    "medium": "#e9c46a",
    "high": "#d62828",
}

STATE_COLORS = {
    "normal": "#2a9d8f",
    "warning": "#f4a261",
    "maintenance_needed": "#d62828",
}

ALERT_LABELS = {
    "alert_motor_vibration": "High vibration with elevated platen current",
    "alert_slurry_flow": "Low slurry flow",
    "alert_pad_wear": "Pad wear with elevated vibration",
    "alert_pressure_drift": "Downforce pressure outside normal range",
    "alert_alarm_burst": "Multiple alarms in the same hour",
    "alert_process_drift": "Removal-rate or process-drift abnormality",
}

ROOT_CAUSE_CHECKS = {
    "Pad wear": [
        "Inspect pad condition and remaining life",
        "Review conditioner performance",
        "Compare removal-rate trend against baseline",
    ],
    "Slurry delivery issue": [
        "Verify slurry flow rate against the expected range",
        "Inspect delivery lines, filters, and flow sensors",
        "Check for recent slurry alarms or flow instability",
    ],
    "Retaining ring wear": [
        "Check retaining ring remaining life",
        "Inspect carrier stability and contact pattern",
        "Review edge-removal behavior if available",
    ],
    "Vibration or bearing issue": [
        "Check vibration sensor reading against previous runs",
        "Inspect platen drive and bearing condition",
        "Review motor current trend and tool event history",
    ],
    "Pressure or carrier control issue": [
        "Verify downforce pressure control",
        "Check pressure sensor calibration",
        "Review carrier load and recipe setpoints",
    ],
    "Unknown or process drift": [
        "Review recent alarm history",
        "Compare current run data with the last stable run",
        "Escalate to engineering if drift continues after basic checks",
    ],
}


st.set_page_config(
    page_title="CMP Tool Health Dashboard",
    page_icon="CMP",
    layout="wide",
)

st.markdown(
    """
    <style>
    :root {
        --cmp-bg: #0f141b;
        --cmp-panel: #171d26;
        --cmp-panel-soft: #1f2732;
        --cmp-border: #2b3542;
        --cmp-text: #eef2f6;
        --cmp-muted: #aab4c0;
        --cmp-accent: #39a7a5;
        --cmp-accent-soft: rgba(57, 167, 165, 0.14);
        --cmp-good: #2a9d8f;
        --cmp-warn: #e9c46a;
        --cmp-danger: #d62828;
        --cmp-shadow: 0 18px 44px rgba(0, 0, 0, 0.28);
    }

    .stApp {
        background:
            radial-gradient(circle at 8% 0%, rgba(57, 167, 165, 0.16), transparent 27rem),
            radial-gradient(circle at 86% 8%, rgba(233, 196, 106, 0.09), transparent 22rem),
            linear-gradient(180deg, #111821 0%, #0f141b 46%, #0a0e13 100%);
        color: var(--cmp-text);
    }

    section[data-testid="stSidebar"] {
        background: #171b23;
        border-right: 1px solid var(--cmp-border);
    }

    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stMarkdown {
        color: var(--cmp-text);
    }

    div[data-testid="stMetric"] {
        background: linear-gradient(180deg, rgba(31, 39, 50, 0.96), rgba(22, 28, 37, 0.96));
        border: 1px solid var(--cmp-border);
        border-radius: 8px;
        padding: 1rem 1.05rem;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.18);
    }

    div[data-testid="stMetricLabel"] {
        color: var(--cmp-muted);
        font-weight: 700;
    }

    div[data-testid="stMetricValue"] {
        color: var(--cmp-text);
        font-weight: 800;
    }

    .cmp-hero {
        border: 1px solid var(--cmp-border);
        border-radius: 8px;
        padding: 1.45rem 1.55rem;
        background:
            linear-gradient(100deg, rgba(57, 167, 165, 0.18), rgba(45, 57, 73, 0.32)),
            linear-gradient(180deg, rgba(25, 32, 43, 0.94), rgba(18, 24, 32, 0.94));
        margin-bottom: 1.05rem;
        box-shadow: var(--cmp-shadow);
    }

    .cmp-eyebrow {
        color: #70d6d3;
        font-size: 0.78rem;
        font-weight: 800;
        letter-spacing: 0;
        text-transform: uppercase;
        margin-bottom: 0.25rem;
    }

    .cmp-title {
        color: var(--cmp-text);
        font-size: 2.05rem;
        font-weight: 850;
        line-height: 1.12;
        margin: 0;
    }

    .cmp-subtitle {
        color: var(--cmp-muted);
        font-size: 1rem;
        margin-top: 0.5rem;
        max-width: 72rem;
    }

    .cmp-section-label {
        color: #b7e7e5;
        font-weight: 800;
        text-transform: uppercase;
        font-size: 0.76rem;
        margin: 1.25rem 0 0.5rem;
    }

    .cmp-action {
        border-left: 4px solid var(--cmp-accent);
        border-top: 1px solid rgba(57, 167, 165, 0.22);
        border-right: 1px solid rgba(57, 167, 165, 0.22);
        border-bottom: 1px solid rgba(57, 167, 165, 0.22);
        background:
            linear-gradient(90deg, rgba(57, 167, 165, 0.18), rgba(57, 167, 165, 0.07)),
            rgba(18, 24, 32, 0.94);
        border-radius: 8px;
        padding: 0.9rem 1rem;
        color: var(--cmp-text);
        margin-bottom: 1rem;
        box-shadow: 0 12px 28px rgba(0, 0, 0, 0.18);
    }

    .cmp-decision-card {
        border: 1px solid var(--cmp-border);
        border-radius: 8px;
        background:
            linear-gradient(180deg, rgba(31, 39, 50, 0.98), rgba(17, 23, 31, 0.98));
        padding: 1rem 1.05rem;
        min-height: 11.25rem;
        box-shadow: var(--cmp-shadow);
        margin-bottom: 1rem;
    }

    .cmp-decision-title {
        color: var(--cmp-text);
        font-weight: 850;
        font-size: 1.05rem;
        margin-bottom: 0.5rem;
    }

    .cmp-decision-body {
        color: var(--cmp-muted);
        font-size: 0.92rem;
        line-height: 1.48;
    }

    .cmp-list {
        margin: 0.35rem 0 0;
        padding-left: 1.15rem;
        color: var(--cmp-muted);
    }

    .cmp-list li {
        margin-bottom: 0.28rem;
    }

    .cmp-handoff {
        border-left: 4px solid var(--cmp-warn);
        border-top: 1px solid rgba(233, 196, 106, 0.28);
        border-right: 1px solid rgba(233, 196, 106, 0.28);
        border-bottom: 1px solid rgba(233, 196, 106, 0.28);
        border-radius: 8px;
        background: rgba(233, 196, 106, 0.08);
        color: var(--cmp-text);
        padding: 1rem 1.05rem;
        line-height: 1.55;
    }

    .cmp-tool-card {
        background: linear-gradient(180deg, rgba(31, 39, 50, 0.98), rgba(18, 24, 32, 0.98));
        border: 1px solid var(--cmp-border);
        border-radius: 8px;
        padding: 1rem;
        min-height: 17.3rem;
        box-shadow: var(--cmp-shadow);
    }

    .cmp-tool-card-header {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 0.75rem;
        margin-bottom: 0.7rem;
    }

    .cmp-tool-id {
        color: var(--cmp-text);
        font-size: 1rem;
        font-weight: 800;
    }

    .cmp-rule-points {
        color: var(--cmp-text);
        font-size: 2rem;
        line-height: 1.1;
        font-weight: 850;
        margin: 0.1rem 0 0.55rem;
    }

    .cmp-card-note {
        color: var(--cmp-muted);
        font-size: 0.78rem;
        margin-bottom: 0.8rem;
    }

    .cmp-card-row {
        display: flex;
        justify-content: space-between;
        gap: 0.75rem;
        color: var(--cmp-muted);
        font-size: 0.86rem;
        padding: 0.18rem 0;
        border-bottom: 1px solid rgba(170, 180, 192, 0.10);
    }

    .cmp-card-row span:last-child {
        color: var(--cmp-text);
        font-weight: 700;
    }

    .cmp-badge {
        display: inline-block;
        color: white;
        padding: 0.22rem 0.58rem;
        border-radius: 0.25rem;
        font-weight: 800;
        font-size: 0.78rem;
    }

    .cmp-command-grid,
    .cmp-kpi-grid {
        display: grid;
        gap: 1rem;
        margin-bottom: 1.05rem;
    }

    .cmp-command-grid {
        grid-template-columns: minmax(18rem, 1.25fr) repeat(3, minmax(11rem, 0.75fr));
    }

    .cmp-kpi-grid {
        grid-template-columns: repeat(4, minmax(0, 1fr));
    }

    .cmp-command-card,
    .cmp-kpi-card {
        border: 1px solid var(--cmp-border);
        border-radius: 8px;
        background:
            linear-gradient(180deg, rgba(31, 39, 50, 0.98), rgba(17, 23, 31, 0.98));
        box-shadow: var(--cmp-shadow);
        margin-bottom: 0.85rem;
    }

    .cmp-command-card {
        padding: 1rem 1.05rem;
        min-height: 8.25rem;
    }

    .cmp-kpi-card {
        padding: 0.95rem 1rem;
        min-height: 7rem;
    }

    .cmp-command-title,
    .cmp-kpi-label {
        color: var(--cmp-muted);
        font-size: 0.78rem;
        font-weight: 800;
        text-transform: uppercase;
    }

    .cmp-command-value {
        color: var(--cmp-text);
        font-size: 1.55rem;
        line-height: 1.15;
        font-weight: 850;
        margin-top: 0.5rem;
    }

    .cmp-command-caption,
    .cmp-kpi-caption {
        color: var(--cmp-muted);
        font-size: 0.82rem;
        margin-top: 0.45rem;
    }

    .cmp-kpi-value {
        color: var(--cmp-text);
        font-size: 2rem;
        line-height: 1.05;
        font-weight: 850;
        margin-top: 0.45rem;
        overflow-wrap: anywhere;
    }

    .cmp-kpi-date {
        font-size: 1.6rem;
    }

    .cmp-accent-good {
        border-top: 3px solid var(--cmp-good);
    }

    .cmp-accent-warn {
        border-top: 3px solid var(--cmp-warn);
    }

    .cmp-accent-danger {
        border-top: 3px solid var(--cmp-danger);
    }

    .cmp-accent-teal {
        border-top: 3px solid var(--cmp-accent);
    }

    .cmp-progress {
        margin: 0.65rem 0 0.75rem;
    }

    .cmp-progress-top {
        display: flex;
        justify-content: space-between;
        gap: 0.75rem;
        color: var(--cmp-muted);
        font-size: 0.78rem;
        font-weight: 700;
        margin-bottom: 0.25rem;
    }

    .cmp-progress-value {
        color: var(--cmp-text);
    }

    .cmp-progress-track {
        height: 0.45rem;
        background: rgba(170, 180, 192, 0.14);
        border-radius: 999px;
        overflow: hidden;
    }

    .cmp-progress-fill {
        height: 100%;
        border-radius: inherit;
    }

    div[data-testid="stDataFrame"] {
        border: 1px solid var(--cmp-border);
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 14px 34px rgba(0, 0, 0, 0.18);
    }

    div[data-testid="stVegaLiteChart"] {
        background: rgba(23, 29, 38, 0.84);
        border: 1px solid var(--cmp-border);
        border-radius: 8px;
        padding: 0.55rem;
        box-shadow: 0 14px 34px rgba(0, 0, 0, 0.18);
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1500px;
    }

    @media (max-width: 1100px) {
        .cmp-command-grid,
        .cmp-kpi-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
    }

    @media (max-width: 760px) {
        .cmp-command-grid,
        .cmp-kpi-grid {
            grid-template-columns: 1fr;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data
def load_csv(
    path: Path,
    file_mtime: float,
    parse_dates: list[str] | None = None,
) -> pd.DataFrame:
    if not path.exists():
        st.error(f"Missing required file: {path}")
        st.stop()
    return pd.read_csv(path, parse_dates=parse_dates)


@st.cache_data
def load_text(path: Path) -> str:
    if not path.exists():
        return "Model metrics report has not been generated yet."
    return path.read_text(encoding="utf-8")


def risk_badge(risk_level: str) -> str:
    color = RISK_COLORS.get(risk_level, "#6c757d")
    return (
        f"<span class='cmp-badge' style='background:{color};'>"
        f"{risk_level.upper()}</span>"
    )


def section_label(text: str) -> None:
    st.markdown(f"<div class='cmp-section-label'>{text}</div>", unsafe_allow_html=True)


def accent_class(level: str) -> str:
    if level in {"high", "maintenance_needed"}:
        return "cmp-accent-danger"
    if level in {"medium", "warning"}:
        return "cmp-accent-warn"
    if level in {"normal", "low"}:
        return "cmp-accent-good"
    return "cmp-accent-teal"


def progress_color(value: float) -> str:
    if value < 30:
        return "var(--cmp-danger)"
    if value < 55:
        return "var(--cmp-warn)"
    return "var(--cmp-good)"


def life_bar(label: str, value: float) -> str:
    bounded = max(0, min(float(value), 100))
    return (
        '<div class="cmp-progress">'
        '<div class="cmp-progress-top">'
        f"<span>{escape(label)}</span>"
        f'<span class="cmp-progress-value">{bounded:.1f}%</span>'
        "</div>"
        '<div class="cmp-progress-track">'
        f'<div class="cmp-progress-fill" style="width:{bounded:.1f}%; background:{progress_color(bounded)};"></div>'
        "</div>"
        "</div>"
    )


def kpi_card(title: str, value: str, caption: str, accent: str = "teal") -> str:
    size_class = " cmp-kpi-date" if len(value) > 10 else ""
    return f"""
    <div class="cmp-kpi-card cmp-accent-{accent}">
        <div class="cmp-kpi-label">{escape(title)}</div>
        <div class="cmp-kpi-value{size_class}">{escape(value)}</div>
        <div class="cmp-kpi-caption">{escape(caption)}</div>
    </div>
    """


def command_card(title: str, value: str, caption: str, accent: str = "teal") -> str:
    return f"""
    <div class="cmp-command-card cmp-accent-{accent}">
        <div class="cmp-command-title">{escape(title)}</div>
        <div class="cmp-command-value">{escape(value)}</div>
        <div class="cmp-command-caption">{escape(caption)}</div>
    </div>
    """


def card_grid(cards: list[str], class_name: str) -> None:
    columns = st.columns(len(cards))
    for column, card in zip(columns, cards):
        with column:
            st.markdown(card, unsafe_allow_html=True)


def active_alerts(row: pd.Series) -> list[str]:
    return [label for column, label in ALERT_LABELS.items() if bool(row.get(column, False))]


def format_action_list(action_text: str) -> list[str]:
    return [action.strip() for action in str(action_text).split(";") if action.strip()]


def decision_card(title: str, items: list[str]) -> str:
    list_items = "".join(f"<li>{escape(item)}</li>" for item in items)
    return f"""
    <div class="cmp-decision-card">
        <div class="cmp-decision-title">{escape(title)}</div>
        <div class="cmp-decision-body"><ul class="cmp-list">{list_items}</ul></div>
    </div>
    """


def urgency_text(row: pd.Series) -> tuple[str, str]:
    risk_level = str(row["rule_risk_level"])
    state = str(row["maintenance_state"])
    if risk_level == "high" or state == "maintenance_needed":
        return (
            "High risk - inspect before next production run",
            "Possible wafer defects, removal-rate drift, tool downtime, scrap risk, and lower yield.",
        )
    if risk_level == "medium" or state == "warning":
        return (
            "Medium risk - review during this shift",
            "Trend is abnormal enough to justify technician review before the condition becomes a hard fault.",
        )
    if risk_level == "low":
        return (
            "Low risk - monitor next runs",
            "Early symptom is present, but current evidence does not require immediate downtime.",
        )
    return (
        "Normal - continue monitoring",
        "Tool is inside expected synthetic operating bands on the latest snapshot.",
    )


def root_cause_probabilities(row: pd.Series) -> pd.DataFrame:
    scores = {
        "Pad wear": 0.6,
        "Slurry delivery issue": 0.6,
        "Retaining ring wear": 0.5,
        "Vibration or bearing issue": 0.5,
        "Pressure or carrier control issue": 0.45,
        "Unknown or process drift": 0.35,
    }

    if bool(row.get("alert_pad_wear", False)):
        scores["Pad wear"] += 3.6
    if float(row.get("pad_life_pct", 0)) >= 85:
        scores["Pad wear"] += 1.5
    if bool(row.get("alert_slurry_flow", False)):
        scores["Slurry delivery issue"] += 3.4
    if float(row.get("slurry_flow_rate", 999)) < 200:
        scores["Slurry delivery issue"] += 1.1
    if float(row.get("retaining_ring_life_pct", 0)) >= 85:
        scores["Retaining ring wear"] += 2.8
    if bool(row.get("alert_motor_vibration", False)):
        scores["Vibration or bearing issue"] += 3.2
    if float(row.get("vibration", 0)) >= 0.65:
        scores["Vibration or bearing issue"] += 1.3
    if bool(row.get("alert_pressure_drift", False)):
        scores["Pressure or carrier control issue"] += 3.0
    if bool(row.get("alert_alarm_burst", False)):
        scores["Unknown or process drift"] += 1.2
    if bool(row.get("alert_process_drift", False)):
        scores["Unknown or process drift"] += 2.4
        scores["Pad wear"] += 0.8
        scores["Slurry delivery issue"] += 0.6

    total = sum(scores.values())
    probabilities = [
        {"Possible Root Cause": cause, "Probability": round(score / total * 100, 1)}
        for cause, score in scores.items()
    ]
    return pd.DataFrame(probabilities).sort_values("Probability", ascending=False)


def likely_causes(probability_table: pd.DataFrame, limit: int = 5) -> list[str]:
    return [
        f"{row['Possible Root Cause']} ({row['Probability']:.1f}%)"
        for _, row in probability_table.head(limit).iterrows()
    ]


def recommended_checks(probability_table: pd.DataFrame, row: pd.Series) -> list[str]:
    checks: list[str] = []
    for cause in probability_table.head(3)["Possible Root Cause"]:
        for check in ROOT_CAUSE_CHECKS[cause]:
            if check not in checks:
                checks.append(check)

    for action in format_action_list(row["recommended_action"]):
        if action not in checks:
            checks.append(action)
    return checks[:8]


def shift_handoff(tool_id: str, row: pd.Series, probability_table: pd.DataFrame) -> str:
    urgency, impact = urgency_text(row)
    top_causes = ", ".join(probability_table.head(3)["Possible Root Cause"].tolist())
    active = active_alerts(row)
    evidence = ", ".join(active) if active else "no active rule alerts on the latest reading"
    return (
        f"Shift Handoff - {tool_id}: Latest tool state is {row['rule_risk_level']} risk "
        f"with {int(row['rule_risk_points'])} rule points. Evidence shows {evidence}. "
        f"Most likely causes are {top_causes}. {urgency}. {impact}"
    )


def maintenance_ticket(tool_id: str, row: pd.Series, probability_table: pd.DataFrame) -> str:
    urgency, impact = urgency_text(row)
    top_cause = probability_table.iloc[0]
    checks = recommended_checks(probability_table, row)
    evidence = active_alerts(row)
    evidence_text = "\n".join(f"- {item}" for item in evidence) or "- No active latest-row rule alerts"
    checks_text = "\n".join(f"- {item}" for item in checks)

    return f"""# Maintenance Ticket - {tool_id}

## Priority
{urgency}

## Tool Snapshot
- Timestamp: {row['timestamp']}
- Maintenance state: {row['maintenance_state']}
- Rule risk level: {row['rule_risk_level']}
- Rule risk points: {int(row['rule_risk_points'])}
- Vibration: {row['vibration']:.3f}
- Slurry flow: {row['slurry_flow_rate']:.2f}
- Wafer removal rate: {row['wafer_removal_rate']:.2f}
- Process drift: {row['process_drift_nm']:.2f} nm
- Pad life used: {row['pad_life_pct']:.1f}%
- Retaining ring life used: {row['retaining_ring_life_pct']:.1f}%
- Alarm count: {int(row['alarm_count'])}

## Most Likely Root Cause
{top_cause['Possible Root Cause']} ({top_cause['Probability']:.1f}% estimated probability)

## Evidence
{evidence_text}

## Recommended Technician Checks
{checks_text}

## Business Impact If Ignored
{impact}

## Closeout Notes
- Record technician action taken.
- Compare next-run risk, vibration, slurry flow, removal rate, and process drift against this snapshot.
- Escalate if abnormal trend continues after basic maintenance checks.
"""


def assistant_response(question: str, tool_id: str, row: pd.Series, probability_table: pd.DataFrame) -> str:
    urgency, impact = urgency_text(row)
    checks = recommended_checks(probability_table, row)[:5]
    top_two = probability_table.head(2)["Possible Root Cause"].tolist()
    prompt_context = f" The question mentions: {question.strip()}" if question.strip() else ""
    return (
        f"For {tool_id}, the most likely issue is {top_two[0].lower()} or "
        f"{top_two[1].lower()}. First check {checks[0].lower()}, then {checks[1].lower()}. "
        f"Current urgency: {urgency}. {impact}{prompt_context}"
    )


def maintenance_before_after(data: pd.DataFrame, tool_id: str) -> pd.DataFrame:
    tool_data = data[data["tool_id"] == tool_id].sort_values("timestamp").reset_index(drop=True)
    event_indices = tool_data.index[tool_data["maintenance_event"] == 1].tolist()
    if not event_indices:
        return pd.DataFrame()

    event_index = event_indices[-1]
    before_index = max(event_index - 1, 0)
    after_index = min(event_index + 3, len(tool_data) - 1)
    before = tool_data.loc[before_index]
    after = tool_data.loc[after_index]
    return pd.DataFrame(
        [
            {
                "Phase": "Before maintenance",
                "Timestamp": before["timestamp"],
                "Risk": before["rule_risk_level"],
                "Rule points": int(before["rule_risk_points"]),
                "Vibration": before["vibration"],
                "Slurry flow": before["slurry_flow_rate"],
                "Removal rate": before["wafer_removal_rate"],
                "Process drift": before["process_drift_nm"],
                "Pad life used": before["pad_life_pct"],
                "Ring life used": before["retaining_ring_life_pct"],
            },
            {
                "Phase": "After maintenance",
                "Timestamp": after["timestamp"],
                "Risk": after["rule_risk_level"],
                "Rule points": int(after["rule_risk_points"]),
                "Vibration": after["vibration"],
                "Slurry flow": after["slurry_flow_rate"],
                "Removal rate": after["wafer_removal_rate"],
                "Process drift": after["process_drift_nm"],
                "Pad life used": after["pad_life_pct"],
                "Ring life used": after["retaining_ring_life_pct"],
            },
        ]
    )


def estimate_pm_calendar(data: pd.DataFrame) -> pd.DataFrame:
    rows = []
    sorted_data = data.sort_values(["tool_id", "timestamp"]).copy()

    for tool_id, tool_data in sorted_data.groupby("tool_id", sort=True):
        latest = tool_data.tail(1).iloc[0]
        recent = tool_data.tail(24)
        pad_rate = recent["pad_hours"].diff().clip(lower=0).mean()
        ring_rate = recent["retaining_ring_hours"].diff().clip(lower=0).mean()
        pad_rate = float(pad_rate) if pd.notna(pad_rate) and pad_rate > 0 else 0.55
        ring_rate = float(ring_rate) if pd.notna(ring_rate) and ring_rate > 0 else 0.45

        pad_hours_remaining = max(0.0, 400.0 - float(latest["pad_hours"]))
        ring_hours_remaining = max(0.0, 300.0 - float(latest["retaining_ring_hours"]))
        pad_due_hours = pad_hours_remaining / pad_rate
        ring_due_hours = ring_hours_remaining / ring_rate
        next_due_hours = min(pad_due_hours, ring_due_hours)
        next_item = "Pad replacement" if pad_due_hours <= ring_due_hours else "Retaining ring replacement"
        next_due_time = latest["timestamp"] + pd.to_timedelta(next_due_hours, unit="h")

        if str(latest["rule_risk_level"]) == "high" or next_due_hours <= 12:
            priority = "Inspect before next production run"
        elif str(latest["rule_risk_level"]) == "medium" or next_due_hours <= 48:
            priority = "Schedule during this shift"
        elif next_due_hours <= 120:
            priority = "Plan in next PM window"
        else:
            priority = "Monitor"

        rows.append(
            {
                "Tool": tool_id,
                "Next PM Item": next_item,
                "Estimated Due": next_due_time,
                "Hours Until Due": round(next_due_hours, 1),
                "Pad Life Used": round(float(latest["pad_life_pct"]), 1),
                "Ring Life Used": round(float(latest["retaining_ring_life_pct"]), 1),
                "Current Risk": latest["rule_risk_level"],
                "Priority": priority,
            }
        )

    return pd.DataFrame(rows).sort_values(["Hours Until Due", "Tool"])


def scenario_risk_assessment(
    vibration: float,
    slurry_flow: float,
    pad_life: float,
    ring_life: float,
    removal_rate: float,
    process_drift: float,
    alarm_count: int,
) -> dict[str, object]:
    points = 0
    reasons = []

    if vibration >= 0.70:
        points += 1
        reasons.append("High vibration")
    if slurry_flow <= 190:
        points += 1
        reasons.append("Low slurry flow")
    if pad_life >= 90 and vibration >= 0.62:
        points += 1
        reasons.append("Pad life near limit with elevated vibration")
    if ring_life >= 90:
        points += 1
        reasons.append("Retaining ring life near limit")
    if removal_rate <= 96 or process_drift >= 10:
        points += 1
        reasons.append("Removal-rate or process-drift abnormality")
    if alarm_count >= 2:
        points += 1
        reasons.append("Alarm burst")

    if points >= 3:
        level = "high"
        urgency = "Inspect before next production run"
    elif points == 2:
        level = "medium"
        urgency = "Review during this shift"
    elif points == 1:
        level = "low"
        urgency = "Monitor next runs"
    else:
        level = "normal"
        urgency = "Continue normal monitoring"

    pseudo_row = pd.Series(
        {
            "alert_pad_wear": pad_life >= 90 and vibration >= 0.62,
            "alert_slurry_flow": slurry_flow <= 190,
            "alert_motor_vibration": vibration >= 0.70,
            "alert_pressure_drift": False,
            "alert_alarm_burst": alarm_count >= 2,
            "alert_process_drift": removal_rate <= 96 or process_drift >= 10,
            "pad_life_pct": pad_life,
            "retaining_ring_life_pct": ring_life,
            "slurry_flow_rate": slurry_flow,
            "vibration": vibration,
            "recommended_action": "Run scenario-based technician checks",
        }
    )
    cause_table = root_cause_probabilities(pseudo_row)

    return {
        "points": points,
        "level": level,
        "urgency": urgency,
        "reasons": reasons or ["No abnormal scenario drivers"],
        "top_causes": cause_table.head(3),
    }


def estimate_business_impact(
    risk_level: str,
    lots_at_risk: int,
    wafers_per_lot: int,
    scrap_cost_per_wafer: float,
    downtime_hours: float,
    downtime_cost_per_hour: float,
) -> dict[str, float]:
    risk_multiplier = {
        "normal": 0.02,
        "low": 0.08,
        "medium": 0.22,
        "high": 0.45,
    }.get(risk_level, 0.10)
    wafers_at_risk = lots_at_risk * wafers_per_lot
    expected_scrap_wafers = wafers_at_risk * risk_multiplier
    expected_scrap_cost = expected_scrap_wafers * scrap_cost_per_wafer
    expected_downtime_cost = downtime_hours * downtime_cost_per_hour * risk_multiplier
    return {
        "wafers_at_risk": float(wafers_at_risk),
        "expected_scrap_wafers": expected_scrap_wafers,
        "expected_scrap_cost": expected_scrap_cost,
        "expected_downtime_cost": expected_downtime_cost,
        "total_exposure": expected_scrap_cost + expected_downtime_cost,
    }


def incident_replay_data(data: pd.DataFrame, tool_id: str) -> pd.DataFrame:
    tool_data = data[data["tool_id"] == tool_id].sort_values("timestamp").reset_index(drop=True)
    incident_rows = tool_data[tool_data["rule_risk_level"].isin(["medium", "high"])]
    if incident_rows.empty:
        incident_rows = tool_data[tool_data["rule_risk_level"] != "normal"]
    if incident_rows.empty:
        return tool_data.tail(36).copy()

    incident_index = int(incident_rows.index[-1])
    start = max(0, incident_index - 18)
    end = min(len(tool_data), incident_index + 18)
    replay = tool_data.iloc[start:end].copy()
    replay["incident_phase"] = "Early trend"
    replay.loc[replay.index >= incident_index, "incident_phase"] = "Alert active"
    replay.loc[replay["maintenance_event"] == 1, "incident_phase"] = "Maintenance reset"
    replay.loc[replay.index > incident_index + 6, "incident_phase"] = "Recovery watch"
    return replay


def incident_replay_chart(data: pd.DataFrame) -> alt.Chart:
    base = alt.Chart(data).encode(
        x=alt.X("timestamp:T", title="Incident timeline"),
        color=alt.Color(
            "incident_phase:N",
            title="Phase",
            scale=alt.Scale(
                domain=["Early trend", "Alert active", "Maintenance reset", "Recovery watch"],
                range=["#39a7a5", "#e9c46a", "#4c78a8", "#2a9d8f"],
            ),
        ),
        tooltip=[
            alt.Tooltip("timestamp:T", title="Time"),
            alt.Tooltip("rule_risk_level:N", title="Risk"),
            alt.Tooltip("vibration:Q", format=".3f"),
            alt.Tooltip("slurry_flow_rate:Q", format=".2f"),
            alt.Tooltip("wafer_removal_rate:Q", format=".2f"),
            alt.Tooltip("process_drift_nm:Q", format=".2f"),
            alt.Tooltip("incident_phase:N", title="Phase"),
        ],
    )
    vibration = base.mark_line(point=True).encode(
        y=alt.Y("vibration:Q", title="Vibration")
    )
    drift = base.mark_line(point=True, strokeDash=[5, 3]).encode(
        y=alt.Y("process_drift_nm:Q", title="Vibration / drift")
    )
    return style_chart((vibration + drift).properties(height=330))


def action_log_dataframe() -> pd.DataFrame:
    columns = [
        "timestamp",
        "tool_id",
        "technician",
        "action_taken",
        "finding",
        "risk_before",
        "risk_after",
        "next_step",
    ]
    return pd.DataFrame(st.session_state.get("technician_action_log", []), columns=columns)


def tool_card(row: pd.Series) -> str:
    risk_level = str(row["rule_risk_level"])
    state = str(row["maintenance_state"])
    return (
        f'<div class="cmp-tool-card {accent_class(risk_level)}">'
        '<div class="cmp-tool-card-header">'
        "<div>"
        f'<div class="cmp-tool-id">{escape(str(row["tool_id"]))}</div>'
        f'<div class="cmp-card-note">{escape(state.replace("_", " "))}</div>'
        "</div>"
        f"{risk_badge(risk_level)}"
        "</div>"
        f'<div class="cmp-rule-points">{int(row["rule_risk_points"])} rule points</div>'
        f'{life_bar("Pad life", row["pad_life_pct"])}'
        f'{life_bar("Ring life", row["retaining_ring_life_pct"])}'
        f'<div class="cmp-card-row"><span>Removal rate</span><span>{row["wafer_removal_rate"]:.2f}</span></div>'
        f'<div class="cmp-card-row"><span>Process drift</span><span>{row["process_drift_nm"]:.2f} nm</span></div>'
        "</div>"
    )


def style_chart(chart: alt.Chart) -> alt.Chart:
    return (
        chart.configure_view(stroke=None)
        .configure_axis(
            gridColor="rgba(170, 180, 192, 0.12)",
            labelColor="#c8d3df",
            titleColor="#aab4c0",
        )
        .configure_legend(labelColor="#c8d3df", titleColor="#aab4c0")
        .configure_title(color="#eef2f6")
        .configure(background="transparent")
    )


def sensor_chart(data: pd.DataFrame, sensor: str) -> alt.Chart:
    trend = (
        alt.Chart(data)
        .mark_line(point=False)
        .encode(
            x=alt.X("timestamp:T", title="Timestamp"),
            y=alt.Y(f"{sensor}:Q", title=sensor.replace("_", " ").title()),
            color=alt.Color("tool_id:N", title="Tool"),
            tooltip=[
                alt.Tooltip("timestamp:T", title="Time"),
                alt.Tooltip("tool_id:N", title="Tool"),
                alt.Tooltip(f"{sensor}:Q", title=sensor, format=".3f"),
                alt.Tooltip("rule_risk_level:N", title="Rule risk"),
                alt.Tooltip("maintenance_state:N", title="Label"),
            ],
        )
        .properties(height=320)
    )
    maintenance_markers = (
        alt.Chart(data[data["maintenance_event"] == 1])
        .mark_rule(color="#4c78a8", strokeDash=[5, 4], size=1.5)
        .encode(
            x=alt.X("timestamp:T"),
            tooltip=[
                alt.Tooltip("timestamp:T", title="Maintenance time"),
                alt.Tooltip("tool_id:N", title="Tool"),
            ],
        )
    )
    return style_chart(trend + maintenance_markers)


def csv_download(data: pd.DataFrame) -> bytes:
    return data.to_csv(index=False).encode("utf-8")


def maintenance_event_summary(data: pd.DataFrame) -> pd.DataFrame:
    rows = []
    sorted_data = data.sort_values(["tool_id", "timestamp"]).reset_index(drop=True)

    for _, event_row in sorted_data[sorted_data["maintenance_event"] == 1].iterrows():
        tool_data = sorted_data[sorted_data["tool_id"] == event_row["tool_id"]]
        previous_rows = tool_data[tool_data["timestamp"] < event_row["timestamp"]]
        previous_row = previous_rows.tail(1)
        before = previous_row.iloc[0] if not previous_row.empty else event_row

        rows.append(
            {
                "tool_id": event_row["tool_id"],
                "maintenance_timestamp": event_row["timestamp"],
                "state_before_pm": before["maintenance_state"],
                "risk_before_pm": before["rule_risk_level"],
                "pad_life_before_pm": before["pad_life_pct"],
                "pad_life_after_pm": event_row["pad_life_pct"],
                "ring_life_before_pm": before["retaining_ring_life_pct"],
                "ring_life_after_pm": event_row["retaining_ring_life_pct"],
                "process_drift_after_pm": event_row["process_drift_nm"],
            }
        )

    return pd.DataFrame(rows)


features = load_csv(
    FEATURE_TABLE,
    FEATURE_TABLE.stat().st_mtime,
    parse_dates=["timestamp"],
)
alerts = load_csv(ALERT_TABLE, ALERT_TABLE.stat().st_mtime, parse_dates=["timestamp"])
summary = load_csv(TOOL_SUMMARY, TOOL_SUMMARY.stat().st_mtime, parse_dates=["timestamp"])
predictions = load_csv(
    MODEL_PREDICTIONS,
    MODEL_PREDICTIONS.stat().st_mtime,
    parse_dates=["timestamp"],
)
importance = load_csv(FEATURE_IMPORTANCE, FEATURE_IMPORTANCE.stat().st_mtime)
metrics_text = load_text(MODEL_METRICS)

if "technician_action_log" not in st.session_state:
    st.session_state.technician_action_log = []

st.markdown(
    """
    <div class="cmp-hero">
        <div class="cmp-eyebrow">CMP predictive maintenance</div>
        <h1 class="cmp-title">Tool Health Dashboard</h1>
        <div class="cmp-subtitle">
            Monitor CMP tool risk, maintenance reset behavior, sensor drift, model confidence,
            and recommended technician checks from one operations-focused view.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

tool_options = sorted(features["tool_id"].unique())
selected_tools = st.sidebar.multiselect(
    "Tools",
    options=tool_options,
    default=tool_options,
)
risk_options = ["normal", "low", "medium", "high"]
selected_risks = st.sidebar.multiselect(
    "Rule risk levels",
    options=risk_options,
    default=risk_options,
)
sensor_options = [
    "platen_motor_current",
    "carrier_motor_current",
    "slurry_flow_rate",
    "downforce_pressure",
    "vibration",
    "temperature_c",
    "wafer_removal_rate",
    "process_drift_nm",
    "pad_hours",
    "retaining_ring_hours",
]
selected_sensor = st.sidebar.selectbox("Sensor trend", sensor_options, index=0)

filtered = features[
    features["tool_id"].isin(selected_tools)
    & features["rule_risk_level"].isin(selected_risks)
].copy()
filtered_alerts = alerts[alerts["tool_id"].isin(selected_tools)].copy()
filtered_summary = summary[summary["tool_id"].isin(selected_tools)].copy()
filtered_predictions = predictions[predictions["tool_id"].isin(selected_tools)].copy()

latest_timestamp = features["timestamp"].max()
high_risk_tools = summary.loc[summary["rule_risk_level"] == "high", "tool_id"].tolist()
current_state_counts = summary["maintenance_state"].value_counts()
latest_non_normal = summary[summary["rule_risk_level"] != "normal"].sort_values(
    "rule_risk_points",
    ascending=False,
)
latest_action = (
    latest_non_normal.iloc[0]["recommended_action"]
    if not latest_non_normal.empty
    else "Continue normal monitoring"
)
top_priority = summary.sort_values(
    ["rule_risk_points", "process_drift_nm"],
    ascending=[False, False],
).iloc[0]
priority_label = (
    "No open priority"
    if latest_non_normal.empty
    else str(top_priority["tool_id"])
)
priority_caption = (
    "All tools currently normal"
    if latest_non_normal.empty
    else f"{int(top_priority['rule_risk_points'])} rule points, {top_priority['rule_risk_level']} risk"
)
priority_accent = (
    "good"
    if latest_non_normal.empty
    else accent_class(str(top_priority["rule_risk_level"])).replace("cmp-accent-", "")
)
fleet_status = (
    "Maintenance attention required"
    if int(current_state_counts.get("maintenance_needed", 0)) > 0
    else "Warning review active"
    if int(current_state_counts.get("warning", 0)) > 0
    else "Fleet stable"
)
fleet_accent = (
    "danger"
    if int(current_state_counts.get("maintenance_needed", 0)) > 0
    else "warn"
    if int(current_state_counts.get("warning", 0)) > 0
    else "good"
)

with st.sidebar.expander("Downloads", expanded=True):
    st.download_button(
        "Tool summary CSV",
        data=csv_download(filtered_summary),
        file_name="tool_health_summary.csv",
        mime="text/csv",
    )
    st.download_button(
        "Recent alerts CSV",
        data=csv_download(filtered_alerts.sort_values("timestamp", ascending=False)),
        file_name="cmp_recent_alerts.csv",
        mime="text/csv",
    )
    st.download_button(
        "Model predictions CSV",
        data=csv_download(filtered_predictions),
        file_name="cmp_model_predictions.csv",
        mime="text/csv",
    )

section_label("Operations Command Center")
card_grid(
    [
        command_card(
            "Fleet status",
            fleet_status,
            f"{features['tool_id'].nunique()} tools monitored from synthetic CMP sensor data",
            fleet_accent,
        ),
        command_card(
            "Priority tool",
            priority_label,
            priority_caption,
            priority_accent,
        ),
        command_card(
            "Last update",
            latest_timestamp.strftime("%b %d, %Y"),
            latest_timestamp.strftime("%I:%M %p sensor snapshot"),
            "teal",
        ),
        command_card(
            "Action queue",
            str(len(alerts)),
            "Rows available for technician review",
            "warn" if len(alerts) else "good",
        ),
    ],
    "cmp-command-grid",
)

section_label("Fleet Snapshot")
card_grid(
    [
        kpi_card("Normal tools", str(int(current_state_counts.get("normal", 0))), "Running inside expected bands", "good"),
        kpi_card("Warning tools", str(int(current_state_counts.get("warning", 0))), "Needs closer trend review", "warn"),
        kpi_card(
            "Maintenance needed",
            str(int(current_state_counts.get("maintenance_needed", 0))),
            "Requires technician action",
            "danger",
        ),
        kpi_card("PM events", str(int(features["maintenance_event"].sum())), "Simulated reset history", "teal"),
    ],
    "cmp-kpi-grid",
)
st.markdown(
    f"<div class='cmp-action'><strong>Latest recommended action:</strong> {latest_action}</div>",
    unsafe_allow_html=True,
)

st.divider()

section_label("Current Tool Priority")
card_cols = st.columns(max(len(filtered_summary), 1))
for column, (_, row) in zip(card_cols, filtered_summary.sort_values("tool_id").iterrows()):
    with column:
        st.markdown(tool_card(row), unsafe_allow_html=True)

section_label("Recommended Technician Checks")
action_view = filtered_summary[
    [
        "tool_id",
        "rule_risk_level",
        "maintenance_state",
        "wafer_removal_rate",
        "process_drift_nm",
        "recommended_action",
    ]
].sort_values(["rule_risk_level", "tool_id"], ascending=[True, True])
st.dataframe(action_view, width="stretch", hide_index=True)

st.divider()

section_label("Fab Command Center")
impact_tab, simulator_tab, replay_tab, executive_tab = st.tabs(
    [
        "Downtime And Scrap Impact",
        "Scenario Simulator",
        "Incident Replay",
        "Executive Summary",
    ]
)

with impact_tab:
    impact_col_a, impact_col_b = st.columns([1, 1])
    with impact_col_a:
        impact_tool = st.selectbox("Impact tool", options=tool_options, index=0, key="impact_tool")
        impact_row = summary[summary["tool_id"] == impact_tool].iloc[0]
        lots_at_risk = st.slider("Lots at risk", min_value=1, max_value=40, value=6)
        wafers_per_lot = st.slider("Wafers per lot", min_value=1, max_value=50, value=25)
        scrap_cost = st.number_input("Scrap cost per wafer ($)", min_value=0, value=850, step=50)
    with impact_col_b:
        downtime_hours = st.slider("Potential downtime hours", min_value=0.0, max_value=48.0, value=8.0, step=0.5)
        downtime_cost = st.number_input("Downtime cost per hour ($)", min_value=0, value=2500, step=250)
        impact = estimate_business_impact(
            str(impact_row["rule_risk_level"]),
            lots_at_risk,
            wafers_per_lot,
            float(scrap_cost),
            downtime_hours,
            float(downtime_cost),
        )
        st.markdown(
            decision_card(
                "Estimated exposure if ignored",
                [
                    f"Wafers at risk: {impact['wafers_at_risk']:.0f}",
                    f"Expected scrap wafers: {impact['expected_scrap_wafers']:.1f}",
                    f"Expected scrap cost: ${impact['expected_scrap_cost']:,.0f}",
                    f"Expected downtime cost: ${impact['expected_downtime_cost']:,.0f}",
                    f"Total exposure: ${impact['total_exposure']:,.0f}",
                ],
            ),
            unsafe_allow_html=True,
        )

with simulator_tab:
    sim_col_a, sim_col_b = st.columns([1, 1])
    with sim_col_a:
        base_tool = st.selectbox("Scenario baseline tool", options=tool_options, index=0, key="scenario_tool")
        base_row = summary[summary["tool_id"] == base_tool].iloc[0]
        sim_vibration = st.slider("Vibration", 0.20, 1.20, float(base_row["vibration"]), 0.01)
        sim_slurry = st.slider("Slurry flow", 150.0, 230.0, float(base_row["slurry_flow_rate"]), 0.5)
        sim_pad = st.slider("Pad life used (%)", 0.0, 100.0, float(base_row["pad_life_pct"]), 0.5)
        sim_ring = st.slider("Retaining ring life used (%)", 0.0, 100.0, float(base_row["retaining_ring_life_pct"]), 0.5)
    with sim_col_b:
        sim_removal = st.slider("Wafer removal rate", 88.0, 112.0, float(base_row["wafer_removal_rate"]), 0.1)
        sim_drift = st.slider("Process drift (nm)", 0.0, 20.0, float(base_row["process_drift_nm"]), 0.1)
        sim_alarms = st.slider("Alarm count", 0, 5, int(base_row["alarm_count"]))
        scenario = scenario_risk_assessment(
            sim_vibration,
            sim_slurry,
            sim_pad,
            sim_ring,
            sim_removal,
            sim_drift,
            sim_alarms,
        )
        top_causes = [
            f"{row['Possible Root Cause']} ({row['Probability']:.1f}%)"
            for _, row in scenario["top_causes"].iterrows()
        ]
        st.markdown(
            decision_card(
                f"Scenario result: {str(scenario['level']).upper()} risk",
                [
                    f"Rule points: {scenario['points']}",
                    f"Urgency: {scenario['urgency']}",
                    "Drivers: " + ", ".join(scenario["reasons"]),
                    "Likely causes: " + ", ".join(top_causes),
                ],
            ),
            unsafe_allow_html=True,
        )

with replay_tab:
    replay_tool = st.selectbox("Replay tool", options=tool_options, index=0, key="replay_tool")
    replay = incident_replay_data(features, replay_tool)
    if replay.empty:
        st.info("No data available for incident replay.")
    else:
        st.altair_chart(incident_replay_chart(replay), width="stretch")
        replay_summary = replay[
            [
                "timestamp",
                "tool_id",
                "incident_phase",
                "rule_risk_level",
                "rule_risk_points",
                "vibration",
                "slurry_flow_rate",
                "wafer_removal_rate",
                "process_drift_nm",
                "maintenance_event",
                "recommended_action",
            ]
        ].sort_values("timestamp", ascending=False)
        st.dataframe(replay_summary, width="stretch", hide_index=True)

with executive_tab:
    pm_calendar = estimate_pm_calendar(features)
    open_priorities = summary[summary["rule_risk_level"] != "normal"].sort_values(
        "rule_risk_points",
        ascending=False,
    )
    if open_priorities.empty:
        status_line = "All tools are currently normal on the latest synthetic snapshot."
    else:
        status_line = (
            f"{len(open_priorities)} tool(s) need review. Top priority is "
            f"{open_priorities.iloc[0]['tool_id']} with {int(open_priorities.iloc[0]['rule_risk_points'])} rule points."
        )
    next_pm = pm_calendar.iloc[0]
    executive_text = (
        f"Fleet summary: {status_line} Next PM planning item is {next_pm['Next PM Item']} "
        f"for {next_pm['Tool']} around {next_pm['Estimated Due'].strftime('%b %d, %Y %I:%M %p')}. "
        "Technician workflow includes troubleshooting, root-cause probability, maintenance ticketing, "
        "action logging, cost exposure, and incident replay."
    )
    st.markdown(f"<div class='cmp-handoff'>{escape(executive_text)}</div>", unsafe_allow_html=True)
    st.download_button(
        "Download executive summary",
        data=executive_text.encode("utf-8"),
        file_name="cmp_executive_summary.txt",
        mime="text/plain",
    )

st.divider()

section_label("Technician Decision System")
technician_tool = st.selectbox(
    "Technician mode tool",
    options=tool_options,
    index=tool_options.index(str(top_priority["tool_id"])) if str(top_priority["tool_id"]) in tool_options else 0,
)
technician_row = (
    features[features["tool_id"] == technician_tool]
    .sort_values("timestamp")
    .tail(1)
    .iloc[0]
)
cause_table = root_cause_probabilities(technician_row)
urgency, business_impact = urgency_text(technician_row)

(
    troubleshooting_tab,
    cause_tab,
    maintenance_tab,
    calendar_tab,
    ticket_tab,
    action_log_tab,
    handoff_tab,
    assistant_tab,
    interview_tab,
) = st.tabs(
    [
        "Troubleshooting Mode",
        "Root Cause Probability",
        "Before vs After PM",
        "Maintenance Calendar",
        "Maintenance Ticket",
        "Technician Action Log",
        "Shift Handoff",
        "AI Maintenance Assistant",
        "Interview Explanation",
    ]
)

with troubleshooting_tab:
    st.markdown(
        f"<div class='cmp-action'><strong>Alert:</strong> {escape(technician_tool)} is "
        f"{escape(str(technician_row['rule_risk_level']).upper())} risk with "
        f"{int(technician_row['rule_risk_points'])} rule points.</div>",
        unsafe_allow_html=True,
    )
    cause_col, check_col, urgency_col = st.columns([1, 1.15, 0.95])
    with cause_col:
        st.markdown(
            decision_card("Possible causes", likely_causes(cause_table)),
            unsafe_allow_html=True,
        )
    with check_col:
        st.markdown(
            decision_card("Recommended technician checks", recommended_checks(cause_table, technician_row)),
            unsafe_allow_html=True,
        )
    with urgency_col:
        st.markdown(
            decision_card(
                "Urgency and business impact",
                [
                    urgency,
                    business_impact,
                    f"Active evidence: {', '.join(active_alerts(technician_row)) if active_alerts(technician_row) else 'No active latest-row alert'}",
                ],
            ),
            unsafe_allow_html=True,
        )

with cause_tab:
    st.dataframe(cause_table, width="stretch", hide_index=True)
    cause_chart = (
        alt.Chart(cause_table)
        .mark_bar()
        .encode(
            x=alt.X("Probability:Q", title="Estimated probability (%)"),
            y=alt.Y("Possible Root Cause:N", title="Possible root cause", sort="-x"),
            tooltip=[
                alt.Tooltip("Possible Root Cause:N"),
                alt.Tooltip("Probability:Q", format=".1f"),
            ],
        )
        .properties(height=320)
    )
    st.altair_chart(style_chart(cause_chart), width="stretch")
    st.caption("Probabilities are heuristic and based on the synthetic alert signals, sensor thresholds, and consumable life.")

with maintenance_tab:
    before_after = maintenance_before_after(features, technician_tool)
    if before_after.empty:
        st.info("No maintenance reset event is available for this tool.")
    else:
        st.dataframe(before_after, width="stretch", hide_index=True)
        st.markdown(
            "<div class='cmp-action'><strong>Maintenance-cycle readout:</strong> "
            "This view shows the condition immediately before the latest simulated PM and the stabilized readings after reset behavior.</div>",
            unsafe_allow_html=True,
        )

with calendar_tab:
    pm_calendar = estimate_pm_calendar(features[features["tool_id"].isin(selected_tools)])
    selected_calendar = pm_calendar[pm_calendar["Tool"] == technician_tool]
    if not selected_calendar.empty:
        calendar_row = selected_calendar.iloc[0]
        st.markdown(
            f"<div class='cmp-action'><strong>Next planned maintenance:</strong> "
            f"{escape(str(calendar_row['Next PM Item']))} for {escape(technician_tool)} around "
            f"{calendar_row['Estimated Due'].strftime('%b %d, %Y %I:%M %p')} "
            f"({calendar_row['Hours Until Due']:.1f} hours). "
            f"{escape(str(calendar_row['Priority']))}.</div>",
            unsafe_allow_html=True,
        )
    st.dataframe(pm_calendar, width="stretch", hide_index=True)
    calendar_chart = (
        alt.Chart(pm_calendar)
        .mark_bar()
        .encode(
            x=alt.X("Tool:N", title="Tool"),
            y=alt.Y("Hours Until Due:Q", title="Estimated hours until PM"),
            color=alt.Color("Current Risk:N", title="Current risk"),
            tooltip=[
                alt.Tooltip("Tool:N"),
                alt.Tooltip("Next PM Item:N"),
                alt.Tooltip("Estimated Due:T"),
                alt.Tooltip("Hours Until Due:Q", format=".1f"),
                alt.Tooltip("Priority:N"),
            ],
        )
        .properties(height=300)
    )
    st.altair_chart(style_chart(calendar_chart), width="stretch")
    st.caption("Calendar estimates use synthetic consumable-hour trends and current risk level, so treat them as planning guidance for the portfolio demo.")

with ticket_tab:
    ticket_text = maintenance_ticket(technician_tool, technician_row, cause_table)
    st.markdown(ticket_text)
    st.download_button(
        "Download maintenance ticket",
        data=ticket_text.encode("utf-8"),
        file_name=f"{technician_tool.lower()}_maintenance_ticket.md",
        mime="text/markdown",
    )

with action_log_tab:
    st.markdown(
        "<div class='cmp-action'><strong>Action log:</strong> Record what the technician checked, "
        "what they found, and whether the risk improved after the action.</div>",
        unsafe_allow_html=True,
    )
    with st.form("technician_action_form", clear_on_submit=True):
        form_col_a, form_col_b = st.columns(2)
        with form_col_a:
            technician_name = st.text_input("Technician", value="Demo technician")
            action_taken = st.selectbox(
                "Action taken",
                [
                    "Inspected pad condition",
                    "Checked retaining ring wear",
                    "Verified slurry flow",
                    "Reviewed recent alarms",
                    "Checked vibration source",
                    "Verified downforce pressure",
                    "Replaced pad",
                    "Escalated to process engineering",
                ],
            )
            risk_after = st.selectbox(
                "Risk after action",
                ["normal", "low", "medium", "high"],
                index=["normal", "low", "medium", "high"].index(str(technician_row["rule_risk_level"])),
            )
        with form_col_b:
            finding = st.text_area(
                "Finding",
                value=f"Checked {cause_table.iloc[0]['Possible Root Cause'].lower()} indicators for {technician_tool}.",
                height=100,
            )
            next_step = st.text_area(
                "Next step",
                value="Monitor next run and compare vibration, slurry flow, removal rate, and process drift against baseline.",
                height=100,
            )

        submitted = st.form_submit_button("Add action log entry")
        if submitted:
            st.session_state.technician_action_log.append(
                {
                    "timestamp": latest_timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "tool_id": technician_tool,
                    "technician": technician_name,
                    "action_taken": action_taken,
                    "finding": finding,
                    "risk_before": str(technician_row["rule_risk_level"]),
                    "risk_after": risk_after,
                    "next_step": next_step,
                }
            )
            st.success("Action log entry added.")

    action_log = action_log_dataframe()
    if action_log.empty:
        st.info("No technician actions recorded yet in this session.")
    else:
        st.dataframe(action_log.sort_values("timestamp", ascending=False), width="stretch", hide_index=True)
        latest_entry = action_log.tail(1).iloc[0]
        if latest_entry["risk_before"] != latest_entry["risk_after"]:
            st.markdown(
                f"<div class='cmp-handoff'>Latest closeout changed {escape(latest_entry['tool_id'])} "
                f"from {escape(latest_entry['risk_before'])} risk to {escape(latest_entry['risk_after'])} risk.</div>",
                unsafe_allow_html=True,
            )
        st.download_button(
            "Download action log CSV",
            data=csv_download(action_log),
            file_name="technician_action_log.csv",
            mime="text/csv",
        )

with handoff_tab:
    handoff_text = shift_handoff(technician_tool, technician_row, cause_table)
    st.markdown(f"<div class='cmp-handoff'>{escape(handoff_text)}</div>", unsafe_allow_html=True)
    st.download_button(
        "Download handoff text",
        data=handoff_text.encode("utf-8"),
        file_name=f"{technician_tool.lower()}_shift_handoff.txt",
        mime="text/plain",
    )

with assistant_tab:
    technician_question = st.text_area(
        "Ask what is wrong with the tool",
        value=(
            f"{technician_tool} has vibration {technician_row['vibration']:.3f}, "
            f"slurry flow {technician_row['slurry_flow_rate']:.2f}, and "
            f"process drift {technician_row['process_drift_nm']:.2f} nm. What should I check?"
        ),
        height=110,
    )
    st.markdown(
        f"<div class='cmp-handoff'>{escape(assistant_response(technician_question, technician_tool, technician_row, cause_table))}</div>",
        unsafe_allow_html=True,
    )
    st.caption("This assistant is rule-based for portfolio transparency; it does not send data to an external AI API.")

with interview_tab:
    st.markdown(
        """
### How I Would Explain This Project In An Interview

I built a CMP predictive maintenance system that simulates semiconductor tool sensor data, detects abnormal equipment trends, estimates maintenance risk, and converts those signals into technician-focused troubleshooting guidance.

CMP tools matter because wafer polishing depends on stable mechanical motion, slurry delivery, downforce pressure, pad condition, retaining ring condition, and removal-rate control. Small drift in those signals can lead to defects, downtime, scrap risk, or yield loss.

The dashboard monitors motor current, slurry flow, vibration, downforce pressure, consumable life, alarm count, removal rate, process drift, and maintenance reset events. Rule-based alerts make the logic explainable, while the model prediction view shows how machine learning can classify normal, warning, and maintenance-needed states.

A technician would use this by checking the priority tool, reviewing the likely root causes, following the recommended checks, comparing before-vs-after maintenance behavior, and copying the shift handoff into the next-shift communication.

Next I would connect the workflow to real historian or equipment log exports, validate thresholds with technicians and process engineers, and add false-alarm review so the system stays useful in production.
        """
    )

st.divider()

left, right = st.columns([1.4, 1])
with left:
    section_label("Sensor Trend")
    if filtered.empty:
        st.info("No rows match the selected filters.")
    else:
        st.altair_chart(sensor_chart(filtered, selected_sensor), width="stretch")

with right:
    section_label("Risk Distribution")
    risk_counts = (
        features[features["tool_id"].isin(selected_tools)]
        .groupby(["tool_id", "rule_risk_level"])
        .size()
        .reset_index(name="rows")
    )
    risk_chart = (
        alt.Chart(risk_counts)
        .mark_bar()
        .encode(
            x=alt.X("tool_id:N", title="Tool"),
            y=alt.Y("rows:Q", title="Rows"),
            color=alt.Color(
                "rule_risk_level:N",
                title="Risk",
                scale=alt.Scale(
                    domain=list(RISK_COLORS.keys()),
                    range=list(RISK_COLORS.values()),
                ),
            ),
            tooltip=["tool_id:N", "rule_risk_level:N", "rows:Q"],
        )
        .properties(height=320)
    )
    st.altair_chart(style_chart(risk_chart), width="stretch")

section_label("Maintenance Event Timeline")
event_view = maintenance_event_summary(features[features["tool_id"].isin(selected_tools)])
if event_view.empty:
    st.info("No maintenance events match the selected tools.")
else:
    st.dataframe(
        event_view.sort_values("maintenance_timestamp", ascending=False),
        width="stretch",
        hide_index=True,
    )

section_label("Recent Alerts")
recent_alerts = filtered_alerts.sort_values("timestamp", ascending=False).head(50)
st.dataframe(
    recent_alerts[
        [
            "timestamp",
            "tool_id",
            "rule_risk_level",
            "rule_risk_points",
            "maintenance_state",
            "platen_motor_current",
            "slurry_flow_rate",
            "vibration",
            "wafer_removal_rate",
            "process_drift_nm",
            "alarm_count",
            "maintenance_event",
            "recommended_action",
        ]
    ],
    width="stretch",
    hide_index=True,
)

st.divider()

model_tab, importance_tab, metrics_tab = st.tabs(
    ["Model Predictions", "Feature Importance", "Model Metrics"]
)

with model_tab:
    prediction_view = filtered_predictions.copy()
    prediction_view["correct_prediction"] = (
        prediction_view["maintenance_state"]
        == prediction_view["predicted_maintenance_state"]
    )
    prediction_accuracy = prediction_view["correct_prediction"].mean()
    st.metric("Filtered Prediction Accuracy", f"{prediction_accuracy:.1%}")
    st.dataframe(
        prediction_view[
            [
                "timestamp",
                "tool_id",
                "maintenance_state",
                "predicted_maintenance_state",
                "rule_risk_level",
                "prob_maintenance_needed",
                "prob_warning",
                "prob_normal",
                "model_confidence",
                "review_priority",
                "wafer_removal_rate",
                "process_drift_nm",
            ]
        ].sort_values("timestamp", ascending=False),
        width="stretch",
        hide_index=True,
    )

with importance_tab:
    top_importance = importance.head(12)
    importance_chart = (
        alt.Chart(top_importance)
        .mark_bar()
        .encode(
            x=alt.X("importance:Q", title="Importance"),
            y=alt.Y("feature:N", title="Feature", sort="-x"),
            tooltip=[
                alt.Tooltip("feature:N"),
                alt.Tooltip("importance:Q", format=".4f"),
            ],
        )
        .properties(height=390)
    )
    st.altair_chart(style_chart(importance_chart), width="stretch")
    st.dataframe(top_importance, width="stretch", hide_index=True)

with metrics_tab:
    st.markdown(metrics_text)
