# =============================================================================
# FYP: Predicting Air Pollution Levels in Malaysia Using Real Time Web Data
# Chapter 3.4 – Data Preparation: Combining APIMS + METMalaysia + NASA FIRMS
# Author : Bryan Quinn Darlen | TP073947
# =============================================================================
#
# HOW THIS FILE CONNECTS TO YOUR 3 FILES:
# -----------------------------------------
#   apimstrsfmvslztn.py     → provides preprocess_apims()
#                             uses requests (sync) — fetched directly here
#
#   metmalaysiatrsfmvslztn.py → provides fetch_met_data() + preprocess_met()
#                               uses httpx (async)
#
#   firmstrsfmvslztn.py     → provides fetch_firms_data() + preprocess_firms()
#                             uses httpx (async)
#
# ALL 3 FILES MUST BE IN THE SAME FOLDER AS THIS FILE.
#
# =============================================================================
#
# WHAT THIS FILE DOES (Plain English):
# -------------------------------------
# We have 3 separate cleaned datasets:
#   - APIMS        → tells us AIR QUALITY (API) at each station per hour
#   - METMalaysia  → tells us WEATHER (temperature, rain) at each state
#   - NASA FIRMS   → tells us WHERE and HOW INTENSE fires are burning
#
# The goal is to combine all 3 into ONE table so that every APIMS reading
# also has the weather and fire information for the same time and place.
# This combined table is what the forecast model will train on.
#
# MERGE STRATEGY:
# ----------------
#   Step A → Round all 3 datasets to the same 1-hour time slot
#   Step B → Join APIMS + METMalaysia by matching STATE + HOUR
#   Step C → Aggregate FIRMS hotspots per hour, attach to every row
#
# COLUMNS SELECTED AND WHY:
# --------------------------
#   FROM APIMS:
#     STATION_ID        → identifies which monitoring station
#     STATION_LOCATION  → human-readable station name
#     STATE_NAME        → ← JOIN KEY with METMalaysia
#     LATITUDE          → station coordinates
#     LONGITUDE         → station coordinates
#     DATETIME          → ← TIME JOIN KEY (rounded to hour)
#     API               → ⭐ TARGET — the value the model will predict
#     CLASS             → Good / Moderate / Unhealthy label
#
#   FROM METMalaysia:
#     STATE             → ← JOIN KEY with APIMS STATE_NAME
#     DATETIME_MYT      → ← TIME JOIN KEY (rounded to hour)
#     TEMPERATURE_C     → temperature affects how pollutants disperse
#     RAIN_FORECAST_SLOTS → rain washes out PM2.5, directly lowers API
#
#   FROM NASA FIRMS (summarised per hour, national level):
#     HOTSPOT_COUNT     → total fires detected in Malaysia that hour
#     FRP_MW_MEAN       → average fire intensity — higher = more smoke
#     FRP_MW_MAX        → strongest single fire that hour
#     HIGH_CONF_COUNT   → only high-confidence detections (most reliable)
#
#   FROM NASA FIRMS (summarised per hour, STATION-LOCAL within LOCAL_RADIUS_KM):
#     HOTSPOT_COUNT_100KM    → fires within 100 km of THIS station that hour
#     FRP_MW_MEAN_100KM      → mean intensity of those nearby fires
#     FRP_MW_MAX_100KM       → strongest nearby fire
#     HIGH_CONF_COUNT_100KM  → high-confidence nearby detections only
#   These give the model a geographically-relevant fire signal — a fire in
#   Sabah no longer affects the feature value seen by a station in Selangor.
#
# =============================================================================

import pandas as pd
import numpy as np
import requests
import sys
import os
import io
from typing import Optional

# Radius (km) within which a FIRMS hotspot is considered "local" to a station.
# 100 km is a practical default — smoke from fires can travel further, but
# the per-station signal weakens with distance. Adjust if you want a tighter
# (e.g. 50 km) or wider (e.g. 200 km) station-local fire feature.
LOCAL_RADIUS_KM = 100.0

OUTPUT_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "outputs")
)
os.makedirs(OUTPUT_DIR, exist_ok=True)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_apims import preprocess_apims, build_apims_history_preview, parse_state_ids
from fetch_metmalaysia import (
    fetch_met_data,
    fetch_wis2_history,
    preprocess_met,
    preprocess_wis2,
)
from fetch_firms import fetch_firms_data, preprocess_firms

# APIMS endpoint — fetched with requests (sync) directly in this file
APIMS_URL = (
    "https://eqms.doe.gov.my/api3/publicmapproxy/PUBLIC_DISPLAY"
    "/CAQM_MCAQM_Current_Reading/MapServer/0/query"
    "?f=json&outFields=*&returnGeometry=false"
    "&spatialRel=esriSpatialRelIntersects&where=1%3D1"
)

HISTORY_PREVIEW_PATH = os.path.normpath(
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "..", "data", "processed", "multisource_history_preview.csv",
    )
)


# =============================================================================
# STEP 1 — SELECT COLUMNS FROM EACH DATASET
# =============================================================================
# Only keep the columns that are useful for forecasting.
# Everything else is dropped to keep the merged table clean.

def select_apims_columns(df: pd.DataFrame) -> pd.DataFrame:
    keep = [
        "STATION_ID",        
        "STATION_LOCATION",  
        "STATE_NAME",        
        "LATITUDE",
        "LONGITUDE",
        "DATETIME",          
        "API",              
        "CLASS",             
    ]
    return df[[c for c in keep if c in df.columns]].copy()


def select_met_columns(df: pd.DataFrame) -> pd.DataFrame:
    keep = [
        "STATE",
        "DATETIME_MYT",   
        "TEMPERATURE_C",   
        "RAIN_FORECAST_SLOTS",
    ]
    return df[[c for c in keep if c in df.columns]].copy()


