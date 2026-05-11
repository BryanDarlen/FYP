# Predicting Air Pollution Levels in Malaysia Using Real-Time Web Data

**Student:** Bryan Quinn Darlen | APU3F2511 | TP073947  
**Supervisor:** Dr. Preethi Subramanian

---

## Project Overview

This system fetches real-time air quality, weather, and fire hotspot data from three sources — **APIMS**, **METMalaysia**, and **NASA FIRMS** — merges them into a single dataset, and collects hourly snapshots to build a historical time series for forecasting Malaysia's Air Pollution Index (API).

---

## Prerequisites

Note: `requirements.txt` now includes the FastAPI backend dependency used in Phase 5.

**Python version:** 3.9 or higher

Install all required libraries before running anything:

```bash
pip install -r requirements.txt
```

Versions are pinned in `requirements.txt`. Later phases (model training, FastAPI serving) have their additional packages listed there too — uncomment them when you reach that phase.

Current note: no uncommenting is needed for Phase 5 in the current `requirements.txt`.

---

## Setup

The pipeline reads its NASA FIRMS API key from a local `.env` file (never commit this).

1. Get a free MAP_KEY from [https://firms.modaps.eosdis.nasa.gov/api/map_key/](https://firms.modaps.eosdis.nasa.gov/api/map_key/).
2. Copy the template and fill in your key. Run this from the project root folder in PowerShell:

   ```bash
   # Windows PowerShell
   Copy-Item .env.example .env
   ```
   If `.env` already exists, skip the copy command and just edit `.env`.
3. Open `.env` and replace `your_firms_key_here` with the key from step 1.

`.env` is excluded by `.gitignore`, so the key stays local. If `FIRMS_MAP_KEY` is missing or still set to the placeholder, live NASA FIRMS fetches raise a clear error during refresh.

---

## Quick Start / Run Order

Use this order when running the project from a fresh terminal.

### 1. Install dependencies

```powershell
pip install -r requirements.txt
```

### 2. Create `.env`

Run this from the project root folder in PowerShell:

```powershell
Copy-Item .env.example .env
```

If `.env` already exists, skip the copy command and just edit `.env`.

Then open `.env` and set:

```text
FIRMS_MAP_KEY=your_firms_key_here
```

Replace `your_firms_key_here` with your real FIRMS key. Leaving the placeholder will prevent live NASA FIRMS refreshes, including the dashboard's automatic refresh.

### 3. Collect or refresh operational data

For standalone data collection:

```powershell
python src\pipeline\scheduler.py
```

The scheduler fetches current data every hour. If the laptop was off or the script stopped, restarting it automatically backfills missing completed hours from the latest 24-hour window before fetching the current snapshot.

### 4. Build features

```powershell
python src\pipeline\feature_engineering.py
```

This creates `data/processed/features.csv` from `data/processed/merged_timeseries.csv`.

### 5. Train the forecasting model

```powershell
python src\models\train.py
```

This creates the model artefacts used by the backend, including `forecast_model.pkl` and `feature_columns.json`.

### 6. Start the FastAPI backend

```powershell
python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8010 --reload
```

Open:

```text
http://127.0.0.1:8010/
```

API docs:

```text
http://127.0.0.1:8010/docs
```

Use either `python src\pipeline\scheduler.py` or `python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8010 --reload` as the active collector during testing. The FastAPI backend also runs an hourly refresh loop, so running both for long periods can cause unnecessary duplicate fetches.

---

## Project Structure

```
Bryan Darlen/
├── src/
│   └── pipeline/
│       ├── fetch_apims.py          # Fetches & cleans APIMS current/recent-history air quality data
│       ├── fetch_metmalaysia.py    # Fetches METMalaysia current data and WIS2 preview observations
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
│   ├── blueprint.md                # Original concept / aims (editable)
│   ├── report.md                   # Formal investigation report (editable)
│   └── submissions/                # Submitted .docx snapshots — do not edit
│       ├── blueprint.docx
│       ├── investigation_report.docx
│       └── project_proposal_form.docx
├── .env                            # Local secrets (gitignored, you create this)
├── .env.example                    # Template for .env (committed)
├── .gitignore
├── PLAN.md
├── README.md
└── requirements.txt                # Pinned Python dependencies
```

---

## How to Run

## Forecasting Data Context

For this FYP, the forecasting context is:

```text
current hour data
+ previous 1h, 2h, 3h, 6h, 12h, and 24h data
```

`merged_timeseries.csv` is the operational time-series context for forecasting. It can change over time as new current-hour snapshots arrive, while retaining the recent 1-24h context needed by the model. When immediate previous-hour context is needed for development or warm-up, available historical endpoints can initialise that context before the scheduler has collected it naturally:

```text
APIMS hourly history + WIS2 SYNOP observations + NASA FIRMS history
```

Rows initialised from historical endpoints must remain clearly flagged, so they can be distinguished from rows collected live by the scheduler.

---

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
3. Validates the data and flags suspicious rows in the `DATA_FLAG` column (rows are *not* deleted — they stay in the dataset for inspection):
   - `INVALID_API` — API value outside 0–500
   - `INVALID_TEMP` — temperature > 50°C
   - `INVALID_HOTSPOT` / `INVALID_HOTSPOT_LOCAL` — negative hotspot count
   - `FLATLINE` — same API value for 6 consecutive hours (likely stuck sensor)
   - `SPIKE` — API change > 50 from previous hour (likely sensor glitch or real episode)
4. Appends the snapshot to `data/processed/merged_timeseries.csv`
5. Logs the result to `data/logs/scheduler.log` and the terminal

Before each live fetch, the scheduler now checks `merged_timeseries.csv` for missing completed hours in the latest 24-hour window. If the laptop was off or the script crashed, it backfills those missing completed hours from APIMS hourly history + WIS2 SYNOP observations + NASA FIRMS history, then continues with the current live snapshot. Catch-up rows are clearly flagged with `SCHEDULER_CATCHUP;` plus their source flags, such as `BACKFILLED_PREVIEW;WIS2_SYNOP_OBSERVED;FIRMS_HISTORY;`.

The automatic catch-up is intentionally capped at the latest 24 completed hours, matching the FYP feature context (`t-1h` through `t-24h`). If the laptop is off for longer than that, the scheduler backfills the latest 24 completed hours and logs a warning.

**To stop:** press `Ctrl+C` in the terminal. The current run will finish cleanly before stopping.

---

### Option 3 — Quick test (1-minute interval instead of 1 hour)

Open [src/pipeline/scheduler.py](src/pipeline/scheduler.py) and change the `INTERVAL_SECONDS` constant (around line 147):

```python
# Change this:
INTERVAL_SECONDS = 3600

# To this:
INTERVAL_SECONDS = 60
```

Run the scheduler, wait a couple of minutes, then check that rows are appearing in `data/processed/merged_timeseries.csv`. Change it back to `3600` before leaving it running overnight.

---

### Option 4 — Preview recent APIMS hourly history

Use this only as an inspection/backfill helper. It does **not** replace the scheduler because it contains APIMS history only; past METMalaysia weather and FIRMS columns are marked missing.

```bash
python src/pipeline/fetch_apims.py --history --datetime "2026-05-07 15:00" --state-ids 1-16
```

This writes `data/processed/apims_history_preview.csv` with the same columns as `merged_timeseries.csv`, but APIMS-only rows are clearly flagged:

```text
BACKFILLED_APIMS_ONLY;WEATHER_MISSING;FIRMS_MISSING;
```

Do not merge this preview into `merged_timeseries.csv` until the missing weather/FIRMS strategy is decided.

---

### Option 5 — Preview APIMS + METMalaysia + FIRMS history

Use this when you want a fuller backfill/warm-up preview before deciding whether to initialise `merged_timeseries.csv`:

```bash
python src/pipeline/pipeline_merge.py --history-preview --datetime "2026-05-07 15:00" --state-ids 1 --output data/processed/multisource_history_preview_state1.csv
```

This uses APIMS recent hourly history, fetches WIS2 `synop-hourly` historical station observations, matches WIS2 stations to APIMS stations by nearest coordinates, and fetches NASA FIRMS for the same date window. It writes a preview first; it does **not** modify `merged_timeseries.csv` unless a later step explicitly initialises the operational time-series file from reviewed preview rows.

Typical preview flags:

```text
BACKFILLED_PREVIEW;WIS2_SYNOP_OBSERVED;FIRMS_HISTORY;
```

Important: WIS2 is a different data product from the METMalaysia `data.json` current weather endpoint. `TEMPERATURE_C` comes from WIS2 `air_temperature`, while `RAIN_FORECAST_SLOTS` is derived from WIS2 present/past weather descriptions, so treat the preview as a controlled backfill candidate rather than silently mixing it into the scheduler dataset.

After reviewing the preview, initialise or update the operational time-series file with:

```bash
python src/pipeline/pipeline_merge.py --init-timeseries-from-preview --preview-input data/processed/multisource_history_preview.csv
```

This writes to `data/processed/merged_timeseries.csv`. If the same `STATION_ID` + `HOUR_MYT` exists in both files, the existing scheduler/live row is kept and the preview row is skipped for that overlap. Backfilled rows keep their `DATA_FLAG` values.

---

### Option 6 — Build engineered features (PHASE 3)

Once you have ≥ 25 hours of data per station accumulated, run:

```bash
python src/pipeline/feature_engineering.py
```

This reads `merged_timeseries.csv`, applies feature engineering (lag, rolling average, time, fire-weather interaction, missing-value handling), and writes `data/processed/features.csv`. Until 25 hours are collected, the script reports "no rows survived" and exits cleanly — that's expected.

For the controlled historical preview only:

```bash
python src/pipeline/feature_engineering.py --history-preview
```

This reads `data/processed/multisource_history_preview.csv` and writes `data/processed/features_history_preview.csv`. Keep this separate from the scheduler-collected `features.csv`.

The same `build_features()` function is also imported by the FastAPI backend at inference time (Phase 5), so the model sees identical feature semantics during training and serving.

---

### Option 7 — Train the forecasting model (PHASE 4)

Once `features.csv` has accumulated enough rows (target: 2–4 weeks of data so that the test split contains at least one full day), run:

```bash
python src/models/train.py
```

For a controlled historical preview execution check only:

```bash
python src/models/train.py --history-preview
```

This reads `features_history_preview.csv` and writes model artefacts under `data/outputs/preview_model/`, not `src/models/`.

This produces five artefacts under `src/models/`:

| File | What it contains |
|---|---|
| `forecast_model.pkl` | Trained `MultiOutputRegressor(RandomForestRegressor)` for all 5 horizons |
| `feature_columns.json` | Feature column order — used by Phase 5 backend at inference |
| `eval_report.json` | Per-horizon RMSE, MAE, and threshold precision/recall at API=100/200 |
| `baseline_report.json` | Same metrics for persistence + linear regression baselines (the floor RF must beat) |
| `shap_global_importance.json` | Global feature ranking for the t+1h horizon (sample of 500 rows) |

The script also prints a side-by-side RMSE table (Persistence | Linear | RF) so you can see at a glance whether the main model is worth its complexity.

---

### Option 8 - Start the FastAPI backend and dashboard (PHASE 5/6)

Run the backend after Phase 4 has produced `src/models/forecast_model.pkl` and `src/models/feature_columns.json`:

```bash
python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8010 --reload
```

Open:

```text
http://127.0.0.1:8010/
```

API docs:

```text
http://127.0.0.1:8010/docs
```

This explicit Windows-friendly command uses localhost and port `8010`. If the default `uvicorn src.api.main:app --reload` command gives `[WinError 10013]`, use the command above.

Implemented endpoints:

| Endpoint | Returns |
|---|---|
| `GET /status` | Last data timestamp, stale flag, row count, station count |
| `GET /latest` | Latest merged row for each station; also writes `data/cache/latest.json` |
| `GET /history/{station_id}` | Recent station rows for the dashboard trend chart |
| `GET /forecast/{station_id}` | 1h, 3h, 6h, 12h, and 24h API forecast |
| `GET /alerts` | Forecast/current stations at API alert level |
| `GET /explain/{station_id}` | Plain-language explanation plus structured NASA FIRMS evidence and SHAP/top feature evidence |
| `POST /refresh` | Manual catch-up + live fetch + feature rebuild + cache refresh |

The dashboard is served from `src/api/static/index.html` with `style.css` and `app.js`. It shows a Leaflet/OpenStreetMap station map, station list, current API, recent trend, forecast chart, alerts, and explanation panel. The map opens on the full project extent and is constrained so users can zoom in/out without dragging away from the Malaysia/regional study area. If map tiles are unavailable, the station markers remain usable with a fallback coordinate view. The station detail and explanation panels show NASA FIRMS evidence separately: regional hotspots/FRP for broader haze context and 100 km local hotspots/FRP for nearby fire evidence. Wind is shown as `N/A` because the current merged dataset does not contain a wind-direction column; this avoids fabricating a weather signal.

For responsiveness, station selection updates the visible station details immediately while trend, forecast, and explanation requests finish in the background. The backend caches latest feature rows, per-station/hour forecasts, and `/explain/{station_id}` results. The dashboard uses fast precomputed model feature evidence by default; set `AIRQUALITY_USE_LOCAL_SHAP=1` only when you specifically want slower local SHAP calculations for debugging/evaluation.

When the dashboard opens, `GET /latest` refreshes from `data/processed/merged_timeseries.csv` first, so the page reflects the latest local operational data. It falls back to `data/cache/latest.json` only if the live file refresh fails.

Starting the FastAPI backend schedules an immediate background live refresh. Opening the dashboard route (`/`) also schedules the same refresh if one is not already running: catch-up missing completed hours, fetch current external data, rebuild `features.csv`, and update the cache. The dashboard polls every 10 seconds for the first 2 minutes after opening, then every 60 seconds, so a newly appended row appears automatically after the background refresh finishes. For this to work, `.env` must contain a real `FIRMS_MAP_KEY`, not the placeholder.

While the API server is running, it also starts an hourly background refresh loop. The loop reuses the scheduler logic: catch up missing completed hours, fetch the latest live snapshot, rebuild `features.csv`, and refresh the JSON/SQLite cache. Use either the FastAPI command above or the standalone `python src/pipeline/scheduler.py` as the active collector during testing to avoid unnecessary duplicate fetches.

## Checking Progress

**Quick status of the accumulating dataset (rows, hours, API range, flag breakdown):**

```bash
python check_progress.py
```

Run this anytime in a separate terminal — it's read-only and does not interfere with the running scheduler.

**View the latest 10 rows:**

```bash
python -c "import pandas as pd; print(pd.read_csv('data/processed/merged_timeseries.csv').tail(10).to_string())"
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
| [METMalaysia](https://api.met.gov.my) `data.json` | Current weather snapshot used by the scheduler | Current snapshot |
| [WIS2 synop-hourly](https://wis2node.met.gov.my/oapi/collections/urn%3Awmo%3Amd%3Amy-metmalaysia%3Asynop-hourly/items?f=html) | Historical SYNOP station observations for controlled preview/backfill only; not the same schema as METMalaysia `data.json` | Hourly observations |
| [NASA FIRMS](https://firms.modaps.eosdis.nasa.gov) | Fire hotspot locations and intensity (VIIRS SNPP) | Daily/current, with date-window history for preview |

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
| **National FIRMS summary** (same value for every station that hour) ||
| `HOTSPOT_COUNT` | Total fire hotspots detected nationally that hour |
| `FRP_MW_MEAN` | Average fire radiative power (MW), nationally |
| `FRP_MW_MAX` | Peak fire radiative power (MW), nationally |
| `HIGH_CONF_COUNT` | High-confidence hotspot count, nationally |
| **Station-local FIRMS summary** (only fires within 100 km of the station, computed via great-circle/haversine distance) ||
| `HOTSPOT_COUNT_100KM` | Fires within 100 km of this station that hour |
| `FRP_MW_MEAN_100KM` | Mean fire radiative power of those nearby fires |
| `FRP_MW_MAX_100KM` | Strongest nearby fire intensity |
| `HIGH_CONF_COUNT_100KM` | High-confidence nearby detections only |
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
| 3 | Feature engineering (lags, rolling averages, time features, fire-weather interaction) | Code complete (waiting for 25h data/station to materialise features.csv) |
| 4 | ML model training, evaluation, SHAP explainability | Code complete (waiting for features.csv to materialise) |
| 5 | FastAPI backend (scheduler, SQLite, endpoints, offline cache) | In progress - API endpoints implemented |
| 6 | HTML dashboard (map, forecast chart, alerts, cause explanation) | In progress - dashboard implemented |
| 7 | Testing: forecast accuracy, offline mode, alert thresholds | Final evaluation not started; current synthetic/unit smoke tests pass |
