"""
Phase 3 - Feature Engineering for Air-Quality Forecasting.

Exposes one function:

    build_features(df: pd.DataFrame) -> pd.DataFrame

It takes a merged hourly snapshot DataFrame (the rows that the scheduler
appends to merged_timeseries.csv) and returns the same data with
engineered columns added for the forecasting model.

The same function is used at TRAINING time (full CSV -> features.csv)
AND at INFERENCE time (last ~25 rows per station -> predict next hour
API). Sharing one implementation prevents train/serve skew, the most
common silent bug in production ML systems.

Run as a script to materialise data/processed/features.csv:

    python src/pipeline/feature_engineering.py
"""

import sys
import argparse
from pathlib import Path

import pandas as pd


# --- Paths -------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TIMESERIES_PATH        = PROJECT_ROOT / "data" / "processed" / "merged_timeseries.csv"
FEATURES_PATH          = PROJECT_ROOT / "data" / "processed" / "features.csv"
HISTORY_PREVIEW_PATH   = PROJECT_ROOT / "data" / "processed" / "multisource_history_preview.csv"
PREVIEW_FEATURES_PATH  = PROJECT_ROOT / "data" / "processed" / "features_history_preview.csv"


# --- Feature column lists (single source of truth) ---------------------------

LAG_HOURS     = (1, 2, 3, 6, 12, 24)
ROLL_WINDOWS  = (3, 6, 12)

LAG_COLS      = [f"API_lag{h}h"  for h in LAG_HOURS]
ROLL_COLS     = [f"API_roll{w}h" for w in ROLL_WINDOWS]
TIME_COLS     = ["HOUR_OF_DAY", "DAY_OF_WEEK", "IS_WEEKEND"]
QUALITY_COLS  = ["DATA_MISSING"]
INTERACT_COLS = ["FIRE_AND_DRY"]

REQUIRED_FEATURE_COLS = LAG_COLS + ROLL_COLS  # rows missing any of these are dropped


# --- Core function -----------------------------------------------------------

