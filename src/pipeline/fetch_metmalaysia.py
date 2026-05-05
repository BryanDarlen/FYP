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