# =============================================================================
# FYP: Predicting Air Pollution Levels in Malaysia Using Real Time Web Data
# PHASE 2 – Hourly Pipeline Scheduler
# Author : Bryan Quinn Darlen | TP073947
# =============================================================================
#
# WHAT THIS FILE DOES:
# --------------------
# Runs the full data pipeline (fetch → clean → merge → validate → save)
# once every 60 minutes and appends each snapshot to merged_timeseries.csv.
#
# HOW TO START:
#   python src/pipeline/scheduler.py
#
# HOW TO STOP:
#   Press Ctrl+C in the terminal. The current run will finish cleanly.
#
# OUTPUT FILES:
#   data/processed/merged_timeseries.csv  ← grows by ~68 rows per hour
#   data/logs/scheduler.log               ← full run history with timestamps
#
# =============================================================================

import asyncio
import logging
import os
import sys
import time
import traceback
from datetime import datetime, timezone, timedelta
from typing import Optional

import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

BASE_DIR      = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
LOG_DIR       = os.path.join(BASE_DIR, "data", "logs")
LOG_FILE      = os.path.join(LOG_DIR, "scheduler.log")

os.makedirs(LOG_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Logging — writes to both the terminal and the log file
# ---------------------------------------------------------------------------

LOG_HANDLERS = [logging.StreamHandler(sys.stdout)]
try:
    LOG_HANDLERS.insert(0, logging.FileHandler(LOG_FILE, encoding="utf-8"))
except OSError as exc:
    print(f"[LOG] Could not open scheduler log file; terminal logging only: {exc}")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=LOG_HANDLERS,
)
logger = logging.getLogger("pipeline")
logging.getLogger("httpx").setLevel(logging.WARNING)

# ---------------------------------------------------------------------------
# Pipeline imports
# ---------------------------------------------------------------------------

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests
from fetch_apims      import parse_state_ids, preprocess_apims
from fetch_metmalaysia import fetch_met_data, preprocess_met
from fetch_firms       import fetch_firms_data, preprocess_firms
from pipeline_merge    import (
    TIMESERIES_PATH,
    build_multisource_history_preview,
    merge_all,
    save_snapshot,
    validate_snapshot,
)

APIMS_URL = (
    "https://eqms.doe.gov.my/api3/publicmapproxy/PUBLIC_DISPLAY"
    "/CAQM_MCAQM_Current_Reading/MapServer/0/query"
    "?f=json&outFields=*&returnGeometry=false"
    "&spatialRel=esriSpatialRelIntersects&where=1%3D1"
)

# ---------------------------------------------------------------------------
# MYT timezone helper
# ---------------------------------------------------------------------------

MYT = timezone(timedelta(hours=8))

# On every cycle the scheduler checks the most recent completed hours before
# the live fetch. This lets a restarted laptop catch up after downtime without
# needing 24 continuous hours of local collection.
BACKFILL_LOOKBACK_HOURS = 24
BACKFILL_STATE_IDS = "1-16"


def now_myt() -> str:
    return datetime.now(MYT).strftime("%Y-%m-%d %H:%M MYT")


def current_hour_myt(now: Optional[object] = None) -> pd.Timestamp:
    """Return the current MYT hour as a timezone-naive pandas Timestamp."""
    if now is None:
        return pd.Timestamp.now(tz=MYT).tz_localize(None).floor("h")

    ts = pd.Timestamp(now)
    if ts.tzinfo is not None:
        ts = ts.tz_convert(MYT).tz_localize(None)
    return ts.floor("h")


def load_timeseries(path: str = TIMESERIES_PATH) -> pd.DataFrame:
    if not os.path.exists(path):
        return pd.DataFrame()
    return pd.read_csv(path, parse_dates=["HOUR_MYT"])