def select_firms_columns(df: pd.DataFrame) -> pd.DataFrame:
    keep = [
        "ACQ_DATETIME_MYT",
        "LATITUDE",       # needed for station-local distance filter
        "LONGITUDE",      # needed for station-local distance filter
        "FRP_MW",
        "CONFIDENCE",
    ]
    return df[[c for c in keep if c in df.columns]].copy()


# =============================================================================
# STEP 2 — ROUND ALL TIMESTAMPS TO THE NEAREST HOUR
# =============================================================================
# APIMS is hourly. METMalaysia is a snapshot. FIRMS has satellite pass times.
# We floor all of them to the same hour so the join keys match.
# Example: 14:47 → 14:00,  14:32 → 14:00,  both match correctly.

def round_to_hour(dt_series: pd.Series) -> pd.Series:
    return pd.to_datetime(dt_series).dt.floor("h")


# =============================================================================
# STEP 3 — AGGREGATE NASA FIRMS TO ONE ROW PER HOUR
# =============================================================================
# FIRMS gives one row per hotspot. We collapse all hotspots detected in
# the same hour into one summary row, then attach it to every APIMS row
# for that hour. This is called a "national-level" fire summary.

def aggregate_firms_hourly(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["HOUR_MYT"]    = round_to_hour(df["ACQ_DATETIME_MYT"])
    df["IS_HIGH_CONF"] = df["CONFIDENCE"].astype(str).str.lower() == "h"

    hourly = df.groupby("HOUR_MYT").agg(
        HOTSPOT_COUNT   =("FRP_MW",        "count"),
        FRP_MW_MEAN     =("FRP_MW",        "mean"),
        FRP_MW_MAX      =("FRP_MW",        "max"),
        HIGH_CONF_COUNT =("IS_HIGH_CONF",  "sum"),
    ).reset_index()

    hourly["FRP_MW_MEAN"] = hourly["FRP_MW_MEAN"].round(2)
    hourly["FRP_MW_MAX"]  = hourly["FRP_MW_MAX"].round(2)
    return hourly


# =============================================================================
# STEP 3b — AGGREGATE NASA FIRMS PER STATION (station-local fire signal)
# =============================================================================
# The national HOTSPOT_COUNT above attaches the same value to every station,
# so a fire in Sabah inflates the feature seen by a station in Selangor.
# Here we count only the hotspots within LOCAL_RADIUS_KM of each station.
#
# Method:
#   1. Cross-join FIRMS hotspots × APIMS stations (small: ~hundreds × 68)
#   2. Compute great-circle (haversine) distance for each pair
#   3. Keep only pairs within LOCAL_RADIUS_KM
#   4. Group by (STATION_ID, HOUR_MYT) and aggregate

def haversine_km(lat1, lon1, lat2, lon2) -> np.ndarray:
    """Great-circle distance in km between two lat/lon points (vectorised)."""
    R = 6371.0  # Earth radius in km
    lat1_r = np.radians(lat1)
    lat2_r = np.radians(lat2)
    dlat   = np.radians(lat2 - lat1)
    dlon   = np.radians(lon2 - lon1)
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1_r) * np.cos(lat2_r) * np.sin(dlon / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))


def aggregate_firms_per_station(
    firms: pd.DataFrame,
    stations: pd.DataFrame,
    radius_km: float = LOCAL_RADIUS_KM,
) -> pd.DataFrame:
    """
    Returns one row per (STATION_ID, HOUR_MYT) with hotspot counts/intensities
    restricted to fires within `radius_km` of that specific station.

    `stations` must have: STATION_ID, LATITUDE, LONGITUDE (one row per station).
    `firms` must have: ACQ_DATETIME_MYT, LATITUDE, LONGITUDE, FRP_MW, CONFIDENCE.
    """
    cols_out = [
        "STATION_ID", "HOUR_MYT",
        "HOTSPOT_COUNT_100KM", "FRP_MW_MEAN_100KM",
        "FRP_MW_MAX_100KM",   "HIGH_CONF_COUNT_100KM",
    ]
    if firms.empty or stations.empty:
        return pd.DataFrame(columns=cols_out)

    f = firms.copy()
    f["HOUR_MYT"]     = round_to_hour(f["ACQ_DATETIME_MYT"])
    f["IS_HIGH_CONF"] = f["CONFIDENCE"].astype(str).str.lower() == "h"

    # Cross-join (Cartesian product). Cheap at this scale: ~hundreds × 68.
    s = stations[["STATION_ID", "LATITUDE", "LONGITUDE"]].rename(
        columns={"LATITUDE": "STATION_LAT", "LONGITUDE": "STATION_LON"}
    )
    pairs = f.merge(s, how="cross")

    pairs["DIST_KM"] = haversine_km(
        pairs["LATITUDE"].to_numpy(),  pairs["LONGITUDE"].to_numpy(),
        pairs["STATION_LAT"].to_numpy(), pairs["STATION_LON"].to_numpy(),
    )
    pairs = pairs[pairs["DIST_KM"] <= radius_km]

    if pairs.empty:
        return pd.DataFrame(columns=cols_out)

    agg = pairs.groupby(["STATION_ID", "HOUR_MYT"]).agg(
        HOTSPOT_COUNT_100KM   =("FRP_MW",       "count"),
        FRP_MW_MEAN_100KM     =("FRP_MW",       "mean"),
        FRP_MW_MAX_100KM      =("FRP_MW",       "max"),
        HIGH_CONF_COUNT_100KM =("IS_HIGH_CONF", "sum"),
    ).reset_index()

    agg["FRP_MW_MEAN_100KM"] = agg["FRP_MW_MEAN_100KM"].round(2)
    agg["FRP_MW_MAX_100KM"]  = agg["FRP_MW_MAX_100KM"].round(2)
    return agg


# =============================================================================
# STEP 4 — CLEAN STATE NAMES SO THE JOIN WORKS
# =============================================================================
# APIMS might say "W.P. Kuala Lumpur", METMalaysia might say "Kuala Lumpur".
# We clean both to lowercase + remove common prefixes so they match.