def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add engineered time-series features per station.

    New columns added (in this order):

      Lag features  : API_lag1h, _lag2h, _lag3h, _lag6h, _lag12h, _lag24h
      Rolling means : API_roll3h, _roll6h, _roll12h
      Time          : HOUR_OF_DAY (0-23), DAY_OF_WEEK (0=Mon..6=Sun), IS_WEEKEND
      Interaction   : FIRE_AND_DRY (1 if local hotspots > 0 AND no rain forecast)
      Data quality  : DATA_MISSING (1 if API was missing AND ffill could NOT recover)

    Behaviour:
      - Sorts input by (STATION_ID, HOUR_MYT) before computing.
      - Forward-fills API gaps of UP TO 2 hours per station.
      - Marks DATA_MISSING=1 only for rows where API was originally NaN AND
        ffill could not recover it (gap > 2 hours).
      - DROPS rows where any required lag/rolling feature is NaN. This satisfies
        the PLAN's "drop where API_lag24h is NaN" rule (early-history rows) AND
        also drops any later rows with NaN features arising from gaps that ffill
        could not bridge - those rows would crash scikit-learn at fit time.

    Returns a NEW DataFrame; the input is not modified.
    """
    if df.empty:
        return df.copy()

    df = df.copy()
    df["HOUR_MYT"] = pd.to_datetime(df["HOUR_MYT"])
    df = df.sort_values(["STATION_ID", "HOUR_MYT"]).reset_index(drop=True)

    # 1. Missing-value handling for API (BEFORE lag/rolling so they use filled values)
    was_missing = df["API"].isna()
    df["API"] = df.groupby("STATION_ID")["API"].ffill(limit=2)
    df["DATA_MISSING"] = (was_missing & df["API"].isna()).astype(int)

    # 2. Lag features (per station) - shift(N) returns NaN for the first N rows of each group
    api_grouped = df.groupby("STATION_ID")["API"]
    for h in LAG_HOURS:
        df[f"API_lag{h}h"] = api_grouped.shift(h)

    # 3. Rolling means (per station, window includes the current row)
    api_grouped = df.groupby("STATION_ID")["API"]
    for w in ROLL_WINDOWS:
        df[f"API_roll{w}h"] = api_grouped.transform(
            lambda x, w=w: x.rolling(window=w, min_periods=w).mean()
        )

    # 4. Time features extracted from HOUR_MYT
    df["HOUR_OF_DAY"] = df["HOUR_MYT"].dt.hour
    df["DAY_OF_WEEK"] = df["HOUR_MYT"].dt.dayofweek  # 0 = Monday
    df["IS_WEEKEND"]  = (df["DAY_OF_WEEK"] >= 5).astype(int)

    # 5. Fire-weather interaction (uses STATION-LOCAL hotspot count, not national)
    if {"HOTSPOT_COUNT_100KM", "RAIN_FORECAST_SLOTS"}.issubset(df.columns):
        hot  = df["HOTSPOT_COUNT_100KM"].fillna(0)
        rain = df["RAIN_FORECAST_SLOTS"].fillna(0)
        df["FIRE_AND_DRY"] = ((hot > 0) & (rain == 0)).astype(int)
    else:
        df["FIRE_AND_DRY"] = 0

    # 6. Drop rows that lack a full feature set
    df = df.dropna(subset=REQUIRED_FEATURE_COLS).reset_index(drop=True)

    return df


# --- CLI entry point: training-time materialisation --------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Build engineered API forecasting features.")
    parser.add_argument(
        "--input",
        default=str(TIMESERIES_PATH),
        help="Input merged CSV. Defaults to scheduler-collected merged_timeseries.csv.",
    )
    parser.add_argument(
        "--output",
        default=str(FEATURES_PATH),
        help="Output features CSV. Defaults to data/processed/features.csv.",
    )
    parser.add_argument(
        "--history-preview",
        action="store_true",
        help=(
            "Use the controlled historical preview input and write a separate "
            "features_history_preview.csv file."
        ),
    )
    args = parser.parse_args()

    input_path = HISTORY_PREVIEW_PATH if args.history_preview else Path(args.input)
    output_path = PREVIEW_FEATURES_PATH if args.history_preview else Path(args.output)

    if not input_path.exists():
        print(f"[FE] No data to process - {input_path} not found.")
        print("[FE] Start the scheduler first: python src/pipeline/scheduler.py")
        print("[FE] Or build the historical preview first:")
        print('[FE]   python src/pipeline/pipeline_merge.py --history-preview --datetime "YYYY-MM-DD HH:00"')
        sys.exit(0)

    print(f"[FE] Loading {input_path.name} ...")
    df = pd.read_csv(input_path, parse_dates=["HOUR_MYT"])
    n_in        = len(df)
    n_stations  = df["STATION_ID"].nunique()
    hour_min    = df["HOUR_MYT"].min()
    hour_max    = df["HOUR_MYT"].max()
    span_hours  = int((hour_max - hour_min).total_seconds() // 3600) + 1
    print(f"[FE]   Rows           : {n_in:,}")
    print(f"[FE]   Unique stations: {n_stations}")
    print(f"[FE]   Hour range     : {hour_min}  ..  {hour_max}  ({span_hours} hours)")
    if "DATA_FLAG" in df.columns:
        backfilled = df["DATA_FLAG"].fillna("").astype(str).str.contains("BACKFILLED_PREVIEW").sum()
        if backfilled:
            print(f"[FE]   Backfilled rows: {backfilled:,}  (controlled historical preview)")

    print("[FE] Building features ...")
    feats = build_features(df)
    n_out = len(feats)

    if n_out == 0:
        print("[FE] No rows survived feature engineering.")
        print("[FE] This is expected early in collection: each station needs at")
        print("[FE] least 25 consecutive hours of data before any row has a")
        print("[FE] valid API_lag24h. Keep the scheduler running and re-run this.")
        sys.exit(0)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    feats.to_csv(output_path, index=False)

    new_cols = LAG_COLS + ROLL_COLS + TIME_COLS + INTERACT_COLS + QUALITY_COLS
    print(f"[FE]   Output rows    : {n_out:,}  (dropped {n_in - n_out:,} early-history/gap rows)")
    print(f"[FE]   Total columns  : {len(feats.columns)}  (added {len(new_cols)} engineered)")
    print(f"[FE]   New features   : {', '.join(new_cols)}")
    print(f"[FE]   Saved to       : {output_path}")


if __name__ == "__main__":
    main()
