# =============================================================================
# FYP: Predicting Air Pollution Levels in Malaysia Using Real Time Web Data
# Chapter 3.3 – Data Collection & 3.4 – Data Pre-processing (METMalaysia)
# Author : Bryan Quinn Darlen | TP073947
# =============================================================================

# ---------------------------------------------------------------------------
# SECTION 1 — IMPORT LIBRARIES
# ---------------------------------------------------------------------------
# Loads httpx (async HTTP), pandas (data manipulation), FastAPI (backend),
# and datetime utilities.

import os
import httpx
import pandas as pd
from fastapi import FastAPI
from typing import Optional

OUTPUT_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "outputs")
)
os.makedirs(OUTPUT_DIR, exist_ok=True)
from datetime import datetime, timezone, timedelta

# ---------------------------------------------------------------------------
# SECTION 2 — DEFINE API ENDPOINT
# ---------------------------------------------------------------------------
# Stores the full endpoint link that will be called to download
# METMalaysia current weather readings in JSON format.

# METMalaysia – current weather readings (JSON, updated to latest, UTC timestamps)
MET_URL = "https://www.met.gov.my/json/cuaca_semasa/data.json"

WIS2_SYNOPTIC_URL = (
    "https://wis2node.met.gov.my/oapi/collections/"
    "urn%3Awmo%3Amd%3Amy-metmalaysia%3Asynop-hourly/items"
)
WIS2_HISTORY_VARIABLES = (
    "air_temperature",
    "present_weather",
    "past_weather1",
    "past_weather2",
)
WIS2_PAGE_LIMIT = 10000
WIS2_VERIFY_SSL = False

# Malaysia Time offset (UTC+8) — used to align all timestamps to MYT
MYT_OFFSET = timedelta(hours=8)

# ---------------------------------------------------------------------------
# SECTION 3 — FASTAPI APP SETUP
# ---------------------------------------------------------------------------
# Creates the FastAPI application and prepares two variables to hold the
# latest cleaned table and the last update time.

app = FastAPI()

latest_met_df  = None  # Holds latest cleaned METMalaysia DataFrame
last_update_met = None  # Timestamp of last successful METMalaysia fetch


# ---------------------------------------------------------------------------
# SECTION 4 — FETCH METMalaysia DATA
# ---------------------------------------------------------------------------
# Sends an online request to the METMalaysia endpoint and returns
# the response as JSON.

async def fetch_met_data() -> dict:
    """
    Fetches current weather readings from METMalaysia JSON API.
    Returns the raw JSON dictionary.
    Raises httpx.HTTPStatusError if the request fails.
    """
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(MET_URL)
        response.raise_for_status()
        return response.json()


# ---------------------------------------------------------------------------
# SECTION 5 — PREPROCESS METMalaysia DATA
# ---------------------------------------------------------------------------
# Extracts station weather attributes from the nested JSON, keeps important
# columns, converts UTC timestamps to Malaysia Time (MYT, UTC+8),
# converts numeric fields to correct types, and removes duplicates.

def preprocess_met(raw_json) -> pd.DataFrame:
    import json

    # 1. Make sure API response is a list
    if not isinstance(raw_json, list):
        raise ValueError(f"Expected list response, but got: {type(raw_json)}")

    if not raw_json:
        raise ValueError("METMalaysia JSON response contains no records.")

    # 2. Turn JSON into DataFrame
    df = pd.DataFrame(raw_json)

    # 3. Rename columns
    df.rename(columns={
        "code": "STATION_CODE",
        "station": "STATION_NAME",
        "timestamp": "TIMESTAMP_RAW",
        "temp": "TEMPERATURE_RAW",
        "state": "STATE",
        "rainfall": "RAINFALL_FORECAST",
        "icon": "WEATHER_ICON"
    }, inplace=True)

    # 4. Convert timestamp
    def parse_timestamp(ts):
        try:
            dt_utc = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S UTC").replace(tzinfo=timezone.utc)
            dt_myt = (dt_utc + MYT_OFFSET).replace(tzinfo=None)
            return dt_utc, dt_myt
        except Exception:
            return None, None

    dt_pairs = df["TIMESTAMP_RAW"].apply(parse_timestamp)
    df["DATETIME_UTC"] = [x[0] for x in dt_pairs]
    df["DATETIME_MYT"] = [x[1] for x in dt_pairs]

    # 5. Convert temperature like "32°" to 32
    df["TEMPERATURE_C"] = (
        df["TEMPERATURE_RAW"]
        .astype(str)
        .str.replace("°", "", regex=False)
        .str.strip()
    )
    df["TEMPERATURE_C"] = pd.to_numeric(df["TEMPERATURE_C"], errors="coerce")

    # 6. Count rainy forecast slots
    def count_rain_slots(rain_dict):
        if isinstance(rain_dict, dict):
            return sum("hujan" in str(v).lower() for v in rain_dict.values())
        return 0

    df["RAIN_FORECAST_SLOTS"] = df["RAINFALL_FORECAST"].apply(count_rain_slots)

    # 7. Convert rainfall dict into string so pandas won't error 
    df["RAINFALL_FORECAST"] = df["RAINFALL_FORECAST"].apply(
        lambda x: json.dumps(x, sort_keys=True) if isinstance(x, dict) else str(x)
    )

    # 8. Remove duplicates safely if there's any
    df.drop_duplicates(inplace=True)

    # 9. Reset index
    df.reset_index(drop=True, inplace=True)

    return df


