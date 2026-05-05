# FYP EXECUTION PLAN
**Project:** Predicting Air Pollution Levels in Malaysia Using Real Time Web Data
**Student:** Bryan Quinn Darlen | APU3F2511 | TP073947
**Supervisor:** Dr. Preethi Subramanian

---

## What Is Already Done

| Area | Status | Files |
|------|--------|-------|
| Data fetching — APIMS, METMalaysia, NASA FIRMS | Done | `src/pipeline/fetch_apims.py`, `fetch_firms.py`, `fetch_metmalaysia.py` |
| Data preprocessing — clean, deduplicate, standardise, convert timestamps to MYT | Done | inside each fetch script |
| Data understanding — EDA, histograms, heatmaps, unique counts, describe tables | Done | `data/processed/apims_analysis.xlsx`, `merged_dataset_visualization.png` |
| Data merge — hourly alignment, state-name normalisation, left joins | Done | `src/pipeline/pipeline_merge.py`, `data/processed/merged_dataset_summary.txt` |
| Investigation report (Chapters 1–4) | Done | `docs/report.md` |

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

**Tasks:**
- [ ] Run the pipeline on a schedule (every hour) and **append** each merged snapshot to a growing dataset instead of overwriting it.
- [ ] Store accumulated records in `data/processed/merged_timeseries.csv` (or SQLite `data/airquality.db`).
- [ ] Collect at minimum 2–4 weeks of data before starting model training. Target: include at least one haze episode (API > 100 at any station).
- [ ] Add a data validation step: flag impossible values (API < 0, temperature > 50°C), sudden flatlines (same API reading for 6+ consecutive hours), and large spikes (API jump > 50 in one hour).

**Output:** A CSV/SQLite table with columns:
`STATION_ID, STATION_LOCATION, STATE_NAME, LAT, LON, HOUR_MYT, API, CLASS, TEMPERATURE_C, RAIN_FORECAST_SLOTS, HOTSPOT_COUNT, FRP_MW_MEAN, FRP_MW_MAX, HIGH_CONF_COUNT`

---

### PHASE 3 — Feature Engineering
**Why:** Raw columns are not enough. The model needs lag features (past API values) and interaction signals to learn short-term trends.

**Tasks:**
- [ ] Create **lag features** per station: `API_lag1h`, `API_lag2h`, `API_lag3h`, `API_lag6h`, `API_lag12h`, `API_lag24h`
- [ ] Create **rolling averages**: `API_roll3h`, `API_roll6h`, `API_roll12h` (these also serve the "episode shape" chart toggle in the UI)
- [ ] Create **time features**: `HOUR_OF_DAY`, `DAY_OF_WEEK`, `IS_WEEKEND`
- [ ] Create **fire-weather interaction**: `FIRE_AND_DRY` = 1 if `HOTSPOT_COUNT > 0` AND `RAIN_FORECAST_SLOTS == 0`
- [ ] Handle missing values: forward-fill gaps up to 2 hours; if gap > 2 hours, mark as `DATA_MISSING = 1`

**Output:** Enriched dataset ready for model training, saved as `data/processed/features.csv`

---

### PHASE 4 — ML Model (Short-term Forecasting, 1–24h)
**Why:** This is Objective 2 — generate 1–24h API predictions and trigger alerts.

**Tasks:**
- [ ] **Baseline first:** Train a simple Linear Regression and a persistence model (next hour = current hour) to get a baseline RMSE/MAE.
- [ ] **Main model:** Train a Random Forest or Gradient Boosting Regressor (scikit-learn) on the feature set. This is the recommended first model before trying LSTM.
- [ ] **Target variable:** `API` at `t+1h`, `t+3h`, `t+6h`, `t+12h`, `t+24h` — train one model per forecast horizon OR a multi-output regressor.
- [ ] **Split:** Use time-based split (train on earlier data, test on later data — never random shuffle for time series).
- [ ] **Evaluate:** Report RMSE, MAE, and threshold accuracy (% of time the model correctly predicts whether API crosses 100 or 200).
- [ ] **Explainability:** Use SHAP values to show which features (rain, hotspots, lag API, temperature) drove each prediction. This feeds the "why it's happening" explanation in the UI.
- [ ] **Save model:** Export trained model to `src/models/forecast_model.pkl` using `joblib`.

**Alert logic (rules, not ML):**
- API prediction ≥ 100 → "Unhealthy — stop outdoor activities"
- API prediction ≥ 200 → "Very Unhealthy — schools should consider closure"

**Output:** Trained model file + evaluation report + SHAP feature importance plot

---

### PHASE 5 — FastAPI Backend
**Why:** The backend is the bridge between the pipeline/model and the HTML dashboard. It also handles caching for offline mode.

**File to create:** `src/api/main.py`

**Tasks:**
- [ ] Set up FastAPI app with Uvicorn (`uvicorn src.api.main:app --reload`)
- [ ] Set up APScheduler to run the full pipeline (fetch → clean → merge → predict) every **60 minutes**
- [ ] Store the latest merged + predicted result in SQLite (`data/airquality.db`) AND as a JSON file (`data/cache/latest.json`) for offline fallback
- [ ] Implement these endpoints:

| Endpoint | Returns |
|----------|---------|
| `GET /latest` | Latest merged snapshot for all 68 stations |
| `GET /forecast/{station_id}` | 1–24h API forecast for one station |
| `GET /alerts` | List of stations currently above threshold |
| `GET /explain/{station_id}` | Plain-language cause explanation for a station |
| `GET /status` | Last updated timestamp + data freshness flag |

- [ ] Serve the HTML dashboard as a static file from the same FastAPI app (`/` route)
- [ ] Enable CORS so the browser can call the endpoints

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
- Chart.js for time series graphs
- Leaflet.js (optional) for map view of stations

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
| 2 | Historical time series collection (hourly append, 2–4 weeks) | ⬜ Not started |
| 3 | Feature engineering (lags, rolling avg, time features, fire-weather interaction) | ⬜ Not started |
| 4 | ML model training, evaluation, SHAP explainability | ⬜ Not started |
| 5 | FastAPI backend (scheduler, SQLite, endpoints, offline cache) | ⬜ Not started |
| 6 | HTML dashboard (map, forecast chart, alerts, cause explanation, offline banner) | ⬜ Not started |
| 7 | Testing: forecast accuracy, offline mode, alert thresholds, stress test | ⬜ Not started |

---

## Key Constraints to Keep in Mind

- **APIMS** updates hourly — schedule fetches no faster than every 60 minutes.
- **METMalaysia** (`data.json`) is a current-conditions snapshot, not historical — collect it on every scheduled run.
- **NASA FIRMS** (`/1` at the end of the URL) returns only the last 1 day — fetch daily and accumulate.
- **Offline mode** must show the *last cached data* + *"Last updated: [timestamp]"* — never show a blank screen.
- **API bands** in Malaysia use API (not US AQI) — make sure the dashboard labels and alert thresholds use Malaysia's system (Good: 0–50, Moderate: 51–100, Unhealthy: 101–200, Very Unhealthy: 201–300, Hazardous: >300).
- The forecasting model must be trained on **time-based splits** only — no random shuffle.