def clean_state(s: str) -> str:
    s = str(s).lower().strip()
    for prefix in ["w.p. ", "w.p.", "wilayah persekutuan ", "wp "]:
        if s.startswith(prefix):
            s = s[len(prefix):]
    return s.strip()


# =============================================================================
# STEP 5 — MERGE ALL THREE DATASETS INTO ONE TABLE
# =============================================================================

def merge_all(
    df_apims: pd.DataFrame,
    df_met:   pd.DataFrame,
    df_firms: pd.DataFrame,
) -> pd.DataFrame:

    apims = select_apims_columns(df_apims)
    met   = select_met_columns(df_met)
    firms = select_firms_columns(df_firms)

    # Bug 1 fix — remove MYT_OFFSET, APIMS datetime is already MYT
    apims["HOUR_MYT"] = round_to_hour(apims["DATETIME"])
    met["HOUR_MYT"]   = round_to_hour(met["DATETIME_MYT"])

    apims["STATE_CLEAN"] = apims["STATE_NAME"].apply(clean_state)
    met["STATE_CLEAN"]   = met["STATE"].apply(clean_state)

    if firms.empty:
        firms_hourly = pd.DataFrame(columns=[
            "HOUR_MYT",
            "HOTSPOT_COUNT",
            "FRP_MW_MEAN",
            "FRP_MW_MAX",
            "HIGH_CONF_COUNT"
        ])
        firms_local = pd.DataFrame(columns=[
            "STATION_ID", "HOUR_MYT",
            "HOTSPOT_COUNT_100KM", "FRP_MW_MEAN_100KM",
            "FRP_MW_MAX_100KM",   "HIGH_CONF_COUNT_100KM",
        ])
    else:
        firms_hourly = aggregate_firms_hourly(firms)
        # Build station-local fire summary using each station's lat/lon
        stations = apims[["STATION_ID", "LATITUDE", "LONGITUDE"]].drop_duplicates()
        firms_local = aggregate_firms_per_station(firms, stations, LOCAL_RADIUS_KM)

    merged = pd.merge(
        apims,
        met.drop(columns=["STATE", "DATETIME_MYT"], errors="ignore"),
        on=["STATE_CLEAN", "HOUR_MYT"],
        how="left",
    )

    # ── F) JOIN 2: merged ← FIRMS hourly summary (by HOUR only) ──────────────
    # Every APIMS row for the same hour gets the same national fire summary.
    # This still has value for transboundary/regional haze episodes.
    merged = pd.merge(
        merged,
        firms_hourly,
        on="HOUR_MYT",
        how="left",
    )

    # ── F2) JOIN 3: merged ← FIRMS station-local summary (by STATION + HOUR) ─
    # Each station gets a fire count restricted to fires within LOCAL_RADIUS_KM
    # of that specific station. This is the geographically-relevant signal.
    merged = pd.merge(
        merged,
        firms_local,
        on=["STATION_ID", "HOUR_MYT"],
        how="left",
    )

    # ── G) Fill missing FIRMS columns with 0 (no fires = 0 hotspots) ─────────
    for col in [
        "HOTSPOT_COUNT", "FRP_MW_MEAN", "FRP_MW_MAX", "HIGH_CONF_COUNT",
        "HOTSPOT_COUNT_100KM", "FRP_MW_MEAN_100KM",
        "FRP_MW_MAX_100KM",   "HIGH_CONF_COUNT_100KM",
    ]:
        if col in merged.columns:
            merged[col] = pd.to_numeric(merged[col], errors="coerce").fillna(0)

    # ── H) Drop helper columns no longer needed ───────────────────────────────
    merged.drop(columns=["STATE_CLEAN", "DATETIME"], inplace=True, errors="ignore")

    # ── I) Sort and reset index ────────────────────────────────────────────────
    merged.sort_values(["STATION_ID", "HOUR_MYT"], inplace=True)
    merged.reset_index(drop=True, inplace=True)

    return merged


# =============================================================================
# STEP 5b - MULTI-SOURCE HISTORY PREVIEW
# =============================================================================
# This is a controlled backfill helper. It does not write into
# merged_timeseries.csv. APIMS can provide recent hourly history, FIRMS can be
# queried by date, but METMalaysia's current endpoint only exposes a current
# snapshot. Any incomplete source coverage remains visible in DATA_FLAG.

def _remove_data_flag(flags: pd.Series, flag: str) -> pd.Series:
    return flags.fillna("").astype(str).str.replace(flag, "", regex=False)


def _add_data_flag(flags: pd.Series, flag: str) -> pd.Series:
    values = flags.fillna("").astype(str)
    return values.where(values.str.contains(flag, regex=False), values + flag)


