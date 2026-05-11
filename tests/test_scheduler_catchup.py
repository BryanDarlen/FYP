"""
Tests for scheduler restart catch-up helpers.

Run directly:
    python tests/test_scheduler_catchup.py
"""
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src" / "pipeline"))

import scheduler


def main() -> int:
    failures = []
    current_hour = pd.Timestamp("2026-05-08 08:00:00")

    empty_window = scheduler.find_missing_history_window(pd.DataFrame(), current_hour)
    if empty_window is None:
        failures.append("empty timeseries should request a 24h warm-up window")
    else:
        if empty_window["start_hour"] != pd.Timestamp("2026-05-07 08:00:00"):
            failures.append("empty start_hour should be current-24h")
        if empty_window["end_hour"] != pd.Timestamp("2026-05-08 07:00:00"):
            failures.append("empty end_hour should be current-1h")
        if len(empty_window["missing_hours"]) != 24:
            failures.append("empty timeseries should have 24 completed missing hours")

    full_existing = pd.DataFrame({
        "HOUR_MYT": pd.date_range("2026-05-07 08:00:00", "2026-05-08 07:00:00", freq="h")
    })
    if scheduler.find_missing_history_window(full_existing, current_hour) is not None:
        failures.append("complete last-24h window should not request catch-up")

    partial_existing = pd.DataFrame({
        "HOUR_MYT": [
            pd.Timestamp("2026-05-07 08:00:00"),
            pd.Timestamp("2026-05-07 09:00:00"),
            pd.Timestamp("2026-05-08 07:00:00"),
        ]
    })
    partial_window = scheduler.find_missing_history_window(partial_existing, current_hour)
    if partial_window is None or len(partial_window["missing_hours"]) != 21:
        failures.append("partial last-24h window should identify missing middle hours")

    old_existing = pd.DataFrame({"HOUR_MYT": [pd.Timestamp("2026-05-06 00:00:00")]})
    old_window = scheduler.find_missing_history_window(old_existing, current_hour)
    if old_window is None or not old_window["truncated"]:
        failures.append("downtime older than 24h should be marked truncated")

    preview = pd.DataFrame({
        "STATION_ID": ["A", "B", "A", "B"],
        "HOUR_MYT": [
            pd.Timestamp("2026-05-08 06:00:00"),
            pd.Timestamp("2026-05-08 06:00:00"),
            pd.Timestamp("2026-05-08 07:00:00"),
            pd.Timestamp("2026-05-08 07:00:00"),
        ],
        "API": [40, 42, 41, 43],
        "DATA_FLAG": ["BACKFILLED_PREVIEW;"] * 4,
    })
    existing = pd.DataFrame({
        "STATION_ID": ["A"],
        "HOUR_MYT": [pd.Timestamp("2026-05-08 06:00:00")],
    })
    filtered = scheduler.filter_preview_to_missing_rows(
        preview,
        existing,
        [pd.Timestamp("2026-05-08 06:00:00")],
    )
    if len(filtered) != 1 or filtered.iloc[0]["STATION_ID"] != "B":
        failures.append("filter should keep only missing station-hour pairs")
    if "SCHEDULER_CATCHUP;" not in str(filtered.iloc[0]["DATA_FLAG"]):
        failures.append("catch-up rows should be clearly flagged")

    if failures:
        print("scheduler catchup: FAIL")
        for failure in failures:
            print(f" - {failure}")
        return 1

    print("scheduler catchup: PASS (6/6 scenarios)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