def find_missing_history_window(
    existing: pd.DataFrame,
    current_hour: pd.Timestamp,
    lookback_hours: int = BACKFILL_LOOKBACK_HOURS,
) -> Optional[dict]:
    """
    Identify missing completed hourly slots in the last N hours.

    The current hour is handled by the live fetch, so this function checks
    only completed hours: current-24h through current-1h.
    """
    current_hour = pd.Timestamp(current_hour).floor("h")
    end_hour = current_hour - pd.Timedelta(hours=1)
    start_bound = current_hour - pd.Timedelta(hours=lookback_hours)
    expected_hours = list(pd.date_range(start_bound, end_hour, freq="h"))
    if not expected_hours:
        return None

    last_hour = None
    existing_hours: set[pd.Timestamp] = set()
    if not existing.empty and "HOUR_MYT" in existing.columns:
        hours = pd.to_datetime(existing["HOUR_MYT"], errors="coerce").dt.floor("h").dropna()
        existing_hours = {pd.Timestamp(hour) for hour in hours}
        if existing_hours:
            last_hour = max(existing_hours)

    missing_hours = [hour for hour in expected_hours if hour not in existing_hours]
    if not missing_hours:
        return None

    truncated = bool(last_hour is not None and last_hour < (start_bound - pd.Timedelta(hours=1)))
    return {
        "start_hour": min(missing_hours),
        "end_hour": max(missing_hours),
        "fetch_end_hour": end_hour,
        "missing_hours": missing_hours,
        "last_hour": last_hour,
        "truncated": truncated,
    }


def _append_flag(values: pd.Series, flag: str) -> pd.Series:
    text = values.fillna("").astype(str)
    return text.where(text.str.contains(flag, regex=False), text + flag)


def filter_preview_to_missing_rows(
    preview: pd.DataFrame,
    existing: pd.DataFrame,
    missing_hours: list[pd.Timestamp],
) -> pd.DataFrame:
    """
    Keep only preview rows for missing STATION_ID + HOUR_MYT pairs.

    This protects scheduler/live rows that already exist while still allowing
    partial missing hours to be filled station by station.
    """
    if preview.empty or not missing_hours:
        return pd.DataFrame(columns=preview.columns)

    out = preview.copy()
    out["HOUR_MYT"] = pd.to_datetime(out["HOUR_MYT"], errors="coerce").dt.floor("h")
    target_hours = {pd.Timestamp(hour).floor("h") for hour in missing_hours}
    out = out[out["HOUR_MYT"].isin(target_hours)].copy()
    if out.empty:
        return out

    if not existing.empty and {"STATION_ID", "HOUR_MYT"}.issubset(existing.columns):
        existing_keys = existing[["STATION_ID", "HOUR_MYT"]].copy()
        existing_keys["HOUR_MYT"] = pd.to_datetime(
            existing_keys["HOUR_MYT"], errors="coerce"
        ).dt.floor("h")
        existing_keys = existing_keys.dropna(subset=["STATION_ID", "HOUR_MYT"]).drop_duplicates()
        out = out.merge(
            existing_keys.assign(_EXISTS=1),
            on=["STATION_ID", "HOUR_MYT"],
            how="left",
        )
        out = out[out["_EXISTS"].isna()].drop(columns=["_EXISTS"]).copy()

    if not out.empty:
        out["DATA_FLAG"] = _append_flag(
            out.get("DATA_FLAG", pd.Series(index=out.index)),
            "SCHEDULER_CATCHUP;",
        )
    return out


async def backfill_missing_history() -> bool:
    """
    Backfill missing completed hours from the last 24h before the live fetch.

    Returns True if rows were added, False if nothing was added or the backfill
    could not be completed. Live collection still proceeds after a failure.
    """
    existing = load_timeseries()
    current_hour = current_hour_myt()
    window = find_missing_history_window(existing, current_hour)

    if window is None:
        logger.info("[CATCHUP] No missing completed hours in the last 24h.")
        return False

    if window["truncated"]:
        logger.warning(
            "[CATCHUP] Downtime appears to exceed the 24h catch-up window. "
            "Only the latest 24 completed hours can be backfilled automatically."
        )

    logger.info(
        "[CATCHUP] Missing completed hour range: "
        f"{window['start_hour']} -> {window['end_hour']} "
        f"({len(window['missing_hours'])} hourly slots)."
    )

    try:
        preview = await build_multisource_history_preview(
            end_datetime=window["fetch_end_hour"].strftime("%Y-%m-%d %H:%M"),
            state_ids=parse_state_ids(BACKFILL_STATE_IDS),
        )
        rows_to_add = filter_preview_to_missing_rows(
            preview=preview,
            existing=existing,
            missing_hours=window["missing_hours"],
        )

        if rows_to_add.empty:
            logger.warning("[CATCHUP] Historical endpoints returned no new rows for the gap.")
            return False

        save_snapshot(rows_to_add)
        logger.info(f"[CATCHUP] Backfilled rows added: {len(rows_to_add):,}")
        return True

    except Exception:
        logger.error("[CATCHUP] Backfill failed; live fetch will still run.")
        logger.error(traceback.format_exc())
        return False