def _attach_wis2_weather_by_nearest_station(
    preview: pd.DataFrame,
    wis2: pd.DataFrame,
) -> pd.DataFrame:
    """
    Attach WIS2 station observations to APIMS rows by nearest station.

    WIS2 historical data does not use the current METMalaysia data.json
    schema, so a direct STATE + HOUR join would be misleading. Nearest-station
    matching keeps the source observable and spatially defensible.
    """
    required_wis2 = {
        "WIGOS_STATION_ID", "HOUR_MYT", "LATITUDE", "LONGITUDE",
        "TEMPERATURE_C", "RAIN_FORECAST_SLOTS",
    }
    required_preview = {"STATION_ID", "LATITUDE", "LONGITUDE", "HOUR_MYT"}
    if wis2.empty or not required_wis2.issubset(wis2.columns):
        return preview
    if preview.empty or not required_preview.issubset(preview.columns):
        return preview

    apims_stations = (
        preview[["STATION_ID", "LATITUDE", "LONGITUDE"]]
        .dropna(subset=["STATION_ID", "LATITUDE", "LONGITUDE"])
        .drop_duplicates(subset=["STATION_ID"])
        .rename(columns={"LATITUDE": "APIMS_LATITUDE", "LONGITUDE": "APIMS_LONGITUDE"})
    )
    wis2_stations = (
        wis2[["WIGOS_STATION_ID", "LATITUDE", "LONGITUDE"]]
        .dropna(subset=["WIGOS_STATION_ID", "LATITUDE", "LONGITUDE"])
        .drop_duplicates(subset=["WIGOS_STATION_ID"])
        .rename(columns={"LATITUDE": "WIS2_LATITUDE", "LONGITUDE": "WIS2_LONGITUDE"})
    )
    if apims_stations.empty or wis2_stations.empty:
        return preview

    pairs = apims_stations.merge(wis2_stations, how="cross")
    pairs["MET_DISTANCE_KM"] = haversine_km(
        pairs["APIMS_LATITUDE"].to_numpy(),
        pairs["APIMS_LONGITUDE"].to_numpy(),
        pairs["WIS2_LATITUDE"].to_numpy(),
        pairs["WIS2_LONGITUDE"].to_numpy(),
    )
    nearest = (
        pairs.sort_values(["STATION_ID", "MET_DISTANCE_KM"])
        .drop_duplicates(subset=["STATION_ID"])
        [["STATION_ID", "WIGOS_STATION_ID", "MET_DISTANCE_KM"]]
    )

    met_join = wis2.merge(nearest, on="WIGOS_STATION_ID", how="inner")
    met_join = (
        met_join[[
            "STATION_ID", "HOUR_MYT", "TEMPERATURE_C", "RAIN_FORECAST_SLOTS",
            "MET_DISTANCE_KM",
        ]]
        .drop_duplicates(subset=["STATION_ID", "HOUR_MYT"], keep="last")
    )

    out = preview.drop(columns=["TEMPERATURE_C", "RAIN_FORECAST_SLOTS"], errors="ignore")
    out = out.merge(met_join, on=["STATION_ID", "HOUR_MYT"], how="left")
    return out


