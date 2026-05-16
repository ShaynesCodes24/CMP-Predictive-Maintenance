from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split


ROOT = Path(__file__).resolve().parents[1]
FEATURE_TABLE = ROOT / "data" / "processed" / "cmp_feature_table.csv"
PREDICTIONS = ROOT / "data" / "processed" / "cmp_model_predictions.csv"
MODEL_OUTPUT = ROOT / "models" / "cmp_maintenance_risk_model.joblib"
METRICS_REPORT = ROOT / "reports" / "model_metrics.md"
FEATURE_IMPORTANCE = ROOT / "reports" / "model_feature_importance.csv"

TARGET = "maintenance_state"
FEATURE_COLUMNS = [
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
    "platen_motor_current_rolling_6h",
    "carrier_motor_current_rolling_6h",
    "slurry_flow_rate_rolling_6h",
    "vibration_rolling_6h",
    "temperature_c_rolling_6h",
    "alarm_count_rolling_6h",
    "wafer_removal_rate_rolling_6h",
    "process_drift_nm_rolling_6h",
    "pad_life_pct",
    "retaining_ring_life_pct",
    "platen_current_delta_6h",
    "slurry_flow_delta_6h",
    "vibration_delta_6h",
    "removal_rate_delta_6h",
    "process_drift_delta_6h",
    "feature_platen_current_high",
    "feature_carrier_current_high",
    "feature_slurry_flow_low",
    "feature_vibration_high",
    "feature_pad_hours_high",
    "feature_alarm_burst",
    "feature_removal_rate_low",
    "feature_process_drift_high",
    "sensor_threshold_count",
]


def load_feature_table(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"Missing feature table: {path}. Run src/build_cmp_feature_table.py first."
        )

    data = pd.read_csv(path, parse_dates=["timestamp"])
    return data.sort_values(["tool_id", "timestamp"]).reset_index(drop=True)


def split_stratified(data: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    train, test = train_test_split(
        data,
        test_size=0.25,
        random_state=42,
        stratify=data[TARGET],
    )
    return train, test


def train_model(train: pd.DataFrame) -> Pipeline:
    model = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=500,
                    max_depth=None,
                    min_samples_leaf=1,
                    class_weight="balanced",
                    random_state=42,
                ),
            ),
        ]
    )
    model.fit(train[FEATURE_COLUMNS], train[TARGET])
    return model


def build_predictions(model: Pipeline, test: pd.DataFrame) -> pd.DataFrame:
    predictions = test[
        [
            "timestamp",
            "tool_id",
            "maintenance_state",
            "rule_risk_level",
            "rule_risk_points",
            "recommended_action",
            "wafer_removal_rate",
            "process_drift_nm",
            "maintenance_event",
        ]
    ].copy()
    predictions["predicted_maintenance_state"] = model.predict(test[FEATURE_COLUMNS])

    probabilities = pd.DataFrame(
        model.predict_proba(test[FEATURE_COLUMNS]),
        columns=[f"prob_{label}" for label in model.named_steps["classifier"].classes_],
    )
    predictions = pd.concat([predictions.reset_index(drop=True), probabilities], axis=1)
    probability_columns = [column for column in predictions.columns if column.startswith("prob_")]
    predictions["model_confidence"] = predictions[probability_columns].max(axis=1)
    predictions["review_priority"] = predictions.apply(review_priority, axis=1)
    return predictions


def review_priority(row: pd.Series) -> str:
    if row["predicted_maintenance_state"] == "maintenance_needed":
        return "urgent_review" if row["model_confidence"] >= 0.70 else "technician_review"
    if row["predicted_maintenance_state"] == "warning":
        return "trend_watch"
    return "normal_monitoring"


def feature_importance(model: Pipeline) -> pd.DataFrame:
    classifier = model.named_steps["classifier"]
    return (
        pd.DataFrame(
            {
                "feature": FEATURE_COLUMNS,
                "importance": classifier.feature_importances_,
            }
        )
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )


