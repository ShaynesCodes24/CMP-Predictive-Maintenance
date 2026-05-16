from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "raw" / "synthetic_cmp_tool_data.csv"


def make_tool_data(tool_id: str, days: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    timestamps = pd.date_range("2026-01-01", periods=days * 24, freq="h")
    hours = np.arange(len(timestamps))

    maintenance_interval = int(rng.integers(420, 480))
    first_maintenance = int(rng.integers(390, 430))
    maintenance_events = np.zeros(len(timestamps), dtype=int)
    maintenance_events[first_maintenance::maintenance_interval] = 1

    last_maintenance_hour = np.maximum.accumulate(
        np.where(maintenance_events == 1, hours, 0)
    )
    hours_since_maintenance = hours - last_maintenance_hour

    pad_hours = hours_since_maintenance + rng.normal(0, 1.8, len(timestamps))
    retaining_ring_hours = (
        hours_since_maintenance * 0.65 + rng.normal(0, 1.2, len(timestamps))
    )
    degradation = np.clip((pad_hours - 230) / 170, 0, None)

    platen_motor_current = 18 + degradation * 4 + rng.normal(0, 0.8, len(timestamps))
    carrier_motor_current = 12 + degradation * 2.5 + rng.normal(0, 0.6, len(timestamps))
    slurry_flow_rate = 210 - degradation * 18 + rng.normal(0, 4, len(timestamps))
    downforce_pressure = 4.2 + rng.normal(0, 0.08, len(timestamps))
    vibration = 0.35 + degradation * 0.45 + rng.normal(0, 0.05, len(timestamps))
    temperature = 22 + degradation * 2 + rng.normal(0, 0.7, len(timestamps))
    alarm_count = rng.poisson(0.08 + degradation * 0.5, len(timestamps))
    wafer_removal_rate = (
        105
        - degradation * 9
        + (slurry_flow_rate - 210) * 0.08
        + rng.normal(0, 1.1, len(timestamps))
    )
    process_drift_nm = np.abs(wafer_removal_rate - 105) + degradation * 4

    risk_score = (
        (platen_motor_current > 22).astype(int)
        + (carrier_motor_current > 14.5).astype(int)
        + (slurry_flow_rate < 190).astype(int)
        + (vibration > 0.7).astype(int)
        + (pad_hours > 360).astype(int)
        + (wafer_removal_rate < 96).astype(int)
        + (process_drift_nm > 10).astype(int)
        + (alarm_count >= 2).astype(int)
    )

    maintenance_state = np.select(
        [risk_score >= 4, risk_score >= 2],
        ["maintenance_needed", "warning"],
        default="normal",
    )

    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "tool_id": tool_id,
            "pad_hours": pad_hours.round(2),
            "retaining_ring_hours": retaining_ring_hours.round(2),
            "platen_motor_current": platen_motor_current.round(2),
            "carrier_motor_current": carrier_motor_current.round(2),
            "slurry_flow_rate": slurry_flow_rate.round(2),
            "downforce_pressure": downforce_pressure.round(3),
            "vibration": vibration.round(3),
            "temperature_c": temperature.round(2),
            "alarm_count": alarm_count,
            "wafer_removal_rate": wafer_removal_rate.round(2),
            "process_drift_nm": process_drift_nm.round(2),
            "maintenance_event": maintenance_events,
            "maintenance_state": maintenance_state,
        }
    )


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    frames = [
        make_tool_data("CMP-01", days=45, seed=7),
        make_tool_data("CMP-02", days=45, seed=21),
        make_tool_data("CMP-03", days=45, seed=42),
    ]
    data = pd.concat(frames, ignore_index=True)
    data.to_csv(OUTPUT, index=False)
    print(f"Wrote {len(data):,} rows to {OUTPUT}")


if __name__ == "__main__":
    main()