async def build_multisource_history_preview(
    end_datetime: Optional[str] = None,
    state_ids: Optional[list[int]] = None,
) -> pd.DataFrame:
    """
    Build a preview table shaped like merged_timeseries.csv using:
      - APIMS recent hourly history
      - WIS2 synop-hourly observations where station matching works
      - NASA FIRMS historical rows for the APIMS preview date window

    Rows remain flagged when weather or FIRMS evidence is unavailable.
    """
    preview = build_apims_history_preview(end_datetime=end_datetime, state_ids=state_ids)
    if preview.empty:
        return preview

    preview = preview.copy()
    preview["HOUR_MYT"] = pd.to_datetime(preview["HOUR_MYT"], errors="coerce")
    preview["DATA_FLAG"] = _remove_data_flag(preview["DATA_FLAG"], "BACKFILLED_APIMS_ONLY;")
    preview["DATA_FLAG"] = _add_data_flag(preview["DATA_FLAG"], "BACKFILLED_PREVIEW;")
    hour_min = preview["HOUR_MYT"].min()
    hour_max = preview["HOUR_MYT"].max()

    # WIS2 synop-hourly: historical station observations, matched by nearest
    # WIS2 station to each APIMS station. This is a different data product
    # from the current METMalaysia data.json snapshot.
    try:
        raw_wis2 = await fetch_wis2_history(hour_min, hour_max)
        wis2 = preprocess_wis2(raw_wis2)
        if not wis2.empty:
            wis2["HOUR_MYT"] = round_to_hour(wis2["HOUR_MYT"])
            preview = _attach_wis2_weather_by_nearest_station(preview, wis2)

            weather_ok = preview["TEMPERATURE_C"].notna() & preview["RAIN_FORECAST_SLOTS"].notna()
            preview.loc[weather_ok, "DATA_FLAG"] = _remove_data_flag(
                preview.loc[weather_ok, "DATA_FLAG"], "WEATHER_MISSING;"
            )
            preview.loc[weather_ok, "DATA_FLAG"] = _add_data_flag(
                preview.loc[weather_ok, "DATA_FLAG"], "WIS2_SYNOP_OBSERVED;"
            )
    except Exception as exc:
        print(f"[HISTORY PREVIEW] WIS2 synop-hourly fetch skipped: {exc}")

    # Fallback: current METMalaysia snapshot only where the timestamp matches.
    # This keeps current-hour preview rows usable if WIS2 is unavailable.
    try:
        preview["_WEATHER_WAS_MISSING"] = (
            preview["TEMPERATURE_C"].isna() | preview["RAIN_FORECAST_SLOTS"].isna()
        )
        raw_met = await fetch_met_data()
        met = select_met_columns(preprocess_met(raw_met))
        if not met.empty and "DATETIME_MYT" in met.columns:
            met["HOUR_MYT"] = round_to_hour(met["DATETIME_MYT"])
            met["STATE_CLEAN"] = met["STATE"].apply(clean_state)
            met = met.drop(columns=["STATE", "DATETIME_MYT"], errors="ignore")

            preview["STATE_CLEAN"] = preview["STATE_NAME"].apply(clean_state)
            preview = preview.merge(
                met,
                on=["STATE_CLEAN", "HOUR_MYT"],
                how="left",
                suffixes=("", "_MET"),
            )
            for col in ["TEMPERATURE_C", "RAIN_FORECAST_SLOTS"]:
                met_col = f"{col}_MET"
                if met_col in preview.columns:
                    preview[col] = preview[col].where(preview[col].notna(), preview[met_col])
                    preview.drop(columns=[met_col], inplace=True)
            preview.drop(columns=["STATE_CLEAN"], inplace=True, errors="ignore")

            current_weather_ok = (
                preview["_WEATHER_WAS_MISSING"]
                & preview["TEMPERATURE_C"].notna()
                & preview["RAIN_FORECAST_SLOTS"].notna()
            )
            preview.loc[current_weather_ok, "DATA_FLAG"] = _remove_data_flag(
                preview.loc[current_weather_ok, "DATA_FLAG"], "WEATHER_MISSING;"
            )
            preview.loc[current_weather_ok, "DATA_FLAG"] = _add_data_flag(
                preview.loc[current_weather_ok, "DATA_FLAG"], "MET_CURRENT_MATCHED;"
            )
        preview.drop(columns=["_WEATHER_WAS_MISSING"], inplace=True, errors="ignore")
    except Exception as exc:
        preview.drop(columns=["_WEATHER_WAS_MISSING"], inplace=True, errors="ignore")
        print(f"[HISTORY PREVIEW] METMalaysia fetch skipped: {exc}")

    # NASA FIRMS: pull historical window, then aggregate like the live merge.
    firms_cols = [
        "HOTSPOT_COUNT", "FRP_MW_MEAN", "FRP_MW_MAX", "HIGH_CONF_COUNT",
        "HOTSPOT_COUNT_100KM", "FRP_MW_MEAN_100KM",
        "FRP_MW_MAX_100KM", "HIGH_CONF_COUNT_100KM",
    ]
    try:
        start_date = hour_min.strftime("%Y-%m-%d")
        day_range = max(1, min(10, (hour_max.normalize() - hour_min.normalize()).days + 1))
        raw_firms = await fetch_firms_data(day_range=day_range, start_date=start_date)
        firms = select_firms_columns(preprocess_firms(raw_firms))

        if not firms.empty:
            firms["HOUR_MYT"] = round_to_hour(firms["ACQ_DATETIME_MYT"])
            firms = firms[(firms["HOUR_MYT"] >= hour_min) & (firms["HOUR_MYT"] <= hour_max)]

        if firms.empty:
            for col in firms_cols:
                preview[col] = 0
        else:
            firms_hourly = aggregate_firms_hourly(firms)
            stations = preview[["STATION_ID", "LATITUDE", "LONGITUDE"]].drop_duplicates()
            firms_local = aggregate_firms_per_station(firms, stations, LOCAL_RADIUS_KM)

            preview = preview.drop(columns=firms_cols, errors="ignore")
            preview = preview.merge(firms_hourly, on="HOUR_MYT", how="left")
            preview = preview.merge(firms_local, on=["STATION_ID", "HOUR_MYT"], how="left")
            for col in firms_cols:
                preview[col] = pd.to_numeric(preview[col], errors="coerce").fillna(0)

        preview["DATA_FLAG"] = _remove_data_flag(preview["DATA_FLAG"], "FIRMS_MISSING;")
        preview["DATA_FLAG"] = _add_data_flag(preview["DATA_FLAG"], "FIRMS_HISTORY;")
    except Exception as exc:
        print(f"[HISTORY PREVIEW] NASA FIRMS fetch skipped: {exc}")

    for col in [
        "STATION_ID", "STATION_LOCATION", "STATE_NAME", "LATITUDE", "LONGITUDE",
        "API", "CLASS", "HOUR_MYT", "TEMPERATURE_C", "RAIN_FORECAST_SLOTS",
        "HOTSPOT_COUNT", "FRP_MW_MEAN", "FRP_MW_MAX", "HIGH_CONF_COUNT",
        "HOTSPOT_COUNT_100KM", "FRP_MW_MEAN_100KM", "FRP_MW_MAX_100KM",
        "HIGH_CONF_COUNT_100KM", "DATA_FLAG",
    ]:
        if col not in preview.columns:
            preview[col] = pd.NA

    preview = preview[[
        "STATION_ID", "STATION_LOCATION", "STATE_NAME", "LATITUDE", "LONGITUDE",
        "API", "CLASS", "HOUR_MYT", "TEMPERATURE_C", "RAIN_FORECAST_SLOTS",
        "HOTSPOT_COUNT", "FRP_MW_MEAN", "FRP_MW_MAX", "HIGH_CONF_COUNT",
        "HOTSPOT_COUNT_100KM", "FRP_MW_MEAN_100KM", "FRP_MW_MAX_100KM",
        "HIGH_CONF_COUNT_100KM", "DATA_FLAG",
    ]]
    return preview.sort_values(["STATION_ID", "HOUR_MYT"]).reset_index(drop=True)


def save_history_preview(df: pd.DataFrame, output_path: str = HISTORY_PREVIEW_PATH) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"[HISTORY PREVIEW] Saved: {output_path}")
    print(f"[HISTORY PREVIEW] Rows: {len(df):,}")
    if not df.empty:
        print(f"[HISTORY PREVIEW] Stations: {df['STATION_ID'].nunique()}")
        print(f"[HISTORY PREVIEW] Hours: {df['HOUR_MYT'].nunique()}")
        print(f"[HISTORY PREVIEW] Range: {df['HOUR_MYT'].min()} -> {df['HOUR_MYT'].max()}")
        flag_counts = df["DATA_FLAG"].fillna("").astype(str).value_counts()
        print("[HISTORY PREVIEW] DATA_FLAG counts:")
        for flag, count in flag_counts.items():
            label = flag if flag else "(clean)"
            print(f"[HISTORY PREVIEW]   {label}: {count}")


# =============================================================================
# STEP 6 — DATA UNDERSTANDING: MERGED DATASET
# =============================================================================

def understand_merged(df: pd.DataFrame) -> None:
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", None)
    pd.set_option("display.max_rows", None)

    output = io.StringIO()

    def p(text=""):
        print(text, file=output)

    p("=== Merged Dataset ===")
    p(f"Rows: {df.shape[0]}  Cols: {df.shape[1]}")
    p(df.head(5).to_string())
    p("\n=== [DESCRIBE] ===")
    p(df.describe(include="all").to_string())
    p("\n=== [UNIQUE VALUE COUNT] ===")
    p(df.nunique(dropna=False).sort_values(ascending=False).to_string())
    p("\n=== [MISSING VALUES] ===")
    missing = df.isnull().sum()
    missing = missing[missing > 0]
    p("  No missing values." if missing.empty else missing.to_string())
    p("\n=== [FINAL COLUMNS] ===")
    for i, col in enumerate(df.columns, 1):
        p(f"  {i:>2}. {col}")

    out_path = os.path.join(OUTPUT_DIR, "merged_understand.txt")
    with open(out_path, "w") as f:
        f.write(output.getvalue())
    print(f"[Saved: {out_path}]")