# ---------------------------------------------------------------------------
# SECTION 5b - PREPROCESS WIS2 SYNOP HISTORY
# ---------------------------------------------------------------------------
# The public METMalaysia data.json endpoint is current-only. The WIS2
# synop-hourly endpoint is a different station-observation product that can
# provide historical readings, so this helper prepares a clearly flagged
# backfill/preview table without changing the scheduler's live behaviour.

def _myt_to_utc_iso(value) -> str:
    """Convert a MYT timestamp into an ISO UTC string accepted by WIS2."""
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        dt = ts.to_pydatetime().replace(tzinfo=timezone(MYT_OFFSET))
    else:
        dt = ts.to_pydatetime()
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


async def fetch_wis2_history(
    start_datetime_myt,
    end_datetime_myt,
    variable_names: Optional[tuple[str, ...]] = None,
) -> list[dict]:
    """
    Fetch historical WIS2 SYNOP observation features.

    The date inputs are Malaysia Time (MYT). WIS2 expects UTC intervals, so the
    function converts them before requesting the OGC API. SSL verification is
    disabled for this endpoint because the local Python certificate store can
    fail to validate wis2node.met.gov.my even when the endpoint is reachable.
    """
    names = variable_names or WIS2_HISTORY_VARIABLES
    datetime_range = f"{_myt_to_utc_iso(start_datetime_myt)}/{_myt_to_utc_iso(end_datetime_myt)}"
    features: list[dict] = []

    async with httpx.AsyncClient(
        timeout=30,
        verify=WIS2_VERIFY_SSL,
        follow_redirects=True,
    ) as client:
        for name in names:
            url = WIS2_SYNOPTIC_URL
            params = {
                "f": "json",
                "limit": WIS2_PAGE_LIMIT,
                "datetime": datetime_range,
                "name": name,
            }

            while url:
                response = await client.get(url, params=params)
                response.raise_for_status()
                payload = response.json()
                features.extend(payload.get("features", []))

                next_url = None
                for link in payload.get("links", []):
                    if link.get("rel") == "next" and link.get("href"):
                        next_url = link["href"]
                        break

                url = next_url
                params = None

    return features


def _description_has_rain(description) -> bool:
    text = str(description or "").lower()
    rain_terms = ("rain", "drizzle", "shower", "thunderstorm")
    return any(term in text for term in rain_terms)


