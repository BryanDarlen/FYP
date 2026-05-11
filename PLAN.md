# FYP EXECUTION PLAN
**Project:** Predicting Air Pollution Levels in Malaysia Using Real Time Web Data
**Student:** Bryan Quinn Darlen | APU3F2511 | TP073947
**Supervisor:** Dr. Preethi Subramanian

---

## What Is Already Done

| Area | Status | Files |
|------|--------|-------|
| Data fetching — APIMS, METMalaysia, NASA FIRMS | Done (FIRMS bbox widened to include Sumatra + Kalimantan; APIMS/FIRMS history preview helpers and separate WIS2 SYNOP preview observations added for controlled backfill inspection) | `src/pipeline/fetch_apims.py`, `fetch_firms.py`, `fetch_metmalaysia.py` |
| Data preprocessing — clean, deduplicate, standardise, convert timestamps to MYT | Done | inside each fetch script |
| Data understanding — EDA, histograms, heatmaps, unique counts, describe tables | Done | `data/processed/apims_analysis.xlsx`, `merged_dataset_visualization.png` |
| Data merge — hourly alignment, state-name normalisation, left joins | Done | `src/pipeline/pipeline_merge.py`, `data/processed/merged_dataset_summary.txt` |
| Investigation report (Chapters 1–4) | Done | `docs/report.md` |

### Outstanding Actions (do before final submission)