# =============================================================================
# STEP 7 — DATA VISUALIZATION: MERGED DATASET
# =============================================================================
# Produces 3 plots to understand the merged dataset:
#
#   Plot 1 — Bar Chart: Average API per State
#             Shows which states consistently have the highest API.
#             This is the most important chart since API is the target.
#
#   Plot 2 — Scatter Plot: Temperature vs API
#             Shows whether hotter temperatures are linked to higher API.
#             If yes, temperature is a strong feature for the model.
#
#   Plot 3 — Scatter Plot: Hotspot Count vs API
#             Shows whether more fires are linked to higher API readings.
#             This is the key relationship the FYP is trying to capture.

def visualize_merged(df: pd.DataFrame) -> None:
    """Generates 3 visualizations for the final merged DataFrame."""

    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    fig.suptitle("Merged Dataset (APIMS + METMalaysia + NASA FIRMS) — Visualization",
                 fontsize=13, fontweight="bold", y=1.01)

    # ── Plot 1: Average API per State ─────────────────────────────────────────
    ax1 = axes[0]
    if "API" in df.columns and "STATE_NAME" in df.columns:
        avg_api = df.groupby("STATE_NAME")["API"].mean().sort_values(ascending=True)
        bars = ax1.barh(avg_api.index, avg_api.values,
                        color="#E53935", edgecolor="white", linewidth=0.7)
        ax1.bar_label(bars, fmt="%.1f", padding=3, fontsize=7)
        ax1.axvline(avg_api.mean(), color="#212121", linestyle="--", linewidth=1.2,
                    label=f"Overall Mean: {avg_api.mean():.1f}")
        ax1.set_title("Average API per State", fontsize=12, fontweight="bold")
        ax1.set_xlabel("Average API")
        ax1.set_ylabel("State")
        ax1.legend(fontsize=8)

    # ── Plot 2: Temperature vs API ────────────────────────────────────────────
    ax2 = axes[1]
    if "TEMPERATURE_C" in df.columns and "API" in df.columns:
        plot_df = df[["TEMPERATURE_C", "API"]].dropna()
        ax2.scatter(plot_df["TEMPERATURE_C"], plot_df["API"],
                    alpha=0.4, color="#1E88E5", edgecolors="none", s=25)
        ax2.set_title("Temperature vs API", fontsize=12, fontweight="bold")
        ax2.set_xlabel("Temperature (°C)")
        ax2.set_ylabel("API")
        ax2.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

    # ── Plot 3: Fire Hotspot Count vs API ─────────────────────────────────────
    ax3 = axes[2]
    if "HOTSPOT_COUNT" in df.columns and "API" in df.columns:
        plot_df = df[["HOTSPOT_COUNT", "API"]].dropna()
        ax3.scatter(plot_df["HOTSPOT_COUNT"], plot_df["API"],
                    alpha=0.4, color="#FB8C00", edgecolors="none", s=25)
        ax3.set_title("Fire Hotspot Count vs API", fontsize=12, fontweight="bold")
        ax3.set_xlabel("Number of Hotspots (National, per Hour)")
        ax3.set_ylabel("API")
        ax3.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

    plt.tight_layout()
    out_path = os.path.join(OUTPUT_DIR, "merged_visualization.png")
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"\n[Visualization saved: {out_path}]")
    plt.show()


# =============================================================================
# STEP 8 — DATA VALIDATION
# =============================================================================
# Checks each snapshot for impossible or suspicious values before saving.
# Rows are NOT dropped — they are flagged so bad data is visible in the dataset.

# Path to the accumulated timeseries CSV. Forward-referenced — defined later in
# the file under STEP 9, but resolved at call time (Python module-level scope).
# Validation reads this file to get the previous N hours per station, which is
# how flatline and spike detection compare against history.

def _load_recent_history(history_path: str, n_per_station: int = 5) -> pd.DataFrame:
    """
    Return the last `n_per_station` rows per station from the timeseries CSV.

    Used by validate_snapshot for checks that need prior context (flatline,
    spike). Returns an empty DataFrame if the CSV does not yet exist (first
    pipeline run) — the caller treats this as "insufficient history, skip".
    """
    if not os.path.exists(history_path):
        return pd.DataFrame()

    history = pd.read_csv(history_path, parse_dates=["HOUR_MYT"])
    history = history.sort_values(["STATION_ID", "HOUR_MYT"])
    return history.groupby("STATION_ID", group_keys=False).tail(n_per_station)