def preprocess_wis2(raw_features: list[dict]) -> pd.DataFrame:
    """
    Convert WIS2 observation features into station-hour weather rows.

    Output columns intentionally mirror the fields needed by the merge:
    WIGOS_STATION_ID, coordinates, HOUR_MYT, TEMPERATURE_C, and
    RAIN_FORECAST_SLOTS. For WIS2 this rain column is an observed/derived count
    from present/past weather descriptions, not the forecast-slot dictionary
    used by the current data.json endpoint.
    """
    out_cols = [
        "WIGOS_STATION_ID", "DATETIME_UTC", "DATETIME_MYT", "HOUR_MYT",
        "LATITUDE", "LONGITUDE", "TEMPERATURE_C", "RAIN_FORECAST_SLOTS",
        "MET_SOURCE",
    ]
    rows = []

    for feature in raw_features or []:
        props = feature.get("properties", {}) or {}
        geometry = feature.get("geometry", {}) or {}
        coords = geometry.get("coordinates") or []
        lon = coords[0] if len(coords) >= 1 else None
        lat = coords[1] if len(coords) >= 2 else None

        rows.append({
            "WIGOS_STATION_ID": props.get("wigos_station_identifier"),
            "DATETIME_UTC": props.get("reportTime"),
            "VARIABLE": props.get("name"),
            "VALUE": props.get("value"),
            "DESCRIPTION": props.get("description"),
            "LATITUDE": lat,
            "LONGITUDE": lon,
        })

    long_df = pd.DataFrame(rows)
    if long_df.empty:
        return pd.DataFrame(columns=out_cols)

    long_df["DATETIME_UTC"] = pd.to_datetime(long_df["DATETIME_UTC"], utc=True, errors="coerce")
    long_df["DATETIME_MYT"] = (long_df["DATETIME_UTC"] + pd.Timedelta(hours=8)).dt.tz_localize(None)
    long_df["HOUR_MYT"] = long_df["DATETIME_MYT"].dt.floor("h")
    long_df["VALUE"] = pd.to_numeric(long_df["VALUE"], errors="coerce")
    long_df["LATITUDE"] = pd.to_numeric(long_df["LATITUDE"], errors="coerce")
    long_df["LONGITUDE"] = pd.to_numeric(long_df["LONGITUDE"], errors="coerce")

    key_cols = ["WIGOS_STATION_ID", "HOUR_MYT"]
    coords = (
        long_df.dropna(subset=["WIGOS_STATION_ID", "HOUR_MYT", "LATITUDE", "LONGITUDE"])
        .sort_values(key_cols)
        .drop_duplicates(subset=key_cols)
        [key_cols + ["DATETIME_UTC", "DATETIME_MYT", "LATITUDE", "LONGITUDE"]]
    )

    temp = (
        long_df[long_df["VARIABLE"] == "air_temperature"]
        .dropna(subset=["WIGOS_STATION_ID", "HOUR_MYT"])
        .sort_values(key_cols)
        .drop_duplicates(subset=key_cols, keep="last")
        [key_cols + ["VALUE"]]
        .rename(columns={"VALUE": "TEMPERATURE_C"})
    )

    weather_vars = ["present_weather", "past_weather1", "past_weather2"]
    weather = long_df[long_df["VARIABLE"].isin(weather_vars)].copy()
    if weather.empty:
        rain = temp[key_cols].copy()
        rain["RAIN_FORECAST_SLOTS"] = 0
    else:
        weather["RAIN_OBSERVED"] = weather["DESCRIPTION"].apply(_description_has_rain).astype(int)
        rain = (
            weather.groupby(key_cols, as_index=False)["RAIN_OBSERVED"]
            .sum()
            .rename(columns={"RAIN_OBSERVED": "RAIN_FORECAST_SLOTS"})
        )

    met = coords.merge(temp, on=key_cols, how="left")
    met = met.merge(rain, on=key_cols, how="left")
    met["RAIN_FORECAST_SLOTS"] = met["RAIN_FORECAST_SLOTS"].fillna(0).astype(int)
    met["MET_SOURCE"] = "WIS2_SYNOP_HOURLY"
    met = met.dropna(subset=["TEMPERATURE_C"])
    return met[out_cols].sort_values(["WIGOS_STATION_ID", "HOUR_MYT"]).reset_index(drop=True)

# ---------------------------------------------------------------------------
# SECTION 6 — DATA UNDERSTANDING: METMalaysia
# ---------------------------------------------------------------------------
# Displays the observation of data after the preprocess step (shape,
# dtypes, missing values, summary statistics, unique value counts).

def inspect_dataset(df: pd.DataFrame, name: str) -> None:
    """Prints INFO and HEAD for any cleaned DataFrame."""
    print(f"\n\n=== {name} ===")
    print("\n[INFO]")
    df.info()
    print("\n[HEAD]")
    print(df.head())

def understand_met(df: pd.DataFrame) -> None:
    """Prints data understanding summary for the cleaned METMalaysia DataFrame."""

    print("=== METMalaysia Cleaned Data ===")
    print("Rows:", df.shape[0], "Cols:", df.shape[1])
    print(df.head(5))

    # A) df.describe
    print("\n=== [DESCRIBE] ===")
    describe_out = df.describe(include="all")
    print(describe_out)

    # B) df.nunique
    print("\n=== [UNIQUE VALUE COUNT] ===")
    nunique_out = df.nunique(dropna=False).sort_values(ascending=False)
    print(nunique_out)


# =============================================================================
# ── FASTAPI ENDPOINT ──────────────────────────────────────────────────────────
# =============================================================================

@app.get("/weather/latest")
async def get_latest_weather():
    """Returns the latest cleaned METMalaysia weather data as JSON records."""
    global latest_met_df, last_update_met
    if latest_met_df is None:
        raw = await fetch_met_data()
        latest_met_df   = preprocess_met(raw)
        last_update_met = (datetime.now(timezone.utc) + MYT_OFFSET).strftime("%Y-%m-%d %H:%M MYT")
    return {
        "last_updated": last_update_met,
        "rows": len(latest_met_df),
        "data": latest_met_df.to_dict(orient="records"),
    }


