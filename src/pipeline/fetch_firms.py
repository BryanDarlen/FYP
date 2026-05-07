# =============================================================================
# FYP: Predicting Air Pollution Levels in Malaysia Using Real Time Web Data
# Chapter 3.3 – Data Collection & 3.4 – Data Pre-processing (NASA FIRMS)
# Author : Bryan Quinn Darlen | TP073947
# =============================================================================

# ---------------------------------------------------------------------------
# SECTION 1 — IMPORT LIBRARIES
# ---------------------------------------------------------------------------
# Loads httpx (async HTTP), pandas (data manipulation), FastAPI (backend),
# io (in-memory file reading for CSV), and datetime utilities.

import os
import httpx
import pandas as pd
import io
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional

# Load environment variables from the project root .env file (if present).
# fetch_firms.py lives at <project_root>/src/pipeline/, so parents[2] is root.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env", override=True)

OUTPUT_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "outputs")
)
os.makedirs(OUTPUT_DIR, exist_ok=True)
import requests
from fastapi import FastAPI
from datetime import datetime, timezone, timedelta

# ---------------------------------------------------------------------------
# SECTION 2 — DEFINE API ENDPOINT
# ---------------------------------------------------------------------------
# Stores the full endpoint link that will be called to download
# NASA FIRMS VIIRS SNPP Near Real-Time fire hotspot data in CSV format.

# NASA FIRMS – VIIRS SNPP Near Real-Time hotspots over the regional study area.
#
# Bounding box: West=95, South=-6, East=119.5, North=7.6  | 1 day lookback
# Covers: Peninsular Malaysia, Sabah, Sarawak, all of Sumatra, all of Kalimantan.
# Rationale: Malaysia's worst haze episodes are driven by transboundary smoke
# from fires in Sumatra (esp. Riau ~0.3°N) and Kalimantan (4°S to 4°N),
# both of which fall well below the previous 0.8°N southern bound and so
# were silently excluded. ASMC monitors the same two sub-regions for ASEAN
# regional haze (https://asmc.asean.org/asmc-haze-hotspot-annual-new/).
#
# The MAP_KEY is read from the FIRMS_MAP_KEY environment variable (loaded
# from .env at project root). Get a free key at:
#   https://firms.modaps.eosdis.nasa.gov/api/map_key/
FIRMS_MAP_KEY = os.environ.get("FIRMS_MAP_KEY")
if not FIRMS_MAP_KEY:
    raise RuntimeError(
        "FIRMS_MAP_KEY is not set. Copy .env.example to .env and fill in "
        "your FIRMS MAP_KEY (free at https://firms.modaps.eosdis.nasa.gov/api/map_key/)."
    )

FIRMS_SOURCE = "VIIRS_SNPP_NRT"
FIRMS_AREA = "95,-6,119.5,7.6"


def build_firms_url(day_range: int = 1, start_date: Optional[str] = None) -> str:
    """
    Build a NASA FIRMS Area API URL.

    `start_date` is optional and enables historical pulls for preview/backfill.
    The default preserves the current scheduler behaviour: latest 1-day NRT
    data over the regional study area.
    """
    url = (
        f"https://firms.modaps.eosdis.nasa.gov/api/area/csv"
        f"/{FIRMS_MAP_KEY}"
        f"/{FIRMS_SOURCE}/{FIRMS_AREA}/{day_range}"
    )
    if start_date:
        url = f"{url}/{start_date}"
    return url


FIRMS_URL = build_firms_url()

# Malaysia Time offset (UTC+8) — used to align all timestamps to MYT
MYT_OFFSET = timedelta(hours=8)

# ---------------------------------------------------------------------------
# SECTION 3 — FASTAPI APP SETUP
# ---------------------------------------------------------------------------
# Creates the FastAPI application and prepares two variables to hold the
# latest cleaned table and the last update time.

app = FastAPI()

latest_firms_df  = None  
last_update_firms = None 


# ---------------------------------------------------------------------------
# SECTION 4 — FETCH NASA FIRMS DATA
# ---------------------------------------------------------------------------
# Sends an online request to the NASA FIRMS CSV endpoint and returns
# the raw response text (CSV format).

