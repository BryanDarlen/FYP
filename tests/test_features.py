"""
Tests for feature_engineering.build_features() — Phase 3 feature pipeline.

Covers:
  - Lag features (6 horizons)
  - Rolling means (3 windows)
  - Time features (hour, day-of-week, weekend flag)
  - FIRE_AND_DRY interaction
  - Forward-fill of short gaps; drop of unfillable deep gaps
  - Empty-input handling

Run directly:
    python tests/test_features.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src" / "pipeline"))

from feature_engineering import build_features


def main() -> int:
    base_hour = pd.Timestamp("2026-05-02 00:00:00")  # 2026-05-02 = Saturday

    def gen(station, hours, api_values, hot=0, rain=5):
        return pd.DataFrame({
            "STATION_ID":          [station] * hours,
            "HOUR_MYT":            [base_hour + pd.Timedelta(hours=i) for i in range(hours)],
            "API":                 api_values,
            "HOTSPOT_COUNT_100KM": [hot] * hours,
            "RAIN_FORECAST_SLOTS": [rain] * hours,
        })

    A = gen("STN_A", 30, [50 + i for i in range(30)])

    B_api = [50 + i for i in range(30)]; B_api[15] = np.nan
    B = gen("STN_B", 30, B_api)

    C_api = [50 + i for i in range(30)]
    for i in range(10, 15):
        C_api[i] = np.nan
    C = gen("STN_C", 30, C_api)

    FIRE = gen("STN_FIRE", 30, [60] * 30, hot=3, rain=0)

    df = pd.concat([A, B, C, FIRE], ignore_index=True)
    out = build_features(df)

    failures = []

    # STN_A row 24 (h24 = 2026-05-03 00:00, API=74) is the first surviving row
    a_first = out[out.STATION_ID == "STN_A"].iloc[0]
    expected_lags = {"API": 74, "API_lag1h": 73, "API_lag2h": 72, "API_lag3h": 71,
                     "API_lag6h": 68, "API_lag12h": 62, "API_lag24h": 50}
    for k, v in expected_lags.items():
        if a_first[k] != v:
            failures.append(f"STN_A first row {k}: expected {v}, got {a_first[k]}")

    expected_rolls = {"API_roll3h": 73.0, "API_roll6h": 71.5, "API_roll12h": 68.5}
    for k, v in expected_rolls.items():
        if abs(a_first[k] - v) > 1e-9:
            failures.append(f"STN_A first row {k}: expected {v}, got {a_first[k]}")

    # h24 = 2026-05-03 00:00 = Sunday midnight
    if a_first["HOUR_OF_DAY"] != 0:
        failures.append(f"HOUR_OF_DAY: expected 0, got {a_first['HOUR_OF_DAY']}")
    if a_first["DAY_OF_WEEK"] != 6:
        failures.append(f"DAY_OF_WEEK: expected 6 (Sun), got {a_first['DAY_OF_WEEK']}")
    if a_first["IS_WEEKEND"] != 1:
        failures.append(f"IS_WEEKEND: expected 1, got {a_first['IS_WEEKEND']}")

    fire_first = out[out.STATION_ID == "STN_FIRE"].iloc[0]
    if fire_first["FIRE_AND_DRY"] != 1:
        failures.append(f"STN_FIRE FIRE_AND_DRY: expected 1, got {fire_first['FIRE_AND_DRY']}")
    if a_first["FIRE_AND_DRY"] != 0:
        failures.append(f"STN_A FIRE_AND_DRY: expected 0, got {a_first['FIRE_AND_DRY']}")

    # STN_B 1-hour gap is fillable; expect 6 surviving rows like STN_A
    b_count = (out.STATION_ID == "STN_B").sum()
    if b_count != 6:
        failures.append(f"STN_B (1h gap): expected 6 rows, got {b_count}")

    # STN_C 5-hour gap unfillable; fewer surviving rows
    c_count = (out.STATION_ID == "STN_C").sum()
    if c_count >= 6:
        failures.append(f"STN_C (5h gap): expected fewer than 6 rows, got {c_count}")

    if "DATA_MISSING" not in out.columns:
        failures.append("DATA_MISSING column missing")

    # Empty input
    if not build_features(pd.DataFrame()).empty:
        failures.append("Empty input did not return empty DataFrame")

    if failures:
        print("FAIL:")
        for f in failures:
            print(f"  - {f}")
        return 1

    n_checks = len(expected_lags) + len(expected_rolls) + 7
    print(f"features: PASS ({n_checks}/{n_checks} scenarios)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