# ---------------------------------------------------------------------------
# SECTION 7 — DATA VISUALIZATION: METMalaysia
# ---------------------------------------------------------------------------
# Produces 3 plots to visually understand the cleaned METMalaysia dataset:
#
#   Plot 1 — Histogram of TEMPERATURE_C
#             Shows the spread and distribution of current temperatures
#             across all weather stations. Reveals if most stations are
#             reporting a similar temperature band or if there are outliers
#             (e.g. unusually cold highland vs hot urban stations).
#
#   Plot 2 — Bar Chart: Number of Stations per State
#             Shows how many METMalaysia stations exist per state.
#             Identifies which states have dense vs sparse weather coverage,
#             which directly affects how reliably METMalaysia data can be
#             merged with APIMS air quality stations in the pipeline.
#
#   Plot 3 — Bar Chart: Average Rain Forecast Slots per State
#             Shows which states have the most forecasted rain periods.
#             Since rainfall washes out PM2.5 particles and lowers API,
#             this is one of the most important weather signals in the FYP.

def visualize_met(df: pd.DataFrame) -> None:
    """Generates 3 visualizations for the cleaned METMalaysia DataFrame."""

    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker

    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    fig.suptitle("METMalaysia — Data Visualization", fontsize=15, fontweight="bold", y=1.01)

    # ── Plot 1: Histogram of TEMPERATURE_C ───────────────────────────────────
    ax1 = axes[0]
    temp_data = df["TEMPERATURE_C"].dropna()
    ax1.hist(temp_data, bins=15, color="#2196F3", edgecolor="white", linewidth=0.7)
    ax1.axvline(temp_data.mean(), color="#F44336", linestyle="--", linewidth=1.5,
                label=f"Mean: {temp_data.mean():.1f}°C")
    ax1.set_title("Distribution of Temperature (°C)", fontsize=12, fontweight="bold")
    ax1.set_xlabel("Temperature (°C)")
    ax1.set_ylabel("Number of Stations")
    ax1.legend(fontsize=9)
    ax1.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))

    # ── Plot 2: Bar Chart — Station Count per State ───────────────────────────
    ax2 = axes[1]
    station_counts = (
        df.groupby("STATE")["STATION_CODE"]
        .count()
        .sort_values(ascending=True)
    )
    bars2 = ax2.barh(station_counts.index, station_counts.values,
                     color="#4CAF50", edgecolor="white", linewidth=0.7)
    ax2.bar_label(bars2, padding=3, fontsize=8)
    ax2.set_title("Number of Stations per State", fontsize=12, fontweight="bold")
    ax2.set_xlabel("Number of Stations")
    ax2.set_ylabel("State")
    ax2.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))

    # ── Plot 3: Bar Chart — Average Rain Forecast Slots per State ────────────
    ax3 = axes[2]
    rain_by_state = (
        df.groupby("STATE")["RAIN_FORECAST_SLOTS"]
        .mean()
        .sort_values(ascending=True)
    )
    bars3 = ax3.barh(rain_by_state.index, rain_by_state.values,
                     color="#FF9800", edgecolor="white", linewidth=0.7)
    ax3.bar_label(bars3, fmt="%.1f", padding=3, fontsize=8)
    ax3.set_title("Avg Rain Forecast Slots per State", fontsize=12, fontweight="bold")
    ax3.set_xlabel("Avg Rain Slots (out of total forecast periods)")
    ax3.set_ylabel("State")

    plt.tight_layout()
    out_path = os.path.join(OUTPUT_DIR, "metmalaysia_visualization.png")
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"\n[Visualization saved: {out_path}]")
    plt.show()


# =============================================================================
# ── FASTAPI ENDPOINT ──────────────────────────────────────────────────────────
# =============================================================================

@app.get("/weather/latest")
async def get_latest_weather():
    """Returns the latest cleaned METMalaysia weather data as JSON records."""
    global latest_met_df, last_update_met
    if latest_met_df is None:
        raw = await fetch_met_data()
        latest_met_df   = preprocess_met(raw)
        last_update_met = (datetime.now(timezone.utc) + MYT_OFFSET).strftime("%Y-%m-%d %H:%M MYT")
    return {
        "last_updated": last_update_met,
        "rows": len(latest_met_df),
        "data": latest_met_df.to_dict(orient="records"),
    }


# =============================================================================
# ── QUICK TEST (run directly: python data_pipeline_metmalaysia.py) ────────────
# =============================================================================

if __name__ == "__main__":
    import asyncio

    async def run_test():
        print("\n" + "=" * 65)
        print("  METMalaysia — Fetch + Preprocess Test")
        print("=" * 65)
        try:
            raw_met = await fetch_met_data()
            df_met  = preprocess_met(raw_met)
            inspect_dataset(df_met, "METMalaysia Cleaned Data")
            understand_met(df_met)
            visualize_met(df_met)
        except Exception as e:
            print(f"  METMalaysia fetch/preprocess failed: {e}")

    asyncio.run(run_test())