# ---------------------------------------------------------------------------
# One pipeline run
# ---------------------------------------------------------------------------

async def run_once() -> bool:
    """
    Executes one full fetch → merge → validate → save cycle.
    Returns True on success, False if any step failed.
    """
    logger.info("=" * 60)
    logger.info(f"Pipeline run started  |  {now_myt()}")
    logger.info("=" * 60)

    try:
        # 1. Fetch APIMS (synchronous requests call)
        logger.info("[1/4] Fetching APIMS...")
        resp = requests.get(APIMS_URL, timeout=60)
        resp.raise_for_status()
        df_apims = preprocess_apims(resp.json())
        logger.info(f"      APIMS rows: {len(df_apims)}")

        # 2. Fetch METMalaysia (async)
        logger.info("[2/4] Fetching METMalaysia...")
        raw_met = await fetch_met_data()
        df_met  = preprocess_met(raw_met)
        logger.info(f"      METMalaysia rows: {len(df_met)}")

        # 3. Fetch NASA FIRMS (async)
        logger.info("[3/4] Fetching NASA FIRMS...")
        raw_firms = await fetch_firms_data()
        df_firms  = preprocess_firms(raw_firms)
        logger.info(f"      FIRMS hotspot rows: {len(df_firms)}")

        # 4. Merge all three datasets
        logger.info("[4/4] Merging datasets...")
        df_merged = merge_all(df_apims, df_met, df_firms)
        logger.info(f"      Merged rows: {len(df_merged)}")

        # 5. Validate
        df_merged = validate_snapshot(df_merged)

        # 6. Append to timeseries CSV
        save_snapshot(df_merged)

        logger.info(f"Run completed successfully  |  {now_myt()}")
        return True

    except requests.exceptions.RequestException as e:
        logger.error(f"Network error during fetch: {e}")
    except Exception:
        logger.error("Unexpected error during pipeline run:")
        logger.error(traceback.format_exc())

    return False


# ---------------------------------------------------------------------------
# Main loop — runs once every INTERVAL_SECONDS (3600 = 1 hour)
# ---------------------------------------------------------------------------

INTERVAL_SECONDS = 3600  # change to 60 for quick testing


async def main() -> None:
    logger.info("=" * 60)
    logger.info("  FYP Hourly Pipeline Scheduler  -  PHASE 2 started")
    logger.info("=" * 60)
    logger.info(f"Interval : {INTERVAL_SECONDS} seconds ({INTERVAL_SECONDS // 60} minutes)")
    logger.info(f"Output   : data/processed/merged_timeseries.csv")
    logger.info(f"Log file : {LOG_FILE}")
    logger.info("")

    run_count   = 0
    fail_count  = 0

    while True:
        run_count += 1
        logger.info(f"--- Run #{run_count} ---")

        await backfill_missing_history()
        success = await run_once()
        if not success:
            fail_count += 1
            logger.warning(
                f"Run #{run_count} FAILED (total failures: {fail_count}). "
                f"Will retry in {INTERVAL_SECONDS // 60} minutes."
            )

        next_run = datetime.now(MYT) + timedelta(seconds=INTERVAL_SECONDS)
        logger.info(f"Next run scheduled at: {next_run.strftime('%Y-%m-%d %H:%M MYT')}")
        logger.info("")

        await asyncio.sleep(INTERVAL_SECONDS)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("")
        logger.info("Scheduler stopped by user (Ctrl+C). Goodbye.")
