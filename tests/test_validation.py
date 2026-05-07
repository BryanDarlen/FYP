"""
Tests for pipeline_merge.validate_snapshot() — Phase 2 validation logic.

Covers:
  - FLATLINE detection (API unchanged for 6 consecutive hours)
  - SPIKE detection (API change > 50 from previous hour)
  - Edge cases: gap in history, NaN previous API, no history, boundary at exactly 50

Run directly:
    python tests/test_validation.py

The script writes a synthetic merged_timeseries.csv into a temp directory,
points pipeline_merge.TIMESERIES_PATH at it, then exercises validate_snapshot
against a 1-hour "current" snapshot and asserts the right rows get flagged.
"""
import os
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src" / "pipeline"))

import pipeline_merge as pm


def main() -> int:
    current_hour  = pd.Timestamp("2026-05-05 12:00:00")
    t_minus_1     = current_hour - pd.Timedelta(hours=1)
    t_minus_3     = current_hour - pd.Timedelta(hours=3)
    prior_5_hours = [current_hour - pd.Timedelta(hours=h) for h in range(5, 0, -1)]

    history_rows = []

    # SPIKE_UP: prev=30, current=85 -> diff 55 > 50, FLAG
    history_rows.append({"STATION_ID": "SPIKE_UP", "HOUR_MYT": t_minus_1, "API": 30})
    # SPIKE_DOWN: prev=80, current=20 -> diff 60 > 50, FLAG
    history_rows.append({"STATION_ID": "SPIKE_DOWN", "HOUR_MYT": t_minus_1, "API": 80})
    # SMALL_CHANGE: prev=40, current=85 -> diff 45 <= 50, no flag
    history_rows.append({"STATION_ID": "SMALL_CHANGE", "HOUR_MYT": t_minus_1, "API": 40})
    # EXACT_50: prev=30, current=80 -> diff exactly 50, NOT flagged (strict >)
    history_rows.append({"STATION_ID": "EXACT_50", "HOUR_MYT": t_minus_1, "API": 30})
    # GAP: only prev row at t-3h, no row at t-1h, no flag possible
    history_rows.append({"STATION_ID": "GAP", "HOUR_MYT": t_minus_3, "API": 30})
    # NAN_PREV: previous API is NaN, no flag possible
    history_rows.append({"STATION_ID": "NAN_PREV", "HOUR_MYT": t_minus_1, "API": np.nan})
    # STUCK_42: 5 prior rows all 42, consecutive — FLATLINE flag
    for h in prior_5_hours:
        history_rows.append({"STATION_ID": "STUCK_42", "HOUR_MYT": h, "API": 42})
    # NEW_STATION_X: no history at all
    # (no rows added)

    history = pd.DataFrame(history_rows)

    current = pd.DataFrame([
        {"STATION_ID": "SPIKE_UP",      "HOUR_MYT": current_hour, "API": 85},
        {"STATION_ID": "SPIKE_DOWN",    "HOUR_MYT": current_hour, "API": 20},
        {"STATION_ID": "SMALL_CHANGE",  "HOUR_MYT": current_hour, "API": 85},
        {"STATION_ID": "EXACT_50",      "HOUR_MYT": current_hour, "API": 80},
        {"STATION_ID": "GAP",           "HOUR_MYT": current_hour, "API": 100},
        {"STATION_ID": "NAN_PREV",      "HOUR_MYT": current_hour, "API": 80},
        {"STATION_ID": "STUCK_42",      "HOUR_MYT": current_hour, "API": 42},
        {"STATION_ID": "NEW_STATION_X", "HOUR_MYT": current_hour, "API": 50},
    ])

    with tempfile.TemporaryDirectory() as d:
        fake_path = os.path.join(d, "merged_timeseries.csv")
        history.to_csv(fake_path, index=False)
        original_path = pm.TIMESERIES_PATH
        try:
            pm.TIMESERIES_PATH = fake_path
            result = pm.validate_snapshot(current)
        finally:
            pm.TIMESERIES_PATH = original_path

    flags = dict(zip(result["STATION_ID"], result["DATA_FLAG"]))
    checks = [
        ("SPIKE_UP",      "SPIKE",     True),
        ("SPIKE_DOWN",    "SPIKE",     True),
        ("SMALL_CHANGE",  "SPIKE",     False),
        ("EXACT_50",      "SPIKE",     False),
        ("GAP",           "SPIKE",     False),
        ("NAN_PREV",      "SPIKE",     False),
        ("NEW_STATION_X", "SPIKE",     False),
        ("STUCK_42",      "FLATLINE",  True),
        ("STUCK_42",      "SPIKE",     False),
    ]

    failures = []
    for station, tag, should_have in checks:
        got = tag in flags.get(station, "")
        if got != should_have:
            failures.append(f"{station}: {tag} expected {should_have}, got {got}")

    if failures:
        print("FAIL:")
        for f in failures:
            print(f"  - {f}")
        return 1

    print(f"validation: PASS ({len(checks)}/{len(checks)} scenarios)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
