from pathlib import Path

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
    }

    .stApp {
        background: radial-gradient(circle at top left, #18222e 0, #0f141b 34%, #0b0f14 100%);
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
        padding: 1.35rem 1.45rem;
        background:
            linear-gradient(90deg, rgba(57, 167, 165, 0.16), rgba(45, 57, 73, 0.38)),
            linear-gradient(180deg, rgba(25, 32, 43, 0.94), rgba(18, 24, 32, 0.94));
        margin-bottom: 1.05rem;
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
        color: var(--cmp-muted);
        font-weight: 800;
        text-transform: uppercase;
        font-size: 0.76rem;
        margin: 1.1rem 0 0.45rem;
    }

    .cmp-action {
        border-left: 4px solid var(--cmp-accent);
        background: var(--cmp-accent-soft);
        border-radius: 8px;
        padding: 0.9rem 1rem;
        color: var(--cmp-text);
        margin-bottom: 1rem;
    }

    .cmp-tool-card {
        background: linear-gradient(180deg, rgba(31, 39, 50, 0.98), rgba(18, 24, 32, 0.98));
        border: 1px solid var(--cmp-border);
        border-radius: 8px;
        padding: 1rem;
        min-height: 13.25rem;
        box-shadow: 0 10px 28px rgba(0, 0, 0, 0.20);
    }

    .cmp-tool-id {
        color: var(--cmp-text);
        font-size: 1rem;
        font-weight: 800;
        margin-top: 0.75rem;
    }

    .cmp-rule-points {
        color: var(--cmp-text);
        font-size: 2rem;
        line-height: 1.1;
        font-weight: 850;
        margin: 0.35rem 0 0.75rem;
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

    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
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


def tool_card(row: pd.Series) -> str:
    return f"""
    <div class="cmp-tool-card">
        {risk_badge(row["rule_risk_level"])}
        <div class="cmp-tool-id">{row["tool_id"]}</div>
        <div class="cmp-rule-points">{int(row["rule_risk_points"])} rule points</div>
        <div class="cmp-card-row"><span>State</span><span>{row["maintenance_state"]}</span></div>
        <div class="cmp-card-row"><span>Pad life</span><span>{row["pad_life_pct"]:.1f}%</span></div>
        <div class="cmp-card-row"><span>Ring life</span><span>{row["retaining_ring_life_pct"]:.1f}%</span></div>
        <div class="cmp-card-row"><span>Removal rate</span><span>{row["wafer_removal_rate"]:.2f}</span></div>
        <div class="cmp-card-row"><span>Process drift</span><span>{row["process_drift_nm"]:.2f} nm</span></div>
    </div>
    """


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
    return trend + maintenance_markers


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

section_label("Portfolio Demo Snapshot")
metric_cols = st.columns(4)
metric_cols[0].metric("Tools", features["tool_id"].nunique())
metric_cols[1].metric("Latest Reading", latest_timestamp.strftime("%Y-%m-%d %H:%M"))
metric_cols[2].metric("Alert Rows", f"{len(alerts):,}")
metric_cols[3].metric("High Risk Tools", len(high_risk_tools))

section_label("Executive Summary")
summary_cols = st.columns(4)
summary_cols[0].metric("Current Normal Tools", int(current_state_counts.get("normal", 0)))
summary_cols[1].metric("Current Warning Tools", int(current_state_counts.get("warning", 0)))
summary_cols[2].metric(
    "Current Maintenance Needed",
    int(current_state_counts.get("maintenance_needed", 0)),
)
summary_cols[3].metric("Maintenance Events", int(features["maintenance_event"].sum()))
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
    st.altair_chart(risk_chart, width="stretch")

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
    st.altair_chart(importance_chart, width="stretch")
    st.dataframe(top_importance, width="stretch", hide_index=True)

with metrics_tab:
    st.markdown(metrics_text)