def validate_snapshot(df: pd.DataFrame) -> pd.DataFrame:
    import logging
    logger = logging.getLogger("pipeline")

    df = df.copy()
    df["DATA_FLAG"] = ""

    # Impossible API values
    mask_api = df["API"].notna() & ((df["API"] < 0) | (df["API"] > 500))
    if mask_api.any():
        logger.warning(f"[VALIDATE] {mask_api.sum()} rows with impossible API value")
        df.loc[mask_api, "DATA_FLAG"] += "INVALID_API;"

    # Impossible temperature
    if "TEMPERATURE_C" in df.columns:
        mask_temp = df["TEMPERATURE_C"].notna() & (df["TEMPERATURE_C"] > 50)
        if mask_temp.any():
            logger.warning(f"[VALIDATE] {mask_temp.sum()} rows with TEMPERATURE_C > 50")
            df.loc[mask_temp, "DATA_FLAG"] += "INVALID_TEMP;"

    # Negative hotspot count (national or station-local)
    for hs_col, flag_tag in [
        ("HOTSPOT_COUNT",       "INVALID_HOTSPOT;"),
        ("HOTSPOT_COUNT_100KM", "INVALID_HOTSPOT_LOCAL;"),
    ]:
        if hs_col in df.columns:
            mask_hs = df[hs_col] < 0
            if mask_hs.any():
                logger.warning(f"[VALIDATE] {mask_hs.sum()} rows with negative {hs_col}")
                df.loc[mask_hs, "DATA_FLAG"] += flag_tag

    # Flatline detection — same API value for 6 consecutive hours (current + 5
    # prior). A stuck sensor is the most common silent failure: it keeps
    # returning the last good reading instead of timing out. We need to flag
    # the row, not drop it, so the model can learn to down-weight stuck rows.
    history = _load_recent_history(TIMESERIES_PATH, n_per_station=5)
    if not history.empty and "API" in df.columns:
        df["HOUR_MYT"] = pd.to_datetime(df["HOUR_MYT"])
        history["HOUR_MYT"] = pd.to_datetime(history["HOUR_MYT"])

        flatline_count = 0
        for station_id, current_rows in df.groupby("STATION_ID"):
            current_row = current_rows.iloc[0]
            current_api = current_row["API"]
            current_hour = current_row["HOUR_MYT"]

            station_history = history[history["STATION_ID"] == station_id]
            if len(station_history) < 5:
                continue  # not enough history yet

            # Require: 5 priors are at exactly hour-1, hour-2, ..., hour-5
            expected_hours = pd.date_range(
                end=current_hour - pd.Timedelta(hours=1),
                periods=5, freq="h"
            )
            actual_hours = station_history["HOUR_MYT"].sort_values().reset_index(drop=True)
            if not (actual_hours.values == expected_hours.values).all():
                continue  # gap in history — not 6 consecutive hours

            # Require: all 5 priors AND current row have identical API
            if pd.isna(current_api):
                continue
            if not (station_history["API"] == current_api).all():
                continue

            df.loc[df["STATION_ID"] == station_id, "DATA_FLAG"] += "FLATLINE;"
            flatline_count += 1

        if flatline_count:
            logger.warning(
                f"[VALIDATE] {flatline_count} station(s) flagged FLATLINE "
                f"(API unchanged for 6 consecutive hours)"
            )

        # Spike detection — API changes by > 50 between this hour and the
        # immediately previous hour for the same station. Both directions are
        # flagged: a sudden jump up suggests a sensor glitch or a real episode
        # spike (worth a second look either way), and a sudden drop > 50
        # suggests a sensor reset or maintenance event. Strict inequality:
        # exactly 50 is NOT flagged. Requires the prior row to be at exactly
        # t-1h; if there's a gap, we cannot infer an hourly jump.
        spike_count = 0
        for station_id, current_rows in df.groupby("STATION_ID"):
            current_row = current_rows.iloc[0]
            current_api = current_row["API"]
            current_hour = current_row["HOUR_MYT"]

            if pd.isna(current_api):
                continue

            prev_hour = current_hour - pd.Timedelta(hours=1)
            prev_rows = history[
                (history["STATION_ID"] == station_id) &
                (history["HOUR_MYT"] == prev_hour)
            ]
            if prev_rows.empty:
                continue  # no row at exactly t-1h

            prev_api = prev_rows["API"].iloc[0]
            if pd.isna(prev_api):
                continue

            if abs(current_api - prev_api) > 50:
                df.loc[df["STATION_ID"] == station_id, "DATA_FLAG"] += "SPIKE;"
                spike_count += 1

        if spike_count:
            logger.warning(
                f"[VALIDATE] {spike_count} station(s) flagged SPIKE "
                f"(API change > 50 from previous hour)"
            )

    flagged = (df["DATA_FLAG"] != "").sum()
    if flagged:
        logger.warning(f"[VALIDATE] Total flagged rows this snapshot: {flagged}")
    else:
        logger.info("[VALIDATE] All rows passed validation.")

    return df


# =============================================================================
# STEP 9 — APPEND SNAPSHOT TO TIMESERIES CSV
# =============================================================================
# Each hourly run appends its rows to merged_timeseries.csv.
# Duplicates (same STATION_ID + HOUR_MYT) are dropped so re-runs are safe.

TIMESERIES_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "data", "processed", "merged_timeseries.csv"
)


def save_snapshot(df: pd.DataFrame) -> None:
    import logging
    logger = logging.getLogger("pipeline")

    out_path = os.path.normpath(TIMESERIES_PATH)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    if os.path.exists(out_path):
        existing = pd.read_csv(out_path, parse_dates=["HOUR_MYT"])
        combined = pd.concat([existing, df], ignore_index=True)
    else:
        combined = df.copy()

    before = len(combined)
    combined.drop_duplicates(subset=["STATION_ID", "HOUR_MYT"], keep="last", inplace=True)
    combined.sort_values(["STATION_ID", "HOUR_MYT"], inplace=True)
    combined.reset_index(drop=True, inplace=True)
    after = len(combined)

    combined.to_csv(out_path, index=False)
    logger.info(
        f"[SAVE] Snapshot appended -> {out_path} "
        f"| new rows: {len(df)} | deduped: {before - after} | total: {after}"
    )
    print(f"[SAVE] merged_timeseries.csv now has {after} rows.")