def dataframe_to_markdown(data: pd.DataFrame, include_index: bool = False) -> str:
    markdown_data = data.reset_index() if include_index else data.copy()
    headers = [str(column) for column in markdown_data.columns]
    rows = markdown_data.astype(str).values.tolist()

    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def write_metrics_report(
    train: pd.DataFrame,
    test: pd.DataFrame,
    predictions: pd.DataFrame,
    importance: pd.DataFrame,
) -> None:
    labels = sorted(test[TARGET].unique())
    report = classification_report(
        test[TARGET],
        predictions["predicted_maintenance_state"],
        labels=labels,
        zero_division=0,
    )
    matrix = confusion_matrix(
        test[TARGET],
        predictions["predicted_maintenance_state"],
        labels=labels,
    )
    accuracy = accuracy_score(test[TARGET], predictions["predicted_maintenance_state"])
    matrix_df = pd.DataFrame(matrix, index=labels, columns=labels)

    lines = [
        "# CMP Maintenance Risk Model Metrics",
        "",
        "This model predicts the CMP maintenance state from sensor readings, usage counters, and rolling trend features.",
        "",
        "## Training Setup",
        "",
        f"- Training rows: {len(train):,}",
        f"- Test rows: {len(test):,}",
        "- Split method: stratified 75/25 train-test split",
        "- Model: Random forest classifier with balanced class weights",
        "- Target: maintenance_state",
        "- Excluded from training: rule alert columns and recommended_action text",
        "- Added domain-threshold sensor features for explainable maintenance boundaries.",
        "- Prediction outputs include model confidence and a technician review priority.",
        "- Note: A pure time-based split was tested first, but the early timeline only contained normal rows. "
        "The stratified split is better for this starter demo because it lets the model learn all three states.",
        f"- Exact test accuracy: {accuracy:.3%}",
        "",
        "## Class Counts",
        "",
        "### Training",
        "",
        "```text",
        train[TARGET].value_counts().to_string(),
        "```",
        "",
        "### Test",
        "",
        "```text",
        test[TARGET].value_counts().to_string(),
        "```",
        "",
        "## Classification Report",
        "",
        "```text",
        report,
        "```",
        "",
        "## Confusion Matrix",
        "",
        "Rows are actual labels. Columns are predicted labels.",
        "",
        dataframe_to_markdown(matrix_df, include_index=True),
        "",
        "## Top Feature Importance",
        "",
        dataframe_to_markdown(importance.head(10), include_index=False),
        "",
        "## Technician Interpretation",
        "",
        "The strongest model inputs show which equipment trends are most useful for estimating maintenance risk. "
        "High-importance features are good candidates for dashboard trend charts and technician review.",
        "",
    ]

    METRICS_REPORT.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    data = load_feature_table(FEATURE_TABLE)
    train, test = split_stratified(data)
    model = train_model(train)
    predictions = build_predictions(model, test)
    importance = feature_importance(model)

    MODEL_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    PREDICTIONS.parent.mkdir(parents=True, exist_ok=True)
    METRICS_REPORT.parent.mkdir(parents=True, exist_ok=True)

    joblib.dump(model, MODEL_OUTPUT)
    predictions.to_csv(PREDICTIONS, index=False)
    importance.to_csv(FEATURE_IMPORTANCE, index=False)
    write_metrics_report(train, test, predictions, importance)

    accuracy = (
        predictions["maintenance_state"] == predictions["predicted_maintenance_state"]
    ).mean()
    print(f"Wrote model: {MODEL_OUTPUT}")
    print(f"Wrote predictions: {PREDICTIONS}")
    print(f"Wrote metrics report: {METRICS_REPORT}")
    print(f"Wrote feature importance: {FEATURE_IMPORTANCE}")
    print(f"Test accuracy: {accuracy:.3f}")


if __name__ == "__main__":
    main()