- [x] **Rotate FIRMS MAP_KEY.** ✅ Done. Old key revoked at NASA; new key stored in `.env` (gitignored) and loaded via `python-dotenv` in `fetch_firms.py`. Stale Windows User-level env var also cleared.
- [ ] **(Conditional) Scrub git history of the old MAP_KEY** — only if this repo has ever been pushed to a public remote. If the repo has only lived locally, no action needed beyond the rotation. (Old key is now revoked, so it's a dead string in history either way.)

---

**Current state of merged dataset (one snapshot, 2026-03-11 21:00 MYT):**
- 68 rows (one per APIMS station), 11 columns
- API range: 18–76 (all Good or Moderate, no Unhealthy at that hour)
- Weather joined by state: temperature 26–30°C, rain forecast slots 0–19
- FIRMS: 0 hotspots at that hour (quiet period)

---

## What Is NOT Yet Done — Remaining Phases

---

### PHASE 2 — Build a Historical Time Series Dataset
**Why:** The current pipeline only captures a single snapshot. The forecasting model needs continuous hourly data over weeks/months to learn patterns and to be tested on haze vs. normal days.

**Forecasting context required by the FYP:** Each prediction row should be able to use the current hour plus previous context at `t-1h`, `t-2h`, `t-3h`, `t-6h`, `t-12h`, and `t-24h`. `merged_timeseries.csv` is the operational time-series context for this forecasting system: it can keep changing over time as the latest current-hour snapshot arrives, while retaining the previous 1-24h rows needed for feature engineering. For immediate warm-up, available historical endpoints may initialise this recent context, but those rows must remain clearly flagged.

**Storage decision:** CSV (`data/processed/merged_timeseries.csv`) — not SQLite — for the FYP. Simpler to inspect, version, and load with `pandas`. This file is the operational forecasting context, not a static one-off snapshot. Migrate to SQLite only if file grows past ~100 MB.

**Already implemented (Phase 1 → 2 carry-over):**
- [x] Hourly scheduler — `src/pipeline/scheduler.py` runs `fetch → merge → validate → save` every 60 minutes.
- [x] Append-mode save — `pipeline_merge.save_snapshot()` appends each snapshot to `merged_timeseries.csv`; never overwrites. Auto-creates `data/processed/` if missing.
- [x] Basic validation — `validate_snapshot()` flags `INVALID_API` (API < 0 or > 500), `INVALID_TEMP` (out-of-range temperature), and negative hotspot counts via the `DATA_FLAG` column.
- [x] **End-to-end smoke test** — verified scheduler runs cleanly through one full cycle: APIMS (68 rows) + METMalaysia (16 rows) + FIRMS, merge, validate, save. CSV at `data/processed/merged_timeseries.csv` confirmed to have all 19 expected columns (incl. `_100KM` station-local FIRMS) and `DATA_FLAG` clean for normal operation.

**Remaining tasks:**
- [x] **Scheduler restart catch-up** - `scheduler.py` now checks the latest 24 completed hours before each live run. Missing completed hours are backfilled from APIMS hourly history + WIS2 SYNOP observations + NASA FIRMS history, filtered by missing `STATION_ID + HOUR_MYT`, and flagged with `SCHEDULER_CATCHUP;`. Live/current collection still runs afterward. Verified on 2026-05-08 by filling 8 missing hours (`2026-05-08 00:00:00` to `2026-05-08 07:00:00`) with 544 rows.
- [ ] **Run the scheduler continuously for ≥ 2–4 weeks** to accumulate training data. Target: capture at least one haze episode (API > 100 at any station). Indonesia's typical fire/haze season is July–October per ASMC — collection started outside this window will produce a "clean-only" dataset, which is fine for baseline accuracy but won't test haze-event behaviour.
- [x] **Add flatline detection** to `validate_snapshot()`: flag stations whose API value is unchanged for ≥ 6 consecutive hours (likely sensor stuck). Append `FLATLINE;` to `DATA_FLAG`. ✅ Done — implemented in `pipeline_merge.py`; requires both identical API across 5 priors AND truly consecutive hours (no gaps). Verified with synthetic test covering stuck/gap/changing/new-station scenarios.
- [x] **Add spike detection** to `validate_snapshot()`: flag rows where API jumps by > 50 from the previous hour for the same station. Append `SPIKE;` to `DATA_FLAG`. ✅ Done — implemented in `pipeline_merge.py`; uses `abs(current - prev) > 50` to flag both up- and down-spikes; requires the prior row at *exactly* `t-1h` (no flag if there's a gap). Verified with 9-scenario test including boundary case (exactly 50 → not flagged) and flatline regression.
- [x] **(History helper)** — flatline and spike checks need access to the previous N hours, so they must read from `merged_timeseries.csv` *before* appending the new snapshot. ✅ Done — `_load_recent_history()` helper in `pipeline_merge.py`; spike detection will reuse it.
- [x] **(Controlled history preview / warm-up)** — `pipeline_merge.py --history-preview` can prepare the required current + previous 1-24h context from APIMS recent hourly history, WIS2 historical SYNOP station observations, and NASA FIRMS historical date-window data. After review, `pipeline_merge.py --init-timeseries-from-preview` can initialise the operational `merged_timeseries.csv` context while preserving existing scheduler/live rows on overlap. WIS2 is a separate observation product from METMalaysia `data.json`, so rows are flagged as `WIS2_SYNOP_OBSERVED;`. Verified on 2026-05-08: operational `merged_timeseries.csv` now has 5,034 rows, 68 stations, 74 unique hours, and range `2026-05-04 23:00:00` to `2026-05-08 08:00:00`; default Phase 3 generated 3,402 rows in `features.csv`.

**Latest verified operational dataset after catch-up (2026-05-08):** `merged_timeseries.csv` has 5,646 rows, 68 stations, and range `2026-05-04 23:00:00` to `2026-05-08 09:00:00`; default Phase 3 generated 4,014 rows in `features.csv`.

**Output:** A CSV table with 19 columns:
`STATION_ID, STATION_LOCATION, STATE_NAME, LATITUDE, LONGITUDE, HOUR_MYT, API, CLASS, TEMPERATURE_C, RAIN_FORECAST_SLOTS, HOTSPOT_COUNT, FRP_MW_MEAN, FRP_MW_MAX, HIGH_CONF_COUNT, HOTSPOT_COUNT_100KM, FRP_MW_MEAN_100KM, FRP_MW_MAX_100KM, HIGH_CONF_COUNT_100KM, DATA_FLAG`

The `DATA_FLAG` column is empty (`""` or `NaN`) for clean rows; flagged rows carry one or more semicolon-separated tags: `INVALID_API`, `INVALID_TEMP`, `INVALID_HOTSPOT`, `INVALID_HOTSPOT_LOCAL`, `FLATLINE`, `SPIKE`. See README's "What it does every 60 minutes" section for definitions.

> **Note on FIRMS columns.** Two granularities are kept:
> - The original four columns (`HOTSPOT_COUNT`, `FRP_MW_MEAN`, `FRP_MW_MAX`, `HIGH_CONF_COUNT`) are a **national** hourly summary — the same value is attached to every station for that hour. Useful for transboundary haze episodes (e.g. fires in Sumatra/Kalimantan driving haze across the whole country, as monitored regionally by the ASEAN Specialised Meteorological Centre).
> - The four `_100KM` columns are **station-local**: only fires within 100 km of the specific station, computed via great-circle (haversine) distance between each FIRMS hotspot's lat/lon (each detection is the centre of a 375 m VIIRS pixel — see NASA FIRMS VIIRS documentation) and the station's lat/lon. Useful for direct local fire impact and for cleaner SHAP explanations on the dashboard.
>
> **Why 100 km?** It is an engineering default, not a published standard — NASA FIRMS documentation does not prescribe a buffer distance for air-quality applications (FIRMS is targeted at fire management, not AQ forecasting). The choice is justified by the empirical finding from Jaffe et al. (2008, *Environ. Sci. Technol.* 42(8): 2812–2818) that wildfire smoke degrades PM2.5 in downwind areas "tens to hundreds of kilometers" from the fire source. 100 km sits in the middle of that range, balancing signal strength (close fires affect the station strongly) against false negatives (smoke can travel further). Adjustable via the `LOCAL_RADIUS_KM` constant in `pipeline_merge.py` — consider running a small sensitivity check at 50 km and 200 km during model evaluation.

---

### PHASE 3 — Feature Engineering
**Why:** Raw columns are not enough. The model needs lag features (past API values) and interaction signals to learn short-term trends.

**Where the code lives:** A new file `src/pipeline/feature_engineering.py` exposing **one** function:
```python
def build_features(df: pd.DataFrame) -> pd.DataFrame
```
which takes a sorted-by-`(STATION_ID, HOUR_MYT)` DataFrame and returns it with all engineered columns added. Always group by `STATION_ID` before computing any per-station feature, otherwise lag values from one station leak into another.

**When it runs (critical to get right):**
- **At training time** — load full `merged_timeseries.csv`, call `build_features(df)` once, save to `features.csv`, train model.
- **At inference time** — when the FastAPI backend serves `/forecast/{station_id}`, it loads the *last 25 hours* for that station from the CSV, calls the **same** `build_features()` function, takes the most recent row, and feeds it to the model.

Using one function for both prevents train/serve skew (the most common silent bug in ML systems).

**Tasks:**
- [x] Create `src/pipeline/feature_engineering.py` with `build_features(df)`. ✅ Done — single function used at both training and inference; CLI entry point materialises `data/processed/features.csv`.
- [x] **Lag features** per station: `API_lag1h`, `API_lag2h`, `API_lag3h`, `API_lag6h`, `API_lag12h`, `API_lag24h` — use `df.groupby('STATION_ID')['API'].shift(N)`. ✅ Done.
- [x] **Rolling averages** per station: `API_roll3h`, `API_roll6h`, `API_roll12h` — use `groupby('STATION_ID')['API'].rolling(N).mean()`. ✅ Done; also feed the "episode shape" chart toggle in the UI.
- [x] **Time features** from `HOUR_MYT`: `HOUR_OF_DAY` (0–23), `DAY_OF_WEEK` (0–6), `IS_WEEKEND` (0/1). ✅ Done.
- [x] **Fire-weather interaction**: `FIRE_AND_DRY = 1` if `HOTSPOT_COUNT_100KM > 0` AND `RAIN_FORECAST_SLOTS == 0`. Uses the station-local hotspot count so the feature reflects fires that can plausibly affect *this* station, not fires anywhere in Malaysia. ✅ Done.
- [x] **Missing-value handling**: forward-fill API gaps up to 2 hours per station; if gap > 2 hours, set `DATA_MISSING = 1`. Drop rows where any required lag/rolling feature is NaN (covers PLAN's `API_lag24h` rule and gap-induced NaN propagation). ✅ Done. Verified with 16-check synthetic test covering continuous data, 1-hour gap (ffilled), and 5-hour gap (partial drop).

**Output:** Enriched dataset saved as `data/processed/features.csv`. The same `build_features()` function is also imported and called by the FastAPI backend at inference time.

---

### PHASE 4 — ML Model (Short-term Forecasting, 1–24h)
**Why:** This is Objective 2 — generate 1–24h API predictions and trigger alerts.

**Tasks:**
- [x] **Baseline first:** Persistence baseline (predict next hour = current hour) + Linear Regression. ✅ Done — both implemented in `src/models/train.py`; their RMSE/MAE per horizon is saved to `baseline_report.json` for comparison.
- [x] **Main model:** `MultiOutputRegressor(RandomForestRegressor)` covering all 5 horizons in one fit. ✅ Done — `RF_PARAMS` constant in `train.py` (200 trees, `min_samples_leaf=5`, all cores).
- [x] **Target variable:** `API` at `[t+1h, t+3h, t+6h, t+12h, t+24h]` via `groupby('STATION_ID').shift(-N)`; trailing rows with any NaN target are dropped. ✅ Done — `build_targets()` function.
- [x] **Split:** 80/20 chronological by unique `HOUR_MYT`. ✅ Done — `chronological_split()` function; same cutoff applied across all stations.
- [x] **Evaluate:** Per-horizon RMSE, MAE, plus threshold confusion matrix at API=100 and API=200 with precision/recall on the crossing event. ✅ Done — `evaluate()` function; output in `eval_report.json`.
- [x] **Explainability:** `shap.TreeExplainer` on the t+1h Random Forest, sampled to 500 test rows for speed; global mean |SHAP value| ranking saved to `shap_global_importance.json`. Per-prediction SHAP for the dashboard "why" panel happens at inference time (Phase 5). ✅ Done.
- [x] **Save model:** `joblib.dump` to `src/models/forecast_model.pkl`; feature column manifest to `src/models/feature_columns.json`. ✅ Done.

**Verified:** end-to-end smoke test on synthetic 3-week dataset (20 stations × 504 hours) produces all 5 artefacts, Random Forest beats both baselines on RMSE across all horizons. The script is ready to run on real data the moment `features.csv` is materialisable (~25h of accumulation per station).

**Alert logic (rules, not ML):**
- API prediction ≥ 100 → "Unhealthy — stop outdoor activities"
- API prediction ≥ 200 → "Very Unhealthy — schools should consider closure"

**Output:** Trained model file + evaluation report + SHAP feature importance plot

---

### PHASE 5 — FastAPI Backend
**Why:** The backend is the bridge between the pipeline/model and the HTML dashboard. It also handles caching for offline mode.

**File to create:** `src/api/main.py`

**Relationship with the existing `scheduler.py`:**
The standalone `src/pipeline/scheduler.py` (Phase 2) runs the data-collection loop in its own process. In Phase 5, that loop **moves inside the FastAPI app** via APScheduler — so a single `uvicorn` process serves the API *and* runs the hourly pipeline + prediction step. After Phase 5 is working, `scheduler.py` becomes redundant and should be deleted (or kept only as a fallback for offline data collection without the API).

**Tasks:**
- [x] Set up FastAPI app with Uvicorn (`python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8010 --reload`). Done in `src/api/main.py`. The explicit localhost/port command avoids the Windows `[WinError 10013]` socket issue seen with the default command.
- [x] Configure an hourly in-process background refresh loop to run `catch-up → fetch → merge → validate → save → build_features → cache` every **60 minutes**. It reuses the same catch-up and `run_once()` logic from `scheduler.py`. APScheduler is not installed in the current environment, so this uses an `asyncio` loop for now.
- [x] At app startup, `joblib.load('src/models/forecast_model.pkl')` once and keep it in memory — never reload per request.
- [x] Store the latest merged result in SQLite (`data/airquality.db`) AND as a JSON file (`data/cache/latest.json`) for offline fallback. JSON is the source of truth for the `/latest` endpoint; SQLite is prepared for dashboard/history use.
- [ ] After Phase 5 is fully verified with the frontend, decide whether to delete `src/pipeline/scheduler.py` or keep it as a fallback collector. For now, keep it because the user specifically needs restart catch-up when running the script directly.
- [x] Implement these endpoints:

| Endpoint | Returns |
|----------|---------|
| `GET /latest` | Latest merged snapshot for all 68 stations |
| `GET /forecast/{station_id}` | 1–24h API forecast for one station |
| `GET /alerts` | List of stations currently above threshold |
| `GET /explain/{station_id}` | Plain-language cause explanation for a station |
| `GET /status` | Last updated timestamp + data freshness flag |

- [x] Serve the HTML dashboard as a static file from the same FastAPI app (`/` route). Done in Phase 6 with `src/api/static/index.html`.
- [x] Enable CORS so the browser can call the endpoints.

**Offline mode logic (in the `/latest` and `/status` endpoints):**
- If the last successful fetch was > 2 hours ago, include `"stale": true` and `"last_updated": "..."` in the response
- The frontend reads this flag and shows a "Last updated: X — data may be outdated" banner

---

### PHASE 6 — HTML Dashboard (Frontend)
**Why:** This is Objective 3 — the user-facing display that shows current conditions, forecasts, alerts, and cause explanations.

**File to create:** `src/api/static/index.html` (+ `style.css`, `app.js`)

**Dashboard sections to build:**

1. **Current Air Quality Map / Station List**
   - Show all 68 APIMS stations with their current API value and colour-coded band (Good/Moderate/Unhealthy/Very Unhealthy/Hazardous)
   - Source: `GET /latest`

2. **Station Detail Panel** (click a station)
   - Real-time API reading + band label
   - Last 12h trend line (using stored history)
   - Toggle: raw hourly / 3h rolling average / 12h rolling average
   - Wind direction arrow + rain forecast slots
   - Hotspot count nearby

3. **Forecast Chart**
   - 1–24h API forecast line with a shaded confidence band
   - Threshold lines drawn at API = 100 and API = 200
   - Source: `GET /forecast/{station_id}`

4. **Alert Panel**
   - Stations currently above 100 or 200, sorted by severity
   - Recommended action per band (match Malaysia API bands exactly)
   - Source: `GET /alerts`

5. **"Why Is Air Quality Like This?" Explanation Box**
   - Plain-language text: e.g. "Air quality in Selangor is Moderate. Rainfall forecast is low (2 slots) and there are 5 active fire hotspots nearby. Wind from the southwest may be carrying smoke toward this station."
   - This logic uses: RAIN_FORECAST_SLOTS, HOTSPOT_COUNT, FRP_MW_MAX, and SHAP top features
   - Source: `GET /explain/{station_id}`

6. **Offline Banner**
   - Shown when `stale: true` from `/status`
   - Text: "Last updated: [timestamp] — Live data unavailable. Showing cached data."

**Frontend stack:**
- Plain HTML + CSS + vanilla JavaScript (no framework needed)
- `fetch()` polling every 60 seconds to refresh data
- Native canvas charts for trend/forecast graphs
- Leaflet/OpenStreetMap station map with a coordinate fallback if map tiles are unavailable

**Phase 6 implementation status:**
- [x] `src/api/static/index.html`
- [x] `src/api/static/style.css`
- [x] `src/api/static/app.js`
- [x] Dashboard served at `/`
- [x] API docs remain available at `/docs`
- [x] Station map/list uses `GET /latest`; map is constrained to the project map extent so users cannot drag out of bounds.
- [x] Last-12-hour trend uses `GET /history/{station_id}`
- [x] Forecast chart uses `GET /forecast/{station_id}`
- [x] Alert panel uses `GET /alerts`
- [x] Explanation panel uses `GET /explain/{station_id}`
- [x] Offline/stale banner uses `/latest.status` and `/status`
- [x] Station detail now shows explicit NASA FIRMS evidence: regional hotspot count, regional max FRP, local 100 km hotspot count, and local max FRP.
- [x] `GET /explain/{station_id}` now returns structured `firms_evidence`, and the Why panel shows whether NASA FIRMS is direct nearby fire evidence, weaker regional context, or not currently supporting a fire-driven explanation.
- [x] Station clicks and refresh are more responsive: station detail renders immediately, trend/forecast/Why load in the background, latest feature rows and per-station forecasts are cached, `/explain/{station_id}` is cached per station/hour, and fast precomputed model feature evidence is used by default instead of slow local SHAP on every click.
- [x] Dashboard columns are constrained against station-change expansion: panels/cards/details use `min-width: 0`, `max-width: 100%`, defensive text wrapping, fixed grid behavior, and active map markers scale via transform instead of changing layout dimensions.
- [x] Detail metric cards are fixed-format: the Rain Slots / Local Hotspots / Wind cards have a fixed row height, single-line labels and values, hidden overflow, tabular numeric values, and shortened numeric formatting so station changes cannot resize that block.
- [x] Last-12-hours and Forecast canvases are fixed-format: visible chart heights are locked at 170px and 190px while the internal canvas buffer still scales for device-pixel-ratio rendering.
- [x] Last-12-hours and Forecast blocks now include simple station-specific summaries: observed APIMS trend/range for recent history and model forecast peak/final-horizon interpretation for future API estimates.
- [x] Starting the FastAPI backend schedules an immediate background live refresh; opening the dashboard also schedules one if needed. The dashboard polls quickly during the first 2 minutes, and `/latest` refreshes from `merged_timeseries.csv` before falling back to cache.
- [ ] Wind direction arrow remains unavailable until a wind-direction source/column is added; the dashboard shows `N/A` instead of inventing wind data.
- [ ] Forecast confidence band remains future work; the current model outputs point forecasts only.

**Near-term accuracy follow-ups if time allows:**
- **Wind direction:** Add only after the pipeline has a real wind-direction field from an official source. Possible implementation path: fetch wind direction/speed from a suitable METMalaysia/WIS2 observation field, store it in `merged_timeseries.csv`, include it in `features.csv` if useful, and then replace the dashboard's `N/A` wind display with the actual direction arrow. Do not infer wind direction from station location or hotspot position.
- **Forecast confidence band:** Add only after defining a defensible uncertainty method. Possible implementation path: use per-tree RandomForest prediction spread or quantile-style prediction intervals, expose lower/median/upper values from `/forecast/{station_id}`, and then draw the shaded band on the dashboard. Do not show a decorative confidence band without model-derived uncertainty values.

---

### PHASE 7 — Testing & Evaluation
**Tasks:**
- [ ] Test pipeline on normal day vs. simulated haze episode (manually inject high API/hotspot values)
- [ ] Test offline mode: disable internet, verify dashboard still loads cached data
- [ ] Test alert thresholds: verify correct stations trigger at API ≥ 100 and API ≥ 200
- [ ] Test forecast accuracy on held-out test set (report RMSE, MAE, threshold accuracy)
- [ ] Check that "Why it's happening" explanation changes correctly when rain/hotspot conditions change
- [ ] Stress-test the scheduler: run for 24h continuous, check for memory leaks or failed fetches

---

## Full System Architecture (Final State)

```
┌─────────────────────────────────────────────────────┐
│  DATA SOURCES (external, updated hourly)            │
│  APIMS  ·  METMalaysia  ·  NASA FIRMS               │
└───────────────────┬─────────────────────────────────┘
                    │ fetch (every 60 min via APScheduler)
┌───────────────────▼─────────────────────────────────┐
│  src/pipeline/                                      │
│  fetch_apims.py · fetch_metmalaysia.py · fetch_firms│
│  pipeline_merge.py  →  feature engineering          │
└───────────────────┬─────────────────────────────────┘
                    │ merged + feature table
┌───────────────────▼─────────────────────────────────┐
│  src/models/forecast_model.pkl                      │
│  → generates 1–24h API predictions + SHAP explain   │
└───────────────────┬─────────────────────────────────┘
                    │ predictions + alerts + explanations
┌───────────────────▼─────────────────────────────────┐
│  SQLite  data/airquality.db                         │
│  JSON cache  data/cache/latest.json  (offline fallback)│
└───────────────────┬─────────────────────────────────┘
                    │ FastAPI endpoints
┌───────────────────▼─────────────────────────────────┐
│  src/api/main.py  (FastAPI + Uvicorn)               │
│  /latest · /forecast · /alerts · /explain · /status │
└───────────────────┬─────────────────────────────────┘
                    │ HTTP fetch() every 60s
┌───────────────────▼─────────────────────────────────┐
│  src/api/static/index.html                          │
│  Dashboard: map · trend · forecast · alerts · why   │
│  Offline banner when stale=true                     │
└─────────────────────────────────────────────────────┘
```

---

## Phase Checklist Summary

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Data pipeline: fetch, clean, merge (one snapshot) | ✅ Done |
| 2 | Historical time series collection (hourly append, 2–4 weeks) | 🟡 In progress — **all code complete** (scheduler, append, all 5 validation flags, end-to-end smoke test passed). Only remaining task: leave the scheduler running for ≥ 2–4 weeks to accumulate training data. |
| 3 | Feature engineering (lags, rolling avg, time features, fire-weather interaction) | ✅ Code complete — `feature_engineering.py` ready for scheduler data and supports `--history-preview` for the separate WIS2/APIMS/FIRMS historical preview |
| 4 | ML model training, evaluation, SHAP explainability | ✅ Code complete — `train.py` ready for scheduler features and supports `--history-preview` to write temporary artefacts under `data/outputs/preview_model/` |
| 5 | FastAPI backend (scheduler, SQLite, endpoints, offline cache) | ⬜ Not started |
| 6 | HTML dashboard (map, forecast chart, alerts, cause explanation, offline banner) | 🟨 In progress - dashboard implemented |
| 7 | Testing: forecast accuracy, offline mode, alert thresholds, stress test | ⬜ Final evaluation not started; current synthetic/unit smoke tests pass (`python tests/run_all.py`) |

---

## Key Constraints to Keep in Mind

- **APIMS** updates hourly — schedule fetches no faster than every 60 minutes.
- **METMalaysia** (`data.json`) is a current-conditions snapshot, not historical — collect it on every scheduled run. **WIS2 `synop-hourly` is a different historical station-observation product**, so use it only for clearly flagged preview/backfill rows unless the methodology/report explicitly justifies mixing it with the scheduler dataset.
- **NASA FIRMS** (`/1` at the end of the URL) returns only the last 1 day — fetch daily and accumulate.
- **Offline mode** must show the *last cached data* + *"Last updated: [timestamp]"* — never show a blank screen.
- **API bands** in Malaysia use API (not US AQI) — make sure the dashboard labels and alert thresholds use Malaysia's system (Good: 0–50, Moderate: 51–100, Unhealthy: 101–200, Very Unhealthy: 201–300, Hazardous: >300).
- The forecasting model must be trained on **time-based splits** only — no random shuffle.
