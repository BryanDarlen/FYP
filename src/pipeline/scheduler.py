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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("pipeline")

# ---------------------------------------------------------------------------
# Pipeline imports
# ---------------------------------------------------------------------------

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import requests
from fetch_apims      import preprocess_apims
from fetch_metmalaysia import fetch_met_data, preprocess_met
from fetch_firms       import fetch_firms_data, preprocess_firms
from pipeline_merge    import merge_all, validate_snapshot, save_snapshot

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


def now_myt() -> str:
    return datetime.now(MYT).strftime("%Y-%m-%d %H:%M MYT")


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
