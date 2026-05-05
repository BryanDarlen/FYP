# FYP
=======
# Predicting Air Pollution Levels in Malaysia Using Real-Time Web Data

**Student:** Bryan Quinn Darlen | APU3F2511 | TP073947  
**Supervisor:** Dr. Preethi Subramanian

---

## Project Overview

This system fetches real-time air quality, weather, and fire hotspot data from three sources — **APIMS**, **METMalaysia**, and **NASA FIRMS** — merges them into a single dataset, and collects hourly snapshots to build a historical time series for forecasting Malaysia's Air Pollution Index (API).

---

## Prerequisites

**Python version:** 3.9 or higher

Install all required libraries before running anything:

```bash
pip install pandas requests httpx fastapi matplotlib
```

---

## Project Structure

```
Bryan Darlen/
├── src/
│   └── pipeline/
│       ├── fetch_apims.py          # Fetches & cleans APIMS air quality data
│       ├── fetch_metmalaysia.py    # Fetches & cleans METMalaysia weather data
│       ├── fetch_firms.py          # Fetches & cleans NASA FIRMS fire hotspot data
│       ├── pipeline_merge.py       # Merges all 3 datasets into one snapshot
│       └── scheduler.py            # Runs the pipeline every hour (PHASE 2)
├── data/
│   ├── outputs/                    # EDA charts and analysis files (auto-created)
│   │   ├── apims_data_understanding.xlsx
│   │   ├── metmalaysia_visualization.png
│   │   ├── nasafirms_visualization.png
│   │   ├── merged_understand.txt
│   │   └── merged_visualization.png
│   ├── processed/
│   │   └── merged_timeseries.csv   # Grows by ~68 rows every hour (auto-created)
│   └── logs/
│       └── scheduler.log           # Full run history with timestamps (auto-created)
├── docs/
│   └── report.md
├── PLAN.md
└── README.md
```

---

## How to Run

### Option 1 — Single snapshot test (one-off run)

Use this to verify the pipeline is working before starting the scheduler.

```bash
python src/pipeline/pipeline_merge.py
```

This fetches live data from all 3 sources, merges them, and saves:
- `merged_understand.txt` — dataset summary (rows, columns, missing values)
- `merged_visualization.png` — 3 charts: API by state, temperature vs API, hotspots vs API

---

### Option 2 — Start the hourly scheduler (PHASE 2)

This is the main command for data collection. Run it and leave it running.

```bash
python src/pipeline/scheduler.py
```

**What it does every 60 minutes:**
1. Fetches fresh data from APIMS, METMalaysia, and NASA FIRMS
2. Merges the 3 datasets into one snapshot (~68 rows, one per station)
3. Validates the data and flags impossible values (without deleting them)
4. Appends the snapshot to `data/processed/merged_timeseries.csv`
5. Logs the result to `data/logs/scheduler.log` and the terminal

**To stop:** press `Ctrl+C` in the terminal. The current run will finish cleanly before stopping.

---

### Option 3 — Quick test (1-minute interval instead of 1 hour)

Open [src/pipeline/scheduler.py](src/pipeline/scheduler.py) and change line 113:

```python
# Change this:
INTERVAL_SECONDS = 3600

# To this:
INTERVAL_SECONDS = 60
```

Run the scheduler, wait a couple of minutes, then check that rows are appearing in `data/processed/merged_timeseries.csv`. Change it back to `3600` before leaving it running overnight.

---

## Checking Progress

**See how many rows have been collected:**

```bash
python -c "import pandas as pd; df = pd.read_csv('data/processed/merged_timeseries.csv'); print(f'{len(df)} rows | {df[\"HOUR_MYT\"].nunique()} hours collected')"
```

**View the latest snapshot:**

```bash
python -c "import pandas as pd; df = pd.read_csv('data/processed/merged_timeseries.csv'); print(df.tail(10).to_string())"
```

**Check the log file:**

```bash
# Windows
type data\logs\scheduler.log

# Or open it directly in any text editor
```

---

## Data Sources

| Source | Data | Update Frequency |
|--------|------|-----------------|
| [APIMS (DOE)](https://eqms.doe.gov.my) | API readings for 68 stations across Malaysia | Hourly |
| [METMalaysia](https://api.met.gov.my) | Temperature and rain forecast per state | Hourly snapshot |
| [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov) | Fire hotspot locations and intensity (VIIRS SNPP) | Daily (last 1 day) |

---

## Output Columns (merged_timeseries.csv)

| Column | Description |
|--------|-------------|
| `STATION_ID` | APIMS monitoring station ID |
| `STATION_LOCATION` | Station name |
| `STATE_NAME` | Malaysian state |
| `LATITUDE`, `LONGITUDE` | Station coordinates |
| `HOUR_MYT` | Timestamp (Malaysia Time, floored to the hour) |
| `API` | Air Pollution Index — the forecast target |
| `CLASS` | API band label (Good / Moderate / Unhealthy / etc.) |
| `TEMPERATURE_C` | Temperature at that state (°C) |
| `RAIN_FORECAST_SLOTS` | Number of forecast slots with rain |
| `HOTSPOT_COUNT` | Total fire hotspots detected nationally that hour |
| `FRP_MW_MEAN` | Average fire radiative power (MW) |
| `FRP_MW_MAX` | Peak fire radiative power (MW) |
| `HIGH_CONF_COUNT` | High-confidence hotspot count |
| `DATA_FLAG` | Validation flags (empty = clean row) |

---

## Malaysia API Bands (Reference)

| API Range | Category | Recommended Action |
|-----------|----------|--------------------|
| 0 – 50 | Good | Normal activities |
| 51 – 100 | Moderate | Sensitive groups take care |
| 101 – 200 | Unhealthy | Reduce prolonged outdoor activity |
| 201 – 300 | Very Unhealthy | Avoid outdoor activity |
| > 300 | Hazardous | Schools may close; stay indoors |

---

## Phase Status

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Data pipeline: fetch, clean, merge (one snapshot) | Done |
| 2 | Historical time series collection (hourly append, 2–4 weeks) | In progress |
| 3 | Feature engineering (lags, rolling averages, time features) | Not started |
| 4 | ML model training, evaluation, SHAP explainability | Not started |
| 5 | FastAPI backend (scheduler, SQLite, endpoints, offline cache) | Not started |
| 6 | HTML dashboard (map, forecast chart, alerts, cause explanation) | Not started |
| 7 | Testing: forecast accuracy, offline mode, alert thresholds | Not started |
>>>>>>> fccf1bc (FYP Files)
