from pathlib import Path
from html import escape
import sqlite3
from datetime import datetime
import math

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
PRODUCT_DB = ROOT / "data" / "processed" / "cmp_product_ops.sqlite"

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
        --cmp-bg: #f4f6f9;
        --cmp-panel: #ffffff;
        --cmp-panel-soft: #f8fafc;
        --cmp-border: #d9e1ec;
        --cmp-text: #162033;
        --cmp-muted: #667085;
        --cmp-accent: #006b68;
        --cmp-accent-2: #1d4ed8;
        --cmp-accent-soft: rgba(0, 107, 104, 0.10);
        --cmp-good: #177245;
        --cmp-warn: #a16207;
        --cmp-danger: #b42318;
        --cmp-shadow: 0 12px 30px rgba(15, 23, 42, 0.08);
        --cmp-shadow-soft: 0 4px 14px rgba(15, 23, 42, 0.06);
    }

    .stApp {
        background:
            linear-gradient(180deg, rgba(255, 255, 255, 0.75) 0%, rgba(244, 246, 249, 0.96) 34%),
            linear-gradient(135deg, #eef5f5 0%, #f6f8fb 54%, #eef2f7 100%);
        color: var(--cmp-text);
    }

    section[data-testid="stSidebar"] {
        background: #ffffff;
        border-right: 1px solid var(--cmp-border);
        box-shadow: 8px 0 24px rgba(15, 23, 42, 0.04);
    }

    header[data-testid="stHeader"] {
        background: rgba(244, 247, 251, 0.86);
        backdrop-filter: blur(10px);
    }

    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] .stMarkdown {
        color: var(--cmp-text);
    }

    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid var(--cmp-border);
        border-radius: 10px;
        padding: 1rem 1.05rem;
        box-shadow: var(--cmp-shadow-soft);
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
        border: 1px solid rgba(0, 107, 104, 0.16);
        border-radius: 12px;
        padding: 1.45rem 1.25rem 1.15rem;
        background:
            linear-gradient(135deg, rgba(255,255,255,0.98) 0%, rgba(232,250,248,0.96) 58%, rgba(232,240,255,0.88) 100%);
        margin-bottom: 0.85rem;
        box-shadow: var(--cmp-shadow);
        overflow: visible;
    }

    .cmp-brand-row {
        display: flex;
        align-items: center;
        gap: 0.95rem;
        margin-bottom: 0.85rem;
        min-height: 3.35rem;
    }

    .cmp-logo-mark {
        width: 3.2rem;
        height: 3.2rem;
        flex: 0 0 auto;
        border-radius: 14px;
        background:
            radial-gradient(circle at 50% 50%, rgba(255,255,255,0.95) 0 20%, transparent 21%),
            conic-gradient(from 210deg, #00b8a9, #2f80ed, #7c3aed, #00b8a9);
        position: relative;
        box-shadow: 0 12px 22px rgba(0, 107, 104, 0.20);
        transform: translateY(0.08rem);
    }

    .cmp-logo-mark::before {
        content: "";
        position: absolute;
        inset: 0.45rem;
        border: 2px solid rgba(255,255,255,0.78);
        border-radius: 50%;
    }

    .cmp-logo-mark::after {
        content: "";
        position: absolute;
        width: 1.75rem;
        height: 0.2rem;
        background: rgba(255,255,255,0.95);
        border-radius: 999px;
        transform: rotate(-28deg);
        left: 0.72rem;
        top: 1.5rem;
    }

    .cmp-brand-name {
        color: var(--cmp-text);
        font-size: 1.4rem;
        line-height: 1;
        font-weight: 900;
    }

    .cmp-brand-tagline {
        color: var(--cmp-muted);
        font-size: 0.86rem;
        margin-top: 0.16rem;
    }

    .cmp-eyebrow {
        color: var(--cmp-accent);
        font-size: 0.78rem;
        font-weight: 800;
        letter-spacing: 0;
        text-transform: uppercase;
        margin-bottom: 0.25rem;
    }

    .cmp-title {
        color: var(--cmp-text);
        font-size: 1.7rem;
        font-weight: 850;
        line-height: 1.12;
        margin: 0;
    }

    .cmp-subtitle {
        color: var(--cmp-muted);
        font-size: 0.96rem;
        margin-top: 0.5rem;
        max-width: 68rem;
    }

    .cmp-top-nav {
        margin: 0.25rem 0 1rem;
        padding: 0.55rem;
        background: rgba(255,255,255,0.76);
        border: 1px solid var(--cmp-border);
        border-radius: 12px;
        box-shadow: var(--cmp-shadow-soft);
    }

    div[role="radiogroup"] {
        gap: 0.45rem;
    }

    div[role="radiogroup"] label {
        background: #ffffff;
        border: 1px solid var(--cmp-border);
        border-radius: 9px;
        padding: 0.48rem 0.74rem;
        box-shadow: none;
    }

    div[role="radiogroup"] label:has(input:checked) {
        border-color: rgba(0, 143, 134, 0.45);
        background: #e9fbf8;
        color: var(--cmp-accent);
        box-shadow: inset 0 0 0 1px rgba(0, 143, 134, 0.18);
    }

    .cmp-section-label {
        color: var(--cmp-accent);
        font-weight: 800;
        text-transform: uppercase;
        font-size: 0.76rem;
        margin: 1.25rem 0 0.5rem;
    }

    .cmp-action {
        border-left: 4px solid var(--cmp-accent);
        border-top: 1px solid rgba(15, 118, 110, 0.18);
        border-right: 1px solid rgba(15, 118, 110, 0.18);
        border-bottom: 1px solid rgba(15, 118, 110, 0.18);
        background: #eef8f7;
        border-radius: 10px;
        padding: 0.9rem 1rem;
        color: var(--cmp-text);
        margin-bottom: 1rem;
        box-shadow: none;
    }

    .cmp-decision-card {
        border: 1px solid var(--cmp-border);
        border-radius: 10px;
        background: #ffffff;
        padding: 1rem 1.05rem;
        min-height: 11.25rem;
        box-shadow: var(--cmp-shadow-soft);
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
        border-radius: 10px;
        background: #fff8e6;
        color: var(--cmp-text);
        padding: 1rem 1.05rem;
        line-height: 1.55;
    }

    .cmp-tool-card {
        background: #ffffff;
        border: 1px solid var(--cmp-border);
        border-radius: 10px;
        padding: 1rem;
        min-height: 17.3rem;
        box-shadow: var(--cmp-shadow-soft);
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
        border-radius: 10px;
        background: #ffffff;
        box-shadow: var(--cmp-shadow-soft);
        margin-bottom: 0.85rem;
    }

    .cmp-command-card {
        padding: 0.95rem 1rem;
        min-height: 7.4rem;
    }

    .cmp-kpi-card {
        padding: 0.9rem 1rem;
        min-height: 6.5rem;
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
        font-size: 1.42rem;
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
        font-size: 1.78rem;
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
        background: #edf2f7;
        border-radius: 999px;
        overflow: hidden;
    }

    .cmp-progress-fill {
        height: 100%;
        border-radius: inherit;
    }

    div[data-testid="stDataFrame"] {
        border: 1px solid var(--cmp-border);
        border-radius: 10px;
        overflow: hidden;
        box-shadow: var(--cmp-shadow-soft);
    }

    div[data-testid="stVegaLiteChart"] {
        background: #ffffff;
        border: 1px solid var(--cmp-border);
        border-radius: 10px;
        padding: 0.55rem;
        box-shadow: var(--cmp-shadow-soft);
    }

    .block-container {
        padding-top: 1.45rem;
        padding-bottom: 3rem;
        max-width: 1380px;
    }

    div[data-testid="stTabs"] button {
        border-radius: 8px 8px 0 0;
        color: var(--cmp-muted);
    }

    div[data-testid="stTabs"] button[aria-selected="true"] {
        color: var(--cmp-accent);
        font-weight: 800;
    }

    .cmp-workspace-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 0.75rem;
        margin: 0.35rem 0 1rem;
    }

    .cmp-workspace-card {
        background: #ffffff;
        border: 1px solid var(--cmp-border);
        border-radius: 10px;
        padding: 0.85rem 0.95rem;
        box-shadow: var(--cmp-shadow-soft);
    }

    .cmp-workspace-title {
        color: var(--cmp-text);
        font-size: 0.92rem;
        font-weight: 850;
        margin-bottom: 0.25rem;
    }

    .cmp-workspace-body {
        color: var(--cmp-muted);
        font-size: 0.82rem;
        line-height: 1.42;
    }

    .cmp-report-panel {
        background: #ffffff;
        border: 1px solid var(--cmp-border);
        border-radius: 10px;
        padding: 1rem 1.15rem;
        box-shadow: var(--cmp-shadow-soft);
    }

    .cmp-status-grid {
        display: grid;
        grid-template-columns: repeat(5, minmax(0, 1fr));
        gap: 0.65rem;
        margin: 0.25rem 0 1rem;
    }

    .cmp-status-pill {
        background: rgba(255,255,255,0.88);
        border: 1px solid var(--cmp-border);
        border-radius: 10px;
        padding: 0.7rem 0.8rem;
        box-shadow: var(--cmp-shadow-soft);
    }

    .cmp-status-label {
        color: var(--cmp-muted);
        font-size: 0.72rem;
        font-weight: 850;
        text-transform: uppercase;
    }

    .cmp-status-value {
        color: var(--cmp-text);
        font-size: 0.9rem;
        font-weight: 850;
        margin-top: 0.16rem;
    }

    .cmp-status-value.good { color: var(--cmp-good); }
    .cmp-status-value.warn { color: var(--cmp-warn); }
    .cmp-status-value.danger { color: var(--cmp-danger); }

    @media (max-width: 1100px) {
        .cmp-command-grid,
        .cmp-kpi-grid,
        .cmp-workspace-grid,
        .cmp-status-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
    }

    @media (max-width: 760px) {
        .cmp-command-grid,
        .cmp-kpi-grid,
        .cmp-workspace-grid,
        .cmp-status-grid {
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


def db_connection() -> sqlite3.Connection:
    PRODUCT_DB.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(PRODUCT_DB)


def execute_db(query: str, params: tuple = ()) -> None:
    with db_connection() as connection:
        connection.execute(query, params)
        connection.commit()


def read_db(query: str, params: tuple = ()) -> pd.DataFrame:
    with db_connection() as connection:
        return pd.read_sql_query(query, connection, params=params)


def audit_event(user: str, role: str, event_type: str, details: str) -> None:
    execute_db(
        """
        INSERT INTO audit_log (timestamp, user_name, role, event_type, details)
        VALUES (datetime('now'), ?, ?, ?, ?)
        """,
        (user, role, event_type, details),
    )


def init_product_db() -> None:
    with db_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS maintenance_tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                tool_id TEXT NOT NULL,
                priority TEXT NOT NULL,
                status TEXT NOT NULL,
                assigned_to TEXT NOT NULL,
                root_cause TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                rule_points INTEGER NOT NULL,
                due_at TEXT NOT NULL,
                summary TEXT NOT NULL,
                closeout_notes TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS technician_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                ticket_id INTEGER,
                tool_id TEXT NOT NULL,
                technician TEXT NOT NULL,
                action_taken TEXT NOT NULL,
                finding TEXT NOT NULL,
                risk_before TEXT NOT NULL,
                risk_after TEXT NOT NULL,
                next_step TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS alert_thresholds (
                threshold_key TEXT PRIMARY KEY,
                value REAL NOT NULL,
                unit TEXT NOT NULL,
                description TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                updated_by TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                user_name TEXT NOT NULL,
                role TEXT NOT NULL,
                event_type TEXT NOT NULL,
                details TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS synthetic_live_feed (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                tool_id TEXT NOT NULL,
                scenario TEXT NOT NULL,
                vibration REAL NOT NULL,
                slurry_flow_rate REAL NOT NULL,
                pad_life_pct REAL NOT NULL,
                retaining_ring_life_pct REAL NOT NULL,
                wafer_removal_rate REAL NOT NULL,
                process_drift_nm REAL NOT NULL,
                alarm_count INTEGER NOT NULL,
                scored_rule_points INTEGER NOT NULL,
                scored_risk_level TEXT NOT NULL,
                scored_urgency TEXT NOT NULL,
                scored_drivers TEXT NOT NULL
            );
            """
        )
        defaults = [
            ("vibration_high", 0.70, "g", "High vibration alert threshold"),
            ("slurry_flow_low", 190.0, "ml/min", "Low slurry flow alert threshold"),
            ("pad_life_high", 90.0, "%", "Pad life warning threshold"),
            ("ring_life_high", 90.0, "%", "Retaining ring warning threshold"),
            ("process_drift_high", 10.0, "nm", "Process drift alert threshold"),
            ("removal_rate_low", 96.0, "rate", "Low wafer removal rate threshold"),
            ("alarm_burst", 2.0, "count", "Alarm burst count threshold"),
        ]
        connection.executemany(
            """
            INSERT OR IGNORE INTO alert_thresholds
                (threshold_key, value, unit, description, updated_at, updated_by)
            VALUES (?, ?, ?, ?, datetime('now'), 'system')
            """,
            defaults,
        )
        connection.commit()


def create_persistent_ticket(
    tool_id: str,
    row: pd.Series,
    probability_table: pd.DataFrame,
    assigned_to: str,
    user: str,
    role: str,
) -> None:
    urgency, _ = urgency_text(row)
    top_cause = str(probability_table.iloc[0]["Possible Root Cause"])
    due_hours = 4 if str(row["rule_risk_level"]) == "high" else 12 if str(row["rule_risk_level"]) == "medium" else 48
    due_at = pd.Timestamp.now() + pd.to_timedelta(due_hours, unit="h")
    execute_db(
        """
        INSERT INTO maintenance_tickets
            (created_at, tool_id, priority, status, assigned_to, root_cause, risk_level,
             rule_points, due_at, summary, closeout_notes)
        VALUES (datetime('now'), ?, ?, 'New', ?, ?, ?, ?, ?, ?, '')
        """,
        (
            tool_id,
            urgency,
            assigned_to,
            top_cause,
            str(row["rule_risk_level"]),
            int(row["rule_risk_points"]),
            due_at.strftime("%Y-%m-%d %H:%M:%S"),
            shift_handoff(tool_id, row, probability_table),
        ),
    )
    audit_event(user, role, "ticket_created", f"Created ticket for {tool_id}: {top_cause}")


def add_persistent_action(
    ticket_id: int | None,
    tool_id: str,
    technician: str,
    action_taken: str,
    finding: str,
    risk_before: str,
    risk_after: str,
    next_step: str,
    user: str,
    role: str,
) -> None:
    execute_db(
        """
        INSERT INTO technician_actions
            (created_at, ticket_id, tool_id, technician, action_taken, finding,
             risk_before, risk_after, next_step)
        VALUES (datetime('now'), ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (ticket_id, tool_id, technician, action_taken, finding, risk_before, risk_after, next_step),
    )
    audit_event(user, role, "action_logged", f"{technician} logged {action_taken} for {tool_id}")


def update_ticket_status(ticket_id: int, status: str, closeout_notes: str, user: str, role: str) -> None:
    execute_db(
        "UPDATE maintenance_tickets SET status = ?, closeout_notes = ? WHERE id = ?",
        (status, closeout_notes, ticket_id),
    )
    audit_event(user, role, "ticket_status_changed", f"Ticket {ticket_id} moved to {status}")


def update_threshold(threshold_key: str, value: float, user: str, role: str) -> None:
    execute_db(
        """
        UPDATE alert_thresholds
        SET value = ?, updated_at = datetime('now'), updated_by = ?
        WHERE threshold_key = ?
        """,
        (value, user, threshold_key),
    )
    audit_event(user, role, "threshold_updated", f"{threshold_key} set to {value}")


def load_threshold_values() -> dict[str, float]:
    thresholds = read_db("SELECT threshold_key, value FROM alert_thresholds")
    if thresholds.empty:
        return {}
    return dict(zip(thresholds["threshold_key"], thresholds["value"]))


def has_permission(role: str, action: str) -> bool:
    permissions = {
        "Technician": {"create_ticket", "update_ticket", "log_action", "ingest_data"},
        "Process Engineer": {
            "create_ticket",
            "update_ticket",
            "log_action",
            "update_threshold",
            "ingest_data",
        },
        "Maintenance Supervisor": {
            "create_ticket",
            "update_ticket",
            "log_action",
            "ingest_data",
        },
        "Admin": {
            "create_ticket",
            "update_ticket",
            "log_action",
            "update_threshold",
            "ingest_data",
        },
    }
    return action in permissions.get(role, set())


def score_uploaded_data(uploaded: pd.DataFrame, thresholds: dict[str, float]) -> pd.DataFrame:
    required = {
        "timestamp",
        "tool_id",
        "vibration",
        "slurry_flow_rate",
        "pad_life_pct",
        "retaining_ring_life_pct",
        "wafer_removal_rate",
        "process_drift_nm",
        "alarm_count",
    }
    missing = required.difference(uploaded.columns)
    if missing:
        raise ValueError(f"Uploaded file is missing required columns: {', '.join(sorted(missing))}")

    scored = uploaded.copy()
    scored["timestamp"] = pd.to_datetime(scored["timestamp"], errors="coerce")
    assessments = scored.apply(
        lambda row: scenario_risk_assessment(
            float(row["vibration"]),
            float(row["slurry_flow_rate"]),
            float(row["pad_life_pct"]),
            float(row["retaining_ring_life_pct"]),
            float(row["wafer_removal_rate"]),
            float(row["process_drift_nm"]),
            int(row["alarm_count"]),
            thresholds,
        ),
        axis=1,
    )
    scored["scored_rule_points"] = [item["points"] for item in assessments]
    scored["scored_risk_level"] = [item["level"] for item in assessments]
    scored["scored_urgency"] = [item["urgency"] for item in assessments]
    scored["scored_drivers"] = [", ".join(item["reasons"]) for item in assessments]
    return scored


def latest_live_feed() -> pd.DataFrame:
    data = read_db("SELECT * FROM synthetic_live_feed ORDER BY timestamp DESC, id DESC")
    if data.empty:
        return data
    data["timestamp"] = pd.to_datetime(data["timestamp"])
    return data


def clear_live_feed(user: str, role: str) -> None:
    execute_db("DELETE FROM synthetic_live_feed")
    audit_event(user, role, "synthetic_feed_cleared", "Cleared simulated live feed rows")


def build_synthetic_sample(
    base_row: pd.Series,
    tool_id: str,
    scenario: str,
    sample_index: int,
    thresholds: dict[str, float],
) -> dict[str, object]:
    wave = math.sin(sample_index / 3)
    vibration = float(base_row["vibration"]) + 0.012 * wave
    slurry_flow = float(base_row["slurry_flow_rate"]) + 1.2 * math.cos(sample_index / 4)
    pad_life = float(base_row["pad_life_pct"]) + sample_index * 0.05
    ring_life = float(base_row["retaining_ring_life_pct"]) + sample_index * 0.04
    removal_rate = float(base_row["wafer_removal_rate"]) - 0.05 * wave
    process_drift = float(base_row["process_drift_nm"]) + 0.08 * sample_index
    alarm_count = int(base_row["alarm_count"])

    if scenario == "Slurry restriction":
        slurry_flow -= sample_index * 1.8
        process_drift += sample_index * 0.18
        removal_rate -= sample_index * 0.12
    elif scenario == "Vibration ramp":
        vibration += sample_index * 0.025
        alarm_count += 1 if sample_index >= 4 else 0
    elif scenario == "Pad wear acceleration":
        pad_life += sample_index * 1.4
        vibration += sample_index * 0.012
        removal_rate -= sample_index * 0.08
    elif scenario == "Maintenance reset":
        vibration = max(0.25, float(base_row["vibration"]) - 0.04)
        slurry_flow = max(slurry_flow, 210.0)
        pad_life = max(5.0, float(base_row["pad_life_pct"]) * 0.12)
        ring_life = max(5.0, float(base_row["retaining_ring_life_pct"]) * 0.18)
        removal_rate = max(removal_rate, 104.0)
        process_drift = min(process_drift, 1.5)
        alarm_count = 0

    assessment = scenario_risk_assessment(
        vibration,
        slurry_flow,
        pad_life,
        ring_life,
        removal_rate,
        process_drift,
        alarm_count,
        thresholds,
    )
    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "tool_id": tool_id,
        "scenario": scenario,
        "vibration": round(vibration, 4),
        "slurry_flow_rate": round(slurry_flow, 2),
        "pad_life_pct": round(min(pad_life, 100), 2),
        "retaining_ring_life_pct": round(min(ring_life, 100), 2),
        "wafer_removal_rate": round(removal_rate, 2),
        "process_drift_nm": round(max(process_drift, 0), 2),
        "alarm_count": alarm_count,
        "scored_rule_points": int(assessment["points"]),
        "scored_risk_level": str(assessment["level"]),
        "scored_urgency": str(assessment["urgency"]),
        "scored_drivers": ", ".join(assessment["reasons"]),
    }


def append_live_sample(
    base_data: pd.DataFrame,
    tool_id: str,
    scenario: str,
    thresholds: dict[str, float],
    user: str,
    role: str,
) -> None:
    live_data = latest_live_feed()
    sample_index = int(len(live_data[live_data["tool_id"] == tool_id]) + 1) if not live_data.empty else 1
    base_row = base_data[base_data["tool_id"] == tool_id].sort_values("timestamp").tail(1).iloc[0]
    sample = build_synthetic_sample(base_row, tool_id, scenario, sample_index, thresholds)
    execute_db(
        """
        INSERT INTO synthetic_live_feed
            (timestamp, tool_id, scenario, vibration, slurry_flow_rate, pad_life_pct,
             retaining_ring_life_pct, wafer_removal_rate, process_drift_nm, alarm_count,
             scored_rule_points, scored_risk_level, scored_urgency, scored_drivers)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            sample["timestamp"],
            sample["tool_id"],
            sample["scenario"],
            sample["vibration"],
            sample["slurry_flow_rate"],
            sample["pad_life_pct"],
            sample["retaining_ring_life_pct"],
            sample["wafer_removal_rate"],
            sample["process_drift_nm"],
            sample["alarm_count"],
            sample["scored_rule_points"],
            sample["scored_risk_level"],
            sample["scored_urgency"],
            sample["scored_drivers"],
        ),
    )
    audit_event(user, role, "synthetic_live_sample", f"Generated {scenario} sample for {tool_id}")


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


def workspace_cards() -> str:
    cards = [
        (
            "Industrial ops",
            "Persistent tickets, threshold settings, data ingestion, and audit trail.",
        ),
        (
            "Fab simulations",
            "Cost exposure, live-feed projections, what-if scenarios, and incident replay.",
        ),
        (
            "Technician workflow",
            "Troubleshooting guidance, work tickets, action logs, and shift handoffs.",
        ),
        (
            "Model analytics",
            "Prediction review, feature importance, confidence bands, and model metrics.",
        ),
    ]
    rendered = "".join(
        "<div class='cmp-workspace-card'>"
        f"<div class='cmp-workspace-title'>{escape(title)}</div>"
        f"<div class='cmp-workspace-body'>{escape(body)}</div>"
        "</div>"
        for title, body in cards
    )
    return f"<div class='cmp-workspace-grid'>{rendered}</div>"


def status_pill(label: str, value: str, state: str = "") -> str:
    state_class = f" {state}" if state else ""
    return (
        "<div class='cmp-status-pill'>"
        f"<div class='cmp-status-label'>{escape(label)}</div>"
        f"<div class='cmp-status-value{state_class}'>{escape(value)}</div>"
        "</div>"
    )


def status_grid(items: list[tuple[str, str, str]]) -> str:
    rendered = "".join(status_pill(label, value, state) for label, value, state in items)
    return f"<div class='cmp-status-grid'>{rendered}</div>"


def freshness_status(latest_data_timestamp: pd.Timestamp, runtime_timestamp: datetime) -> tuple[str, str]:
    age = runtime_timestamp - latest_data_timestamp.to_pydatetime()
    age_hours = age.total_seconds() / 3600
    if age_hours <= 2:
        return "Current", "good"
    if age_hours <= 24:
        return f"{age_hours:.1f}h old", "warn"
    return "Demo snapshot", "warn"


def deployment_readiness_report(
    thresholds: dict[str, float],
    latest_data_timestamp: pd.Timestamp,
    runtime_timestamp: datetime,
) -> str:
    threshold_lines = "\n".join(
        f"- {key}: {value}" for key, value in sorted(thresholds.items())
    )
    return f"""# PlanarIQ Deployment Readiness

## Runtime Status
- Application runtime: {runtime_timestamp.strftime('%Y-%m-%d %H:%M:%S')}
- Latest source data timestamp: {latest_data_timestamp.strftime('%Y-%m-%d %H:%M:%S')}
- Current data mode: Synthetic CMP demo data
- Sensor feed state: Simulated, ready for historian or CSV integration
- Product database: SQLite demo database connected

## Required Production Integrations
- Equipment historian, SECS/GEM, EDA, MES export, or scheduled CSV ingestion
- Enterprise authentication and role mapping
- Production database with backup and retention policy
- Change-controlled alert threshold governance
- Model validation against real maintenance and process history

## Expected Data Contract
- timestamp
- tool_id
- vibration
- slurry_flow_rate
- pad_life_pct
- retaining_ring_life_pct
- wafer_removal_rate
- process_drift_nm
- alarm_count

## Active Threshold Configuration
{threshold_lines}

## Production Validation Checklist
- Confirm thresholds with equipment, process, and maintenance engineers
- Measure false positives and missed detections by tool type
- Tie tickets to verified technician closeout and root cause
- Audit user actions, threshold changes, and ticket status changes
- Validate model drift and retraining triggers before operational use
"""


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
    thresholds: dict[str, float] | None = None,
) -> dict[str, object]:
    thresholds = thresholds or {}
    vibration_high = thresholds.get("vibration_high", 0.70)
    slurry_flow_low = thresholds.get("slurry_flow_low", 190.0)
    pad_life_high = thresholds.get("pad_life_high", 90.0)
    ring_life_high = thresholds.get("ring_life_high", 90.0)
    removal_rate_low = thresholds.get("removal_rate_low", 96.0)
    process_drift_high = thresholds.get("process_drift_high", 10.0)
    alarm_burst = int(thresholds.get("alarm_burst", 2.0))
    points = 0
    reasons = []

    if vibration >= vibration_high:
        points += 1
        reasons.append("High vibration")
    if slurry_flow <= slurry_flow_low:
        points += 1
        reasons.append("Low slurry flow")
    if pad_life >= pad_life_high and vibration >= vibration_high * 0.89:
        points += 1
        reasons.append("Pad life near limit with elevated vibration")
    if ring_life >= ring_life_high:
        points += 1
        reasons.append("Retaining ring life near limit")
    if removal_rate <= removal_rate_low or process_drift >= process_drift_high:
        points += 1
        reasons.append("Removal-rate or process-drift abnormality")
    if alarm_count >= alarm_burst:
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
            "alert_pad_wear": pad_life >= pad_life_high and vibration >= vibration_high * 0.89,
            "alert_slurry_flow": slurry_flow <= slurry_flow_low,
            "alert_motor_vibration": vibration >= vibration_high,
            "alert_pressure_drift": False,
            "alert_alarm_burst": alarm_count >= alarm_burst,
            "alert_process_drift": removal_rate <= removal_rate_low or process_drift >= process_drift_high,
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


def live_feed_simulation(
    data: pd.DataFrame,
    tool_id: str,
    thresholds: dict[str, float],
    rows: int = 18,
) -> pd.DataFrame:
    tool_data = data[data["tool_id"] == tool_id].sort_values("timestamp").tail(rows).copy()
    if tool_data.empty:
        return pd.DataFrame()

    latest = tool_data.tail(1).iloc[0]
    projected_rows = []
    for step in range(1, 7):
        drift_factor = step / 6
        vibration = float(latest["vibration"]) + 0.018 * step
        slurry_flow = float(latest["slurry_flow_rate"]) - 1.4 * step
        removal_rate = float(latest["wafer_removal_rate"]) - 0.18 * step
        process_drift = float(latest["process_drift_nm"]) + 0.35 * step
        assessment = scenario_risk_assessment(
            vibration,
            slurry_flow,
            float(latest["pad_life_pct"]) + drift_factor,
            float(latest["retaining_ring_life_pct"]) + drift_factor,
            removal_rate,
            process_drift,
            int(latest["alarm_count"]),
            thresholds,
        )
        projected_rows.append(
            {
                **latest.to_dict(),
                "timestamp": latest["timestamp"] + pd.to_timedelta(step, unit="h"),
                "vibration": vibration,
                "slurry_flow_rate": slurry_flow,
                "wafer_removal_rate": removal_rate,
                "process_drift_nm": process_drift,
                "rule_risk_level": assessment["level"],
                "rule_risk_points": assessment["points"],
                "feed_type": "Projected live feed",
            }
        )

    tool_data["feed_type"] = "Historical feed"
    return pd.concat([tool_data, pd.DataFrame(projected_rows)], ignore_index=True)


def live_feed_chart(data: pd.DataFrame) -> alt.Chart:
    base = alt.Chart(data).encode(
        x=alt.X("timestamp:T", title="Feed time"),
        color=alt.Color("feed_type:N", title="Feed"),
        tooltip=[
            alt.Tooltip("timestamp:T", title="Time"),
            alt.Tooltip("feed_type:N", title="Feed"),
            alt.Tooltip("rule_risk_level:N", title="Risk"),
            alt.Tooltip("vibration:Q", format=".3f"),
            alt.Tooltip("slurry_flow_rate:Q", format=".2f"),
            alt.Tooltip("process_drift_nm:Q", format=".2f"),
        ],
    )
    return style_chart(
        base.mark_line(point=True).encode(
            y=alt.Y("vibration:Q", title="Projected vibration")
        ).properties(height=300)
    )


def display_live_feed_rows(live_rows: pd.DataFrame, tool_id: str) -> pd.DataFrame:
    if live_rows.empty:
        return pd.DataFrame()
    display_rows = live_rows[live_rows["tool_id"] == tool_id].copy()
    if display_rows.empty:
        return display_rows
    display_rows["feed_type"] = "Persistent synthetic stream"
    display_rows["rule_risk_level"] = display_rows["scored_risk_level"]
    display_rows["rule_risk_points"] = display_rows["scored_rule_points"]
    return display_rows.sort_values("timestamp")


def model_quality_summary(prediction_data: pd.DataFrame) -> pd.DataFrame:
    reviewed = prediction_data.copy()
    reviewed["correct_prediction"] = (
        reviewed["maintenance_state"] == reviewed["predicted_maintenance_state"]
    )
    reviewed["confidence_band"] = pd.cut(
        reviewed["model_confidence"],
        bins=[0, 0.7, 0.9, 1.0],
        labels=["Low confidence", "Medium confidence", "High confidence"],
        include_lowest=True,
    )
    return (
        reviewed.groupby("confidence_band", observed=True)
        .agg(
            rows=("tool_id", "size"),
            accuracy=("correct_prediction", "mean"),
            avg_maintenance_probability=("prob_maintenance_needed", "mean"),
        )
        .reset_index()
    )


def professional_report(
    summary_data: pd.DataFrame,
    ticket_data: pd.DataFrame,
    action_data: pd.DataFrame,
    pm_calendar: pd.DataFrame,
) -> str:
    priority = summary_data.sort_values(
        ["rule_risk_points", "process_drift_nm"],
        ascending=[False, False],
    ).iloc[0]
    open_tickets = 0 if ticket_data.empty else int((ticket_data["status"] != "Closed").sum())
    latest_pm = pm_calendar.iloc[0]
    latest_actions = "No technician actions recorded."
    if not action_data.empty:
        latest_action = action_data.iloc[0]
        latest_actions = (
            f"Latest action: {latest_action['technician']} performed "
            f"{latest_action['action_taken']} on {latest_action['tool_id']}."
        )

    return f"""# CMP Equipment Health Operations Report

## Fleet Status
- Tools monitored: {summary_data['tool_id'].nunique()}
- Highest priority tool: {priority['tool_id']}
- Current risk: {priority['rule_risk_level']}
- Rule points: {int(priority['rule_risk_points'])}
- Open maintenance tickets: {open_tickets}

## Next PM
- Tool: {latest_pm['Tool']}
- Item: {latest_pm['Next PM Item']}
- Estimated due: {latest_pm['Estimated Due'].strftime('%Y-%m-%d %H:%M')}
- Priority: {latest_pm['Priority']}

## Technician Activity
{latest_actions}

## Recommended Supervisor Review
- Review open tickets and confirm assignment.
- Check any high-risk tool before the next production run.
- Validate recurring root causes against action history.
- Export audit trail for shift review if thresholds or ticket status changed.
"""


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
            gridColor="rgba(100, 112, 132, 0.18)",
            labelColor="#425066",
            titleColor="#647084",
        )
        .configure_legend(labelColor="#425066", titleColor="#647084")
        .configure_title(color="#17202c")
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

init_product_db()

if "technician_action_log" not in st.session_state:
    st.session_state.technician_action_log = []

st.markdown(
    """
    <div class="cmp-hero">
        <div class="cmp-brand-row">
            <div class="cmp-logo-mark"></div>
            <div>
                <div class="cmp-brand-name">PlanarIQ</div>
                <div class="cmp-brand-tagline">CMP equipment intelligence for high-uptime fabs</div>
            </div>
        </div>
        <div class="cmp-eyebrow">Process-aware predictive maintenance</div>
        <h1 class="cmp-title">Fleet Health, PM Planning, And Technician Execution</h1>
        <div class="cmp-subtitle">
            A semiconductor maintenance command center for CMP tool risk, technician work orders,
            root-cause guidance, PM planning, model quality, and operational exposure.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

product_area = st.radio(
    "Workspace",
    [
        "Executive overview",
        "Industrial ops",
        "Fab simulations",
        "Technician workflow",
        "Model analytics",
        "Deployment readiness",
        "Full command center",
    ],
    horizontal=True,
)

tool_options = sorted(features["tool_id"].unique())
operator_name = st.sidebar.text_input("User", value="Demo User")
operator_role = st.sidebar.selectbox(
    "Role",
    options=["Technician", "Process Engineer", "Maintenance Supervisor", "Admin"],
)
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
threshold_values = load_threshold_values()
runtime_timestamp = datetime.now()
data_mode = st.sidebar.selectbox(
    "Data mode",
    [
        "Synthetic CMP demo data",
        "Simulated live feed",
        "Uploaded CSV scoring",
        "Historian connector placeholder",
    ],
)
live_feed_rows = latest_live_feed()
stream_tool = None
stream_scenario = "Normal drift"
if data_mode == "Simulated live feed":
    st.sidebar.markdown("### Synthetic Stream")
    stream_tool = st.sidebar.selectbox("Stream tool", tool_options)
    stream_scenario = st.sidebar.selectbox(
        "Stream scenario",
        [
            "Normal drift",
            "Slurry restriction",
            "Vibration ramp",
            "Pad wear acceleration",
            "Maintenance reset",
        ],
    )
    stream_active = st.sidebar.toggle("Stream active", value=True)
    if st.sidebar.button("Generate next sample"):
        append_live_sample(
            features,
            stream_tool,
            stream_scenario,
            threshold_values,
            operator_name,
            operator_role,
        )
        live_feed_rows = latest_live_feed()
        st.sidebar.success("Synthetic sample generated.")
    if st.sidebar.button("Clear stream"):
        clear_live_feed(operator_name, operator_role)
        live_feed_rows = latest_live_feed()
        st.sidebar.success("Synthetic feed cleared.")
    if stream_active:
        last_auto_sample = st.session_state.get("last_auto_live_sample")
        now_second = datetime.now().replace(microsecond=0)
        if last_auto_sample != now_second:
            append_live_sample(
                features,
                stream_tool,
                stream_scenario,
                threshold_values,
                operator_name,
                operator_role,
            )
            st.session_state.last_auto_live_sample = now_second
            live_feed_rows = latest_live_feed()

source_timestamp = latest_timestamp
if data_mode == "Simulated live feed" and not live_feed_rows.empty:
    source_timestamp = live_feed_rows["timestamp"].max()
freshness_label, freshness_state = freshness_status(source_timestamp, runtime_timestamp)

st.markdown(
    status_grid(
        [
            ("Runtime clock", runtime_timestamp.strftime("%b %d, %Y %I:%M %p"), "good"),
            ("Source timestamp", source_timestamp.strftime("%b %d, %Y %I:%M %p"), freshness_state),
            ("Data freshness", freshness_label, freshness_state),
            ("Feed mode", data_mode, "warn" if "demo" in data_mode.lower() or "placeholder" in data_mode.lower() else "good"),
            ("System status", "Integration ready", "good"),
        ]
    ),
    unsafe_allow_html=True,
)

if product_area == "Executive overview":
    section_label("Executive Overview")
    pm_calendar_overview = estimate_pm_calendar(features)
    tickets_overview = read_db("SELECT * FROM maintenance_tickets ORDER BY id DESC")
    actions_overview = read_db("SELECT * FROM technician_actions ORDER BY id DESC")
    open_ticket_count = (
        int((tickets_overview["status"] != "Closed").sum())
        if not tickets_overview.empty
        else 0
    )
    next_pm = pm_calendar_overview.iloc[0]
    st.markdown(workspace_cards(), unsafe_allow_html=True)
    card_grid(
        [
            command_card("Fleet status", fleet_status, f"{features['tool_id'].nunique()} tools monitored", fleet_accent),
            command_card("Priority tool", priority_label, priority_caption, priority_accent),
            command_card("Open work orders", str(open_ticket_count), "Persistent maintenance tickets", "warn" if open_ticket_count else "good"),
            command_card("Next PM", str(next_pm["Tool"]), f"{next_pm['Next PM Item']} in {float(next_pm['Hours Until Due']):.1f}h", "teal"),
        ],
        "cmp-command-grid",
    )
    executive_report = professional_report(
        summary,
        tickets_overview,
        actions_overview,
        pm_calendar_overview,
    )
    st.markdown(executive_report)
    st.download_button(
        "Download operations report",
        data=executive_report.encode("utf-8"),
        file_name="cmp_operations_report.md",
        mime="text/markdown",
    )
    st.stop()

if product_area == "Deployment readiness":
    section_label("Deployment Readiness")
    readiness_text = deployment_readiness_report(
        threshold_values,
        source_timestamp,
        runtime_timestamp,
    )
    card_grid(
        [
            kpi_card("Data source", data_mode, "Current configured runtime mode", "warn" if "demo" in data_mode.lower() else "teal"),
            kpi_card("Product DB", "Connected", "SQLite demo persistence active", "good"),
            kpi_card("Alert engine", "Active", "Threshold-driven simulator and upload scoring", "good"),
            kpi_card("Production state", "Integration ready", "Needs fab data validation", "warn"),
        ],
        "cmp-kpi-grid",
    )
    st.markdown(readiness_text)
    st.download_button(
        "Download deployment readiness report",
        data=readiness_text.encode("utf-8"),
        file_name="planariq_deployment_readiness.md",
        mime="text/markdown",
    )
    st.stop()

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
st.markdown(
    f"<div class='cmp-action'><strong>Selected product area:</strong> {escape(product_area)}. "
    "Use the sections below as role-based product modules: industrial ops, fab simulations, technician workflow, and model analytics.</div>",
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

if product_area == "Model analytics":
    section_label("Model Analytics")
    left, right = st.columns([1.35, 1])
    with left:
        if filtered.empty:
            st.info("No rows match the selected filters.")
        else:
            st.altair_chart(sensor_chart(filtered, selected_sensor), width="stretch")
    with right:
        quality = model_quality_summary(predictions)
        overall_accuracy = (
            predictions["maintenance_state"] == predictions["predicted_maintenance_state"]
        ).mean()
        card_grid(
            [
                kpi_card("Model accuracy", f"{overall_accuracy:.1%}", "Generated validation rows", "good"),
                kpi_card("Review queue", str(int((predictions["review_priority"] != "normal_monitoring").sum())), "Rows needing model review", "warn"),
            ],
            "cmp-kpi-grid",
        )
        st.dataframe(quality, width="stretch", hide_index=True)

    model_tab, importance_tab, metrics_tab = st.tabs(
        ["Model Predictions", "Feature Importance", "Model Metrics"]
    )
    with model_tab:
        prediction_view = filtered_predictions.copy()
        prediction_view["correct_prediction"] = (
            prediction_view["maintenance_state"]
            == prediction_view["predicted_maintenance_state"]
        )
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
    with metrics_tab:
        st.markdown(metrics_text)
    st.stop()

if product_area == "Fab simulations":
    section_label("Fab Simulation Workspace")
    impact_tab, live_tab, simulator_tab, replay_tab, report_tab = st.tabs(
        [
            "Cost Exposure",
            "Live Feed",
            "What-If Scenario",
            "Incident Replay",
            "Supervisor Report",
        ]
    )
    with impact_tab:
        impact_tool = st.selectbox("Impact tool", options=tool_options, index=0, key="route_impact_tool")
        impact_row = summary[summary["tool_id"] == impact_tool].iloc[0]
        col_a, col_b = st.columns(2)
        with col_a:
            lots_at_risk = st.slider("Lots at risk", 1, 40, 6, key="route_lots")
            wafers_per_lot = st.slider("Wafers per lot", 1, 50, 25, key="route_wafers")
            scrap_cost = st.number_input("Scrap cost per wafer ($)", min_value=0, value=850, step=50, key="route_scrap")
        with col_b:
            downtime_hours = st.slider("Potential downtime hours", 0.0, 48.0, 8.0, 0.5, key="route_down_hours")
            downtime_cost = st.number_input("Downtime cost per hour ($)", min_value=0, value=2500, step=250, key="route_down_cost")
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
                    "Estimated exposure",
                    [
                        f"Wafers at risk: {impact['wafers_at_risk']:.0f}",
                        f"Expected scrap cost: ${impact['expected_scrap_cost']:,.0f}",
                        f"Expected downtime cost: ${impact['expected_downtime_cost']:,.0f}",
                        f"Total exposure: ${impact['total_exposure']:,.0f}",
                    ],
                ),
                unsafe_allow_html=True,
            )
    with live_tab:
        live_tool = st.selectbox("Live feed tool", options=tool_options, index=0, key="route_live_tool")
        live_feed = display_live_feed_rows(live_feed_rows, live_tool)
        if live_feed.empty:
            live_feed = live_feed_simulation(features, live_tool, threshold_values)
        st.altair_chart(live_feed_chart(live_feed), width="stretch")
        st.dataframe(live_feed.tail(12), width="stretch", hide_index=True)
    with simulator_tab:
        base_tool = st.selectbox("Scenario baseline tool", options=tool_options, index=0, key="route_scenario_tool")
        base_row = summary[summary["tool_id"] == base_tool].iloc[0]
        col_a, col_b = st.columns(2)
        with col_a:
            sim_vibration = st.slider("Vibration", 0.20, 1.20, float(base_row["vibration"]), 0.01, key="route_vib")
            sim_slurry = st.slider("Slurry flow", 150.0, 230.0, float(base_row["slurry_flow_rate"]), 0.5, key="route_slurry")
            sim_pad = st.slider("Pad life used (%)", 0.0, 100.0, float(base_row["pad_life_pct"]), 0.5, key="route_pad")
        with col_b:
            sim_ring = st.slider("Ring life used (%)", 0.0, 100.0, float(base_row["retaining_ring_life_pct"]), 0.5, key="route_ring")
            sim_removal = st.slider("Wafer removal rate", 88.0, 112.0, float(base_row["wafer_removal_rate"]), 0.1, key="route_removal")
            sim_drift = st.slider("Process drift (nm)", 0.0, 20.0, float(base_row["process_drift_nm"]), 0.1, key="route_drift")
            sim_alarms = st.slider("Alarm count", 0, 5, int(base_row["alarm_count"]), key="route_alarms")
        scenario = scenario_risk_assessment(
            sim_vibration,
            sim_slurry,
            sim_pad,
            sim_ring,
            sim_removal,
            sim_drift,
            sim_alarms,
            threshold_values,
        )
        st.markdown(
            decision_card(
                f"Scenario result: {str(scenario['level']).upper()} risk",
                [
                    f"Rule points: {scenario['points']}",
                    f"Urgency: {scenario['urgency']}",
                    "Drivers: " + ", ".join(scenario["reasons"]),
                ],
            ),
            unsafe_allow_html=True,
        )
    with replay_tab:
        replay_tool = st.selectbox("Replay tool", options=tool_options, index=0, key="route_replay_tool")
        replay = incident_replay_data(features, replay_tool)
        st.altair_chart(incident_replay_chart(replay), width="stretch")
        st.dataframe(replay.tail(20), width="stretch", hide_index=True)
    with report_tab:
        report_text = professional_report(
            summary,
            read_db("SELECT * FROM maintenance_tickets ORDER BY id DESC"),
            read_db("SELECT * FROM technician_actions ORDER BY id DESC"),
            estimate_pm_calendar(features),
        )
        st.markdown(report_text)
        st.download_button(
            "Download supervisor report",
            data=report_text.encode("utf-8"),
            file_name="cmp_operations_report.md",
            mime="text/markdown",
        )
    st.stop()

if product_area == "Technician workflow":
    section_label("Technician Workflow")
    technician_tool = st.selectbox(
        "Tool",
        options=tool_options,
        index=tool_options.index(str(top_priority["tool_id"])) if str(top_priority["tool_id"]) in tool_options else 0,
        key="route_technician_tool",
    )
    technician_row = features[features["tool_id"] == technician_tool].sort_values("timestamp").tail(1).iloc[0]
    cause_table = root_cause_probabilities(technician_row)
    urgency, business_impact = urgency_text(technician_row)
    troubleshooting_tab, ticket_tab, action_tab, handoff_tab = st.tabs(
        ["Troubleshooting", "Ticket", "Action Log", "Shift Handoff"]
    )
    with troubleshooting_tab:
        col_a, col_b, col_c = st.columns([1, 1.1, 0.9])
        with col_a:
            st.markdown(decision_card("Likely causes", likely_causes(cause_table)), unsafe_allow_html=True)
        with col_b:
            st.markdown(decision_card("Technician checks", recommended_checks(cause_table, technician_row)), unsafe_allow_html=True)
        with col_c:
            st.markdown(decision_card("Urgency", [urgency, business_impact]), unsafe_allow_html=True)
    with ticket_tab:
        ticket_text = maintenance_ticket(technician_tool, technician_row, cause_table)
        st.markdown(ticket_text)
        assigned_to = st.text_input("Assign persistent ticket to", value=operator_name, key="route_assign")
        can_create_ticket = has_permission(operator_role, "create_ticket")
        if st.button("Create persistent ticket", disabled=not can_create_ticket, key="route_create_ticket"):
            create_persistent_ticket(technician_tool, technician_row, cause_table, assigned_to, operator_name, operator_role)
            st.success(f"Created persistent ticket for {technician_tool}.")
    with action_tab:
        action_log = read_db("SELECT * FROM technician_actions ORDER BY id DESC")
        if action_log.empty:
            st.info("No technician actions recorded yet.")
        else:
            st.dataframe(action_log, width="stretch", hide_index=True)
    with handoff_tab:
        handoff_text = shift_handoff(technician_tool, technician_row, cause_table)
        st.markdown(f"<div class='cmp-handoff'>{escape(handoff_text)}</div>", unsafe_allow_html=True)
    st.stop()

st.divider()

section_label("Industrial Product Console")
product_tab, ticket_board_tab, threshold_tab, ingestion_tab, audit_tab = st.tabs(
    [
        "Product Overview",
        "Persistent Ticket Board",
        "Threshold Settings",
        "Data Ingestion",
        "Audit Trail",
    ]
)

with product_tab:
    tickets = read_db("SELECT * FROM maintenance_tickets ORDER BY id DESC")
    actions = read_db("SELECT * FROM technician_actions ORDER BY id DESC")
    audit = read_db("SELECT * FROM audit_log ORDER BY id DESC LIMIT 100")
    open_ticket_count = int((tickets["status"] != "Closed").sum()) if not tickets.empty else 0
    card_grid(
        [
            kpi_card("Active user", operator_role, operator_name, "teal"),
            kpi_card("Open tickets", str(open_ticket_count), "Persistent SQLite work orders", "warn" if open_ticket_count else "good"),
            kpi_card("Action records", str(len(actions)), "Saved technician closeout history", "teal"),
            kpi_card("Audit events", str(len(audit)), "Traceable product activity", "teal"),
        ],
        "cmp-kpi-grid",
    )
    st.markdown(
        "<div class='cmp-action'><strong>Product posture:</strong> This layer adds persistence, role context, "
        "ticket lifecycle tracking, configurable thresholds, and an audit trail on top of the analytics dashboard.</div>",
        unsafe_allow_html=True,
    )

with ticket_board_tab:
    create_col, update_col = st.columns([1, 1])
    with create_col:
        st.markdown("#### Create Work Order")
        ticket_tool = st.selectbox("Ticket tool", options=tool_options, key="persistent_ticket_tool")
        ticket_row = features[features["tool_id"] == ticket_tool].sort_values("timestamp").tail(1).iloc[0]
        ticket_causes = root_cause_probabilities(ticket_row)
        assigned_to = st.text_input("Assign to", value=operator_name)
        can_create_ticket = has_permission(operator_role, "create_ticket")
        if not can_create_ticket:
            st.warning("Current role does not have permission to create tickets.")
        if st.button("Create persistent ticket", disabled=not can_create_ticket):
            create_persistent_ticket(
                ticket_tool,
                ticket_row,
                ticket_causes,
                assigned_to,
                operator_name,
                operator_role,
            )
            st.success(f"Created persistent ticket for {ticket_tool}.")

    with update_col:
        st.markdown("#### Update Ticket Status")
        tickets_for_update = read_db("SELECT * FROM maintenance_tickets ORDER BY id DESC")
        if tickets_for_update.empty:
            st.info("No persistent tickets have been created yet.")
        else:
            ticket_options = [
                f"{int(row['id'])} - {row['tool_id']} - {row['status']}"
                for _, row in tickets_for_update.iterrows()
            ]
            selected_ticket = st.selectbox("Ticket", ticket_options)
            selected_ticket_id = int(selected_ticket.split(" - ")[0])
            new_status = st.selectbox(
                "Status",
                ["New", "Assigned", "In Progress", "Waiting for parts", "Action Taken", "Verified", "Closed"],
            )
            closeout_notes = st.text_area("Closeout notes", value="Awaiting technician update.", height=90)
            can_update_ticket = has_permission(operator_role, "update_ticket")
            if not can_update_ticket:
                st.warning("Current role does not have permission to update tickets.")
            if st.button("Update persistent ticket", disabled=not can_update_ticket):
                update_ticket_status(
                    selected_ticket_id,
                    new_status,
                    closeout_notes,
                    operator_name,
                    operator_role,
                )
                st.success(f"Updated ticket {selected_ticket_id}.")

    tickets = read_db("SELECT * FROM maintenance_tickets ORDER BY id DESC")
    if tickets.empty:
        st.info("No persistent maintenance tickets yet.")
    else:
        st.markdown("#### Ticket Detail")
        detail_options = [
            f"{int(row['id'])} - {row['tool_id']} - {row['status']}"
            for _, row in tickets.iterrows()
        ]
        detail_ticket = st.selectbox("Open ticket detail", detail_options)
        detail_ticket_id = int(detail_ticket.split(" - ")[0])
        detail_row = tickets[tickets["id"] == detail_ticket_id].iloc[0]
        ticket_actions = read_db(
            "SELECT * FROM technician_actions WHERE ticket_id = ? ORDER BY id DESC",
            (detail_ticket_id,),
        )
        ticket_audit = read_db(
            "SELECT * FROM audit_log WHERE details LIKE ? ORDER BY id DESC",
            (f"%{detail_ticket_id}%",),
        )
        st.markdown(
            decision_card(
                f"Ticket {detail_ticket_id}: {detail_row['tool_id']}",
                [
                    f"Status: {detail_row['status']}",
                    f"Priority: {detail_row['priority']}",
                    f"Assigned to: {detail_row['assigned_to']}",
                    f"Root cause: {detail_row['root_cause']}",
                    f"Due: {detail_row['due_at']}",
                ],
            ),
            unsafe_allow_html=True,
        )
        if not ticket_actions.empty:
            st.dataframe(ticket_actions, width="stretch", hide_index=True)
        if not ticket_audit.empty:
            st.dataframe(ticket_audit, width="stretch", hide_index=True)
        st.markdown("#### Ticket Board")
        st.dataframe(tickets, width="stretch", hide_index=True)
        st.download_button(
            "Download ticket board CSV",
            data=csv_download(tickets),
            file_name="cmp_ticket_board.csv",
            mime="text/csv",
        )

with threshold_tab:
    thresholds = read_db("SELECT * FROM alert_thresholds ORDER BY threshold_key")
    st.dataframe(thresholds, width="stretch", hide_index=True)
    with st.form("threshold_update_form"):
        threshold_key = st.selectbox("Threshold", thresholds["threshold_key"].tolist())
        current_value = float(thresholds.loc[thresholds["threshold_key"] == threshold_key, "value"].iloc[0])
        new_value = st.number_input("New value", value=current_value, step=0.1)
        can_update_thresholds = has_permission(operator_role, "update_threshold")
        if not can_update_thresholds:
            st.warning("Only Process Engineer and Admin roles can update thresholds.")
        submitted_threshold = st.form_submit_button("Save threshold", disabled=not can_update_thresholds)
        if submitted_threshold:
            update_threshold(threshold_key, float(new_value), operator_name, operator_role)
            st.success(f"Updated {threshold_key}.")
    st.caption("These settings now drive the live feed simulator, scenario simulator, and uploaded CSV scoring.")

with ingestion_tab:
    can_ingest = has_permission(operator_role, "ingest_data")
    if not can_ingest:
        st.warning("Current role does not have permission to ingest data.")
    uploaded_file = st.file_uploader(
        "Upload CMP sensor CSV",
        type=["csv"],
        disabled=not can_ingest,
    )
    st.caption(
        "Required columns: timestamp, tool_id, vibration, slurry_flow_rate, pad_life_pct, "
        "retaining_ring_life_pct, wafer_removal_rate, process_drift_nm, alarm_count."
    )
    if uploaded_file is not None and can_ingest:
        try:
            uploaded_data = pd.read_csv(uploaded_file)
            scored_upload = score_uploaded_data(uploaded_data, threshold_values)
            audit_event(
                operator_name,
                operator_role,
                "data_ingested",
                f"Scored uploaded CSV with {len(scored_upload)} rows",
            )
            st.success(f"Scored {len(scored_upload):,} uploaded rows.")
            st.dataframe(scored_upload, width="stretch", hide_index=True)
            st.download_button(
                "Download scored upload CSV",
                data=csv_download(scored_upload),
                file_name="scored_cmp_upload.csv",
                mime="text/csv",
            )
        except Exception as exc:
            st.error(str(exc))

with audit_tab:
    audit = read_db("SELECT * FROM audit_log ORDER BY id DESC LIMIT 250")
    if audit.empty:
        st.info("No audit events yet. Create or update a ticket to generate trace history.")
    else:
        st.dataframe(audit, width="stretch", hide_index=True)
        st.download_button(
            "Download audit trail CSV",
            data=csv_download(audit),
            file_name="cmp_audit_trail.csv",
            mime="text/csv",
        )

if product_area == "Industrial ops":
    st.stop()

st.divider()

section_label("Fab Command Center")
impact_tab, live_tab, simulator_tab, replay_tab, quality_tab, executive_tab, report_tab = st.tabs(
    [
        "Downtime And Scrap Impact",
        "Live Feed Simulator",
        "Scenario Simulator",
        "Incident Replay",
        "Model Quality Monitor",
        "Executive Summary",
        "Operations Report",
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

with live_tab:
    live_tool = st.selectbox("Live feed tool", options=tool_options, index=0, key="live_feed_tool")
    live_feed = display_live_feed_rows(live_feed_rows, live_tool)
    using_persistent_stream = not live_feed.empty
    if live_feed.empty:
        live_feed = live_feed_simulation(features, live_tool, threshold_values)
    if live_feed.empty:
        st.info("No live feed simulation rows available.")
    else:
        latest_projection = live_feed.tail(1).iloc[0]
        live_label = "Persistent synthetic stream" if using_persistent_stream else "Projected demo feed"
        time_context = "latest generated sample" if using_persistent_stream else "next 6 hours"
        st.markdown(
            f"<div class='cmp-action'><strong>{escape(live_label)}:</strong> {escape(live_tool)} shows "
            f"{escape(str(latest_projection['rule_risk_level']).upper())} risk for the {time_context} "
            f"with {int(latest_projection['rule_risk_points'])} rule points.</div>",
            unsafe_allow_html=True,
        )
        st.altair_chart(live_feed_chart(live_feed), width="stretch")
        st.dataframe(
            live_feed[
                [
                    "timestamp",
                    "feed_type",
                    "rule_risk_level",
                    "rule_risk_points",
                    "vibration",
                    "slurry_flow_rate",
                    "wafer_removal_rate",
                    "process_drift_nm",
                ]
            ].sort_values("timestamp", ascending=False),
            width="stretch",
            hide_index=True,
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
            threshold_values,
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

with quality_tab:
    quality = model_quality_summary(predictions)
    overall_accuracy = (
        predictions["maintenance_state"] == predictions["predicted_maintenance_state"]
    ).mean()
    low_confidence_rows = int((predictions["model_confidence"] < 0.90).sum())
    card_grid(
        [
            kpi_card("Model accuracy", f"{overall_accuracy:.1%}", "Prediction agreement on generated test rows", "good"),
            kpi_card("Low-confidence rows", str(low_confidence_rows), "Rows below 90% confidence", "warn" if low_confidence_rows else "good"),
            kpi_card("Avg maint. probability", f"{predictions['prob_maintenance_needed'].mean():.1%}", "Mean maintenance-needed probability", "teal"),
            kpi_card("Review queue", str(int((predictions["review_priority"] != "normal_monitoring").sum())), "Model rows needing review", "warn"),
        ],
        "cmp-kpi-grid",
    )
    st.dataframe(quality, width="stretch", hide_index=True)
    quality_chart = (
        alt.Chart(quality)
        .mark_bar()
        .encode(
            x=alt.X("confidence_band:N", title="Confidence band"),
            y=alt.Y("accuracy:Q", title="Accuracy"),
            tooltip=[
                alt.Tooltip("confidence_band:N"),
                alt.Tooltip("rows:Q"),
                alt.Tooltip("accuracy:Q", format=".1%"),
                alt.Tooltip("avg_maintenance_probability:Q", format=".1%"),
            ],
        )
        .properties(height=300)
    )
    st.altair_chart(style_chart(quality_chart), width="stretch")
    st.caption("In a production deployment this page would monitor drift, false positives, confirmed root causes, and retraining triggers.")

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

with report_tab:
    tickets = read_db("SELECT * FROM maintenance_tickets ORDER BY id DESC")
    actions = read_db("SELECT * FROM technician_actions ORDER BY id DESC")
    pm_calendar = estimate_pm_calendar(features)
    report_text = professional_report(summary, tickets, actions, pm_calendar)
    st.markdown(report_text)
    st.download_button(
        "Download operations report",
        data=report_text.encode("utf-8"),
        file_name="cmp_operations_report.md",
        mime="text/markdown",
    )

if product_area == "Fab simulations":
    st.stop()

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
    persistent_tickets = read_db("SELECT id, tool_id, status FROM maintenance_tickets ORDER BY id DESC")
    with st.form("technician_action_form", clear_on_submit=True):
        form_col_a, form_col_b = st.columns(2)
        with form_col_a:
            technician_name = st.text_input("Technician", value=operator_name)
            ticket_link_options = ["No ticket link"]
            if not persistent_tickets.empty:
                ticket_link_options.extend(
                    [
                        f"{int(row['id'])} - {row['tool_id']} - {row['status']}"
                        for _, row in persistent_tickets.iterrows()
                    ]
                )
            ticket_link = st.selectbox("Link to ticket", ticket_link_options)
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
            if not has_permission(operator_role, "log_action"):
                st.error("Current role does not have permission to log technician actions.")
            else:
                linked_ticket_id = None if ticket_link == "No ticket link" else int(ticket_link.split(" - ")[0])
                add_persistent_action(
                    linked_ticket_id,
                    technician_tool,
                    technician_name,
                    action_taken,
                    finding,
                    str(technician_row["rule_risk_level"]),
                    risk_after,
                    next_step,
                    operator_name,
                    operator_role,
                )
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
                st.success("Action log entry added to the persistent product database.")

    action_log = read_db("SELECT * FROM technician_actions ORDER BY id DESC")
    if action_log.empty:
        st.info("No technician actions recorded yet.")
    else:
        st.dataframe(action_log, width="stretch", hide_index=True)
        latest_entry = action_log.iloc[0]
        if latest_entry["risk_before"] != latest_entry["risk_after"]:
            st.markdown(
                f"<div class='cmp-handoff'>Latest closeout changed {escape(str(latest_entry['tool_id']))} "
                f"from {escape(str(latest_entry['risk_before']))} risk to {escape(str(latest_entry['risk_after']))} risk.</div>",
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

if product_area == "Technician workflow":
    st.stop()

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
