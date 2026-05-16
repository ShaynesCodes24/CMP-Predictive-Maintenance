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