async def fetch_firms_data(day_range: int = 1, start_date: Optional[str] = None) -> str:
    """
    Fetches VIIRS SNPP Near Real-Time fire hotspot data from NASA FIRMS.
    Returns the raw CSV response as a string.
    Raises httpx.HTTPStatusError if the request fails.
    """
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(build_firms_url(day_range=day_range, start_date=start_date))
        response.raise_for_status()
        return response.text


# ---------------------------------------------------------------------------
# SECTION 5 — PREPROCESS NASA FIRMS DATA
# ---------------------------------------------------------------------------
# Parses the CSV text into a DataFrame, keeps important columns,
# converts acquisition date + time to MYT datetime, converts numeric
# fields to correct types, filters to the regional study area
# (Malaysia + Sumatra + Kalimantan, matching the FIRMS URL bbox),
# and removes duplicates.

# ---------------------------------------------------------------------------
# SECTION 5 — PREPROCESS NASA FIRMS DATA
# ---------------------------------------------------------------------------
# Parses the CSV text into a DataFrame, keeps important columns for hotspot
# analysis, converts date/time to UTC and MYT, converts numeric values,
# filters to Malaysia coordinates, removes duplicates, and renames columns.

def preprocess_firms(raw_csv: str) -> pd.DataFrame:
    # 1: Parse raw CSV text into a pandas DataFrame 
    df = pd.read_csv(io.StringIO(raw_csv))
    if df.empty:
        print("NASA FIRMS: No hotspot records found for the specified bounding box / period.")
        return df

    # 2: Standardise all column names to uppercase 
    # This makes the dataset easier to handle consistently in later steps.
    df.columns = [c.strip().upper() for c in df.columns]

    # 3: Keep only the important columns for the FYP 
    # Selected columns to keep wanted columns
    keep_cols = [
        "LATITUDE",
        "LONGITUDE",
        "BRIGHT_TI4",
        "BRIGHT_TI5",
        "FRP",
        "CONFIDENCE",
        "SCAN",
        "TRACK",
        "ACQ_DATE",
        "ACQ_TIME",
        "SATELLITE",
        "DAYNIGHT",
    ]
    df = df[[c for c in keep_cols if c in df.columns]].copy()

    # 4: Combine acquisition date and time into full datetime 
    def parse_firms_datetime(row):
        try:
            time_str = str(int(row["ACQ_TIME"])).zfill(4)
            dt_str = f"{row['ACQ_DATE']} {time_str[:2]}:{time_str[2:]}"
            dt_utc = datetime.strptime(dt_str, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
            dt_myt = (dt_utc + MYT_OFFSET).replace(tzinfo=None)
            return dt_utc, dt_myt
        except Exception:
            return None, None

    dt_pairs = df.apply(parse_firms_datetime, axis=1)
    df["ACQ_DATETIME_UTC"] = [p[0] for p in dt_pairs]
    df["ACQ_DATETIME_MYT"] = [p[1] for p in dt_pairs]

    # 5: Remove the original date and time columns 
    # no longer needed after creating the full datetime fields.
    df.drop(columns=["ACQ_DATE", "ACQ_TIME"], inplace=True, errors="ignore")

    # 6: Convert selected columns into numeric format 
    # This ensures correct data types for analysis and machine learning.
    numeric_cols = [
        "LATITUDE", "LONGITUDE",
        "BRIGHT_TI4", "BRIGHT_TI5",
        "FRP", "SCAN", "TRACK"
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # 7: Filter hotspot records to the regional study area
    # The study area covers Malaysia plus the two main transboundary haze
    # source regions (Sumatra and Kalimantan), since Malaysia's worst haze
    # episodes are driven by smoke from those Indonesian provinces rather
    # than by domestic fires alone. Bounds match the FIRMS API URL above.
    #   Sumatra:    ~6°N to ~6°S, ~95°E to ~106°E
    #   Kalimantan: ~4°N to ~4°S, ~108°E to ~119°E
    #   Malaysia:   ~1°N to ~7°N, ~99°E to ~119°E
    df = df[
        (df["LATITUDE"]  >= -6.0) & (df["LATITUDE"]  <= 7.6) &
        (df["LONGITUDE"] >= 95.0) & (df["LONGITUDE"] <= 119.5)
    ].copy()


    # 8: Rename columns
    # improves readability when the dataset is used later in the pipeline.
    df.rename(columns={
        "BRIGHT_TI4": "BRIGHTNESS_TI4_K",
        "BRIGHT_TI5": "BRIGHTNESS_TI5_K",
        "FRP": "FRP_MW",
        "SCAN": "SCAN_KM",
        "TRACK": "TRACK_KM",
    }, inplace=True, errors="ignore")

    # 9: Remove duplicates safely if there's any
    df.drop_duplicates(inplace=True)

    # 10: Reset the DataFrame index
    # This gives the cleaned dataset a fresh sequential index.
    df.reset_index(drop=True, inplace=True)

    return df

# ---------------------------------------------------------------------------
# SECTION 6 — DATA UNDERSTANDING: NASA FIRMS
# ---------------------------------------------------------------------------
# Displays the observation of data after the preprocess step (shape,
# dtypes, missing values, summary statistics, unique value counts,
# day/night split, and confidence level distribution).

def inspect_dataset(df: pd.DataFrame, name: str) -> None:
    """Prints INFO and HEAD for any cleaned DataFrame."""
    print(f"\n\n=== {name} ===")
    print("\n[INFO]")
    df.info()
    print("\n[HEAD]")
    print(df.head())

def understand_firms(df: pd.DataFrame) -> None:
    """Prints data understanding summary for the cleaned NASA FIRMS DataFrame."""

    print("=== NASA FIRMS Cleaned Data ===")
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

# ---------------------------------------------------------------------------
# SECTION 7 — DATA VISUALIZATION: NASA FIRMS
# ---------------------------------------------------------------------------
# Produces 4 plots to visually understand the cleaned NASA FIRMS dataset:
#
#   Plot 1 — Histogram of FRP_MW (Fire Radiative Power)
#             Shows the distribution of fire intensity across all detected
#             hotspots. Most fires cluster at low FRP, but high-FRP outliers
#             represent intense fires that generate heavy smoke — the main
#             driver of transboundary haze events and API spikes in Malaysia.
#
#   Plot 2 — Bar Chart: Hotspot Count by Confidence Level (l / n / h)
#             FIRMS assigns each detection a confidence level: low (l),
#             nominal (n), or high (h). This chart shows how many hotspots
#             fall into each category, helping assess how reliable the
#             current batch of fire detections is before merging with APIMS.
#
#   Plot 3 — Scatter Plot: Hotspot Geographic Distribution
#             Plots each hotspot by LONGITUDE vs LATITUDE, with point colour
#             and size scaled by FRP_MW. This is the most direct way to see
#             where active fires are burning relative to Malaysia's air
#             quality monitoring stations — a key spatial insight for the FYP.
#
#   Plot 4 — Bar Chart: Hotspot Count by Day/Night Detection
#             VIIRS thermal sensors behave differently between day and night
#             passes. Daytime detections can be affected by solar reflection,
#             while night detections tend to be more thermally reliable for
#             low-intensity fires. This split shows how many hotspots were
#             captured in each pass, helping judge detection quality.

def visualize_firms(df: pd.DataFrame) -> None:
    """Generates 4 visualizations for the cleaned NASA FIRMS DataFrame."""

    import matplotlib.pyplot as plt
    import matplotlib.ticker as ticker

    if df.empty:
        print("[Visualization skipped: no hotspot records available]")
        return

    # ── Plot 1: Histogram of FRP_MW ───────────────────────────────────────────
    plt.figure(figsize=(8, 6))
    ax1 = plt.gca()
    frp_data = df["FRP_MW"].dropna()
    ax1.hist(frp_data, bins=20, color="#F44336", edgecolor="white", linewidth=0.7)
    ax1.axvline(frp_data.mean(), color="#212121", linestyle="--", linewidth=1.5,
                label=f"Mean: {frp_data.mean():.1f} MW")
    ax1.set_title("Distribution of Fire Radiative Power (FRP)", fontsize=12, fontweight="bold")
    ax1.set_xlabel("FRP (MW)")
    ax1.set_ylabel("Number of Hotspots")
    ax1.legend(fontsize=9)
    ax1.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    plt.tight_layout()
    plt.show()

    # ── Plot 2: Bar Chart — Hotspot Count by Confidence Level ─────────────────
    plt.figure(figsize=(8, 6))
    ax2 = plt.gca()
    conf_order = ["l", "n", "h"]
    conf_labels = {"l": "Low", "n": "Nominal", "h": "High"}
    conf_colors = {"l": "#FF9800", "n": "#2196F3", "h": "#4CAF50"}

    conf_counts = df["CONFIDENCE"].value_counts()
    ordered_keys = [k for k in conf_order if k in conf_counts.index]
    values  = [conf_counts[k] for k in ordered_keys]
    labels  = [conf_labels[k] for k in ordered_keys]
    colors  = [conf_colors[k] for k in ordered_keys]

    bars2 = ax2.bar(labels, values, color=colors, edgecolor="white", linewidth=0.7)
    ax2.bar_label(bars2, padding=3, fontsize=10)
    ax2.set_title("Hotspot Count by Confidence Level", fontsize=12, fontweight="bold")
    ax2.set_xlabel("Confidence Level")
    ax2.set_ylabel("Number of Hotspots")
    ax2.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    plt.tight_layout()  
    plt.show()

    # ── Plot 3: Scatter — Geographic Distribution of Hotspots ─────────────────
    plt.figure(figsize=(8, 6))
    ax3 = plt.gca()
    frp_vals = df["FRP_MW"].fillna(df["FRP_MW"].median())
    # Normalise point size: min 20, max 200 based on FRP
    sizes = 20 + 180 * (frp_vals - frp_vals.min()) / (frp_vals.max() - frp_vals.min() + 1e-9)

    sc = ax3.scatter(
        df["LONGITUDE"], df["LATITUDE"],
        c=frp_vals, cmap="YlOrRd",
        s=sizes, alpha=0.75, edgecolors="grey", linewidths=0.3
    )
    plt.colorbar(sc, ax=ax3, label="FRP (MW)")
    ax3.set_title("Hotspot Geographic Distribution\n(colour & size = FRP intensity)",
                  fontsize=12, fontweight="bold")
    ax3.set_xlabel("Longitude")
    ax3.set_ylabel("Latitude")
    plt.tight_layout()
    plt.show()

    # ── Plot 4: Bar Chart — Hotspot Count by Day/Night ────────────────────────
    plt.figure(figsize=(8, 6))
    ax4 = plt.gca()
    dn_counts = df["DAYNIGHT"].value_counts()
    dn_labels = {"D": "Day", "N": "Night"}
    dn_colors = {"D": "#FFC107", "N": "#3F51B5"}

    labels4 = [dn_labels.get(k, k) for k in dn_counts.index]
    colors4 = [dn_colors.get(k, "#9E9E9E") for k in dn_counts.index]

    bars4 = ax4.bar(labels4, dn_counts.values,
                    color=colors4, edgecolor="white", linewidth=0.7, width=0.5)
    ax4.bar_label(bars4, padding=3, fontsize=11)
    ax4.set_title("Hotspot Count by\nDay / Night Detection", fontsize=12, fontweight="bold")
    ax4.set_xlabel("Detection Pass")
    ax4.set_ylabel("Number of Hotspots")
    ax4.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    plt.tight_layout()
    plt.show()

    out_path = os.path.join(OUTPUT_DIR, "nasafirms_visualization.png")
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"\n[Visualization saved: {out_path}]")

# =============================================================================
# ── FASTAPI ENDPOINT ────
# =============================================================================


@app.get("/firms/latest")
async def get_latest_firms():
    """Returns the latest cleaned NASA FIRMS hotspot data as JSON records."""
    global latest_firms_df, last_update_firms
    if latest_firms_df is None:
        raw = await fetch_firms_data()
        latest_firms_df   = preprocess_firms(raw)
        last_update_firms = (datetime.now(timezone.utc) + MYT_OFFSET).strftime("%Y-%m-%d %H:%M MYT")
    return {
        "last_updated": last_update_firms,
        "rows": len(latest_firms_df),
        "data": latest_firms_df.to_dict(orient="records"),
    }


# =============================================================================
# ── QUICK TEST (run directly: python data_pipeline_nasafirms.py) ─────────────
# =============================================================================

if __name__ == "__main__":
    import asyncio

    async def run_test():
        print("\n" + "=" * 65)
        print("  NASA FIRMS — Fetch + Preprocess Test")
        print("=" * 65)
        try:
            raw_firms = await fetch_firms_data()
            df_firms  = preprocess_firms(raw_firms)
            inspect_dataset(df_firms, "METMalaysia Cleaned Data")
            understand_firms(df_firms)
            visualize_firms(df_firms)
        except Exception as e:
            print(f"  NASA FIRMS fetch/preprocess failed: {e}")

    asyncio.run(run_test())