def initialize_timeseries_from_history_preview(
    preview_path: str = HISTORY_PREVIEW_PATH,
    timeseries_path: str = TIMESERIES_PATH,
) -> pd.DataFrame:
    """
    Initialise/update merged_timeseries.csv from a reviewed history preview.

    Preview rows provide the current + previous 1-24h forecasting context
    immediately. Existing scheduler-collected rows are kept when the same
    STATION_ID + HOUR_MYT already exists, so live observations are not
    overwritten by backfilled rows.
    """
    preview_path = os.path.normpath(preview_path)
    timeseries_path = os.path.normpath(timeseries_path)

    if not os.path.exists(preview_path):
        raise FileNotFoundError(f"History preview not found: {preview_path}")

    preview = pd.read_csv(preview_path, parse_dates=["HOUR_MYT"])
    if preview.empty:
        raise ValueError(f"History preview is empty: {preview_path}")
    if not {"STATION_ID", "HOUR_MYT"}.issubset(preview.columns):
        raise ValueError("History preview must contain STATION_ID and HOUR_MYT columns.")

    os.makedirs(os.path.dirname(os.path.abspath(timeseries_path)), exist_ok=True)
    if os.path.exists(timeseries_path):
        existing = pd.read_csv(timeseries_path, parse_dates=["HOUR_MYT"])
    else:
        existing = pd.DataFrame(columns=preview.columns)

    before_existing = len(existing)
    before_preview = len(preview)

    # Preview first, existing second: existing live rows win on overlap.
    combined = pd.concat([preview, existing], ignore_index=True, sort=False)
    before_dedup = len(combined)
    combined.drop_duplicates(subset=["STATION_ID", "HOUR_MYT"], keep="last", inplace=True)
    combined.sort_values(["STATION_ID", "HOUR_MYT"], inplace=True)
    combined.reset_index(drop=True, inplace=True)
    combined.to_csv(timeseries_path, index=False)

    after = len(combined)
    print(f"[INIT] Preview input       : {preview_path}")
    print(f"[INIT] Timeseries output   : {timeseries_path}")
    print(f"[INIT] Existing rows       : {before_existing:,}")
    print(f"[INIT] Preview rows        : {before_preview:,}")
    print(f"[INIT] Deduped rows        : {before_dedup - after:,}")
    print(f"[INIT] Added rows          : {after - before_existing:,}")
    print(f"[INIT] Final rows          : {after:,}")
    print(f"[INIT] Stations            : {combined['STATION_ID'].nunique()}")
    print(f"[INIT] Hours               : {combined['HOUR_MYT'].nunique()}")
    print(f"[INIT] Range               : {combined['HOUR_MYT'].min()} -> {combined['HOUR_MYT'].max()}")
    if "DATA_FLAG" in combined.columns:
        print("[INIT] DATA_FLAG counts:")
        flag_counts = combined["DATA_FLAG"].fillna("").astype(str).value_counts()
        for flag, count in flag_counts.items():
            label = flag if flag else "(clean/live)"
            print(f"[INIT]   {label}: {count}")

    return combined


# =============================================================================
# ── QUICK TEST (run directly: python data_pipeline_merge.py) ─────────────────
# =============================================================================

if __name__ == "__main__":
    import argparse
    import asyncio
    import traceback

    parser = argparse.ArgumentParser(description="Merge APIMS, METMalaysia, and NASA FIRMS data.")
    parser.add_argument(
        "--history-preview",
        action="store_true",
        help="Build a multi-source historical preview CSV without changing merged_timeseries.csv.",
    )
    parser.add_argument(
        "--init-timeseries-from-preview",
        action="store_true",
        help=(
            "Initialise/update merged_timeseries.csv from a reviewed history "
            "preview, keeping existing live rows on overlap."
        ),
    )
    parser.add_argument(
        "--datetime",
        dest="end_datetime",
        default=None,
        help='Ending hour for APIMS history, for example "2026-05-07 15:00".',
    )
    parser.add_argument(
        "--state-ids",
        default="1-16",
        help='APIMS state ids to fetch, for example "1-16" or "1,2,14".',
    )
    parser.add_argument(
        "--output",
        default=HISTORY_PREVIEW_PATH,
        help="Output CSV path for --history-preview mode.",
    )
    parser.add_argument(
        "--preview-input",
        default=HISTORY_PREVIEW_PATH,
        help="Input CSV path for --init-timeseries-from-preview mode.",
    )
    parser.add_argument(
        "--timeseries-output",
        default=TIMESERIES_PATH,
        help="Output CSV path for --init-timeseries-from-preview mode.",
    )
    args = parser.parse_args()

    if args.history_preview:
        preview_df = asyncio.run(build_multisource_history_preview(
            end_datetime=args.end_datetime,
            state_ids=parse_state_ids(args.state_ids),
        ))
        save_history_preview(preview_df, args.output)
        sys.exit(0)

    if args.init_timeseries_from_preview:
        initialize_timeseries_from_history_preview(
            preview_path=args.preview_input,
            timeseries_path=args.timeseries_output,
        )
        sys.exit(0)

    async def run_test():
        print("\n" + "=" * 65)
        print("  Merge Pipeline — Fetch + Combine Test")
        print("=" * 65)
        try:
            # ── APIMS: uses requests (sync) ───────────────────────────────────
            print("[1/4] Fetching APIMS...")
            raw_apims  = requests.get(APIMS_URL, timeout=60)
            raw_apims.raise_for_status()
            df_apims   = preprocess_apims(raw_apims.json())

            # ── METMalaysia: uses httpx (async) ──────────────────────────────
            print("[2/4] Fetching METMalaysia...")
            raw_met  = await fetch_met_data()
            df_met   = preprocess_met(raw_met)

            # ── NASA FIRMS: uses httpx (async) ────────────────────────────────
            print("[3/4] Fetching NASA FIRMS...")
            raw_firms = await fetch_firms_data()
            df_firms  = preprocess_firms(raw_firms)
            
            # ── Merge all 3 ───────────────────────────────────────────────────
            print("[4/4] Merging all 3 datasets...\n")
            df_merged = merge_all(df_apims, df_met, df_firms)

            understand_merged(df_merged)
            visualize_merged(df_merged)

        except Exception as e:
            print(f"\n  ERROR: {e}")
            traceback.print_exc()

    # Works in both terminal and Jupyter / VS Code Interactive
    try:
        asyncio.run(run_test())
    except RuntimeError:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(run_test())

    async def save_snapshot(df):
        print(hi)
