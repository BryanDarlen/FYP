# Chat History / Continuity Notes

Last updated: 2026-05-08

Purpose: this file exists so future assistant sessions know where the project left off. Treat pasted chat history as context only. Do not make code changes from pasted history unless the user explicitly asks for an action.

## User Preferences

- If a task is completed, update `PLAN.md` immediately so progress is not lost.
- If a new command becomes executable, update `README.md` so the user knows what can currently be run.
- Keep the folder structure clean and reduce visual noise.
- Do not remove the Word lock file unless the user explicitly asks.
- `.claude/` was assistant-tool metadata, not project code. It was deleted on 2026-05-07.

## Current Project State

- Main project path: `C:\Users\darle\Documents\!Bryan 3rd Year FYP Project\Bryan Darlen`
- The project is an FYP system for predicting air pollution levels in Malaysia using APIMS, METMalaysia, and NASA FIRMS data.
- User clarified on 2026-05-08 that the intended forecasting context is:
  `current hour data + previous 1h, 2h, 3h, 6h, 12h, and 24h data`.
- User further clarified that `merged_timeseries.csv` can be the changing operational time-series context for the forecasting system: it should hold/update the current hour plus previous 1-24h rows needed for prediction.
- This means previous 1-24h context may be initialised from available historical endpoints for warm-up/development, as long as those rows are clearly flagged and not described as purely scheduler-collected live rows.
- `README.md`, `PLAN.md`, and code should agree on column names:
  - Use `LATITUDE`, `LONGITUDE`, not `LAT`, `LON`.
- `docs/submissions/` contains submitted `.docx` snapshots.
- Editable docs are:
  - `docs/blueprint.md`
  - `docs/report.md`
- Formal/report drift in `docs/report.md` may need supervisor discussion before changing.

## Phase 2 Status

Phase 2 code work is complete. Remaining Phase 2 task is wall-clock data accumulation.

Implemented:

- `src/pipeline/scheduler.py` runs the hourly pipeline.
- `pipeline_merge.save_snapshot()` appends to `data/processed/merged_timeseries.csv`.
- `data/processed/` is auto-created if missing.
- Scheduler was smoke-tested through one full cycle.
- CSV schema confirmed to have 19 expected columns, including station-local FIRMS `_100KM` columns and `DATA_FLAG`.
- Validation flags implemented:
  - `INVALID_API`
  - `INVALID_TEMP`
  - `INVALID_HOTSPOT`
  - `INVALID_HOTSPOT_LOCAL`
  - `FLATLINE`
  - `SPIKE`
- `FLATLINE` logic:
  - current API plus 5 prior hourly readings must be identical
  - all 6 hours must be consecutive
- `SPIKE` logic:
  - `abs(current_API - previous_hour_API) > 50`
  - previous row must be exactly `t-1h`
  - exactly 50 is not flagged

Important runnable commands:

```powershell
python src\pipeline\scheduler.py
python check_progress.py
```

## Phase 3 Status

Phase 3 code was created and marked complete in the previous chat.

File:

- `src/pipeline/feature_engineering.py`

Main function:

```python
build_features(df: pd.DataFrame) -> pd.DataFrame
```

Feature groups:

- Lag features:
  - `API_lag1h`
  - `API_lag2h`
  - `API_lag3h`
  - `API_lag6h`
  - `API_lag12h`
  - `API_lag24h`
- Rolling means:
  - `API_roll3h`
  - `API_roll6h`
  - `API_roll12h`
- Time features:
  - `HOUR_OF_DAY`
  - `DAY_OF_WEEK`
  - `IS_WEEKEND`
- Interaction:
  - `FIRE_AND_DRY`
- Quality:
  - `DATA_MISSING`

Important behavior:

- Same `build_features()` function should be used at training time and inference time to avoid train/serve skew.
- Feature generation needs about 25 consecutive hours per station before rows survive because of `API_lag24h`.

Runnable command:

```powershell
python src\pipeline\feature_engineering.py
```

Expected early behavior:

- If only 1 hour of data exists, the script says no rows survived. That is expected.

## Phase 4 Status

Phase 4 training code was created and marked complete in the previous chat.

File:

- `src/models/train.py`

Model design:

- Persistence baseline
- Linear Regression baseline
- Main model: `MultiOutputRegressor(RandomForestRegressor)`
- Forecast horizons:
  - `t+1h`
  - `t+3h`
  - `t+6h`
  - `t+12h`
  - `t+24h`
- Time-based 80/20 chronological split.
- Metrics:
  - RMSE
  - MAE
  - threshold precision/recall/confusion matrix at API 100 and API 200
- SHAP global importance is generated for the t+1h horizon.
- Per-prediction SHAP explanation is planned for Phase 5 inference/dashboard work.

Outputs when real `features.csv` exists:

- `src/models/forecast_model.pkl`
- `src/models/feature_columns.json`
- `src/models/eval_report.json`
- `src/models/baseline_report.json`
- `src/models/shap_global_importance.json`

Runnable command:

```powershell
python src\models\train.py
```

Current blocker:

- Needs `data/processed/features.csv`, which needs enough accumulated hourly data first.

## Tests

Previous chat created a `tests/` folder:

- `tests/test_validation.py`
- `tests/test_features.py`
- `tests/test_train.py`
- `tests/run_all.py`

Import side-effect fix completed on 2026-05-07:

- `fetch_apims.py` no longer fetches live APIMS data, writes Excel output, or opens plots when imported.
- Direct script behavior is preserved through `main()` and `if __name__ == "__main__":`.
- Verification passed:
  - `python tests\test_validation.py`
  - `python tests\run_all.py` (`3/3` passed)

Project cleanup completed on 2026-05-07:

- Removed generated `__pycache__/` directories from the working tree.
- Updated `.gitignore` to keep runtime logs, generated model artefacts, and test backup folders out of git noise.
- Left `docs/report.md` untouched per user instruction.

APIMS history helper added on 2026-05-07:

- `src/pipeline/fetch_apims.py` now supports `--history` mode using the existing APIMS hourly table endpoint.
- It saves an APIMS-only preview with `merged_timeseries.csv` columns and flags rows as:
  `BACKFILLED_APIMS_ONLY;WEATHER_MISSING;FIRMS_MISSING;`
- Verification command used:
  `python src\pipeline\fetch_apims.py --history --datetime "2026-05-07 15:00" --state-ids 1 --output data\processed\apims_history_preview_state1.csv`
- Result: 200 rows, 8 stations, 25 hours for state 1.
- Do not merge APIMS-only preview rows into `merged_timeseries.csv` until a weather/FIRMS missing-data strategy is explicitly chosen.

Multi-source history preview added on 2026-05-07:

- `src/pipeline/pipeline_merge.py` now supports `--history-preview`.
- It builds a preview from APIMS recent hourly history, WIS2 historical `synop-hourly` station observations, and NASA FIRMS historical pulls for the APIMS date window.
- Important correction: WIS2 `synop-hourly` is a different historical station-observation product from the METMalaysia `data.json` current weather endpoint. Do not describe it as equivalent METMalaysia historical `data.json` data.
- `src/pipeline/fetch_metmalaysia.py` now has WIS2 helpers:
  - `fetch_wis2_history(...)`
  - `preprocess_wis2(...)`
- WIS2 weather is matched to APIMS stations by nearest station coordinates in `pipeline_merge.py`. This is more accurate than a fake state join because WIS2 is station-observation data, not the same state forecast schema as `data.json`.
- Verification command used:
  `python src\pipeline\pipeline_merge.py --history-preview --datetime "2026-05-07 15:00" --state-ids 1 --output data\processed\multisource_history_preview_state1.csv`
- Result after WIS2 integration: 200 rows, 8 stations, 25 hours for state 1.
- `DATA_FLAG` count:
  `BACKFILLED_PREVIEW;WIS2_SYNOP_OBSERVED;FIRMS_HISTORY;: 200`
- Inspection showed 0 missing `TEMPERATURE_C` and 0 missing `RAIN_FORECAST_SLOTS`.
- Running `build_features()` against this preview produced 8 engineered rows, one per state-1 station at `2026-05-07 15:00`, with valid `API_lag24h`.
- Do not merge this preview into `merged_timeseries.csv` automatically. It is a controlled backfill candidate and should be reviewed first because WIS2 rain is derived from present/past weather descriptions, not the original METMalaysia forecast-slot dictionary.

All-state previous-data preview regenerated on 2026-05-07:

- Command used:
  `python src\pipeline\pipeline_merge.py --history-preview --datetime "2026-05-07 23:00" --state-ids 1-16 --output data\processed\multisource_history_preview.csv`
- Result: 1,700 rows, 68 stations, 25 hours, range `2026-05-06 23:00:00` to `2026-05-07 23:00:00`.
- `DATA_FLAG` count:
  `BACKFILLED_PREVIEW;WIS2_SYNOP_OBSERVED;FIRMS_HISTORY;: 1700`
- Running `build_features()` in-memory against this preview produced 68 rows, one per station, all at `2026-05-07 23:00:00`.
- This is useful for Phase 3 sanity checking and possible inference warm-up, but not enough for honest Phase 4 multi-horizon training because `train.py` also needs future target rows up to `t+24h`.

All-state previous-data preview extended on 2026-05-07:

- APIMS history endpoint was tested with an older endpoint datetime:
  `python src\pipeline\fetch_apims.py --history --datetime "2026-05-06 23:00" --state-ids 1 --output data\processed\apims_history_preview_state1_older.csv`
- Result: APIMS returned another 25-hour window, `2026-05-05 23:00:00` to `2026-05-06 23:00:00`, proving older windows can be stitched.
- Multi-source preview was then extended by stitching three 25-hour windows into the single ignored file:
  `data/processed/multisource_history_preview.csv`
- Combined result: 4,964 rows, 68 stations, 73 unique hours, range `2026-05-04 23:00:00` to `2026-05-07 23:00:00`.
- In-memory Phase 3/Phase 4 readiness check:
  - `build_features()` produced 3,332 feature rows across 49 feature hours.
  - `train.build_targets(...).dropna(...)` produced 1,700 target-complete rows across 25 target-complete hours.
- This means the historical preview can be used for a temporary/backfilled Phase 3 and Phase 4 execution check now, but it must remain clearly flagged as `BACKFILLED_PREVIEW;WIS2_SYNOP_OBSERVED;FIRMS_HISTORY;` and should not be described as purely real-time scheduler-collected data.

Preview Phase 3/4 execution support added on 2026-05-07:

- `src/pipeline/feature_engineering.py` now accepts:
  `python src\pipeline\feature_engineering.py --history-preview`
- It reads `data/processed/multisource_history_preview.csv` and writes ignored `data/processed/features_history_preview.csv`.
- `src/models/train.py` now accepts:
  `python src\models\train.py --history-preview`
- It reads `features_history_preview.csv` and writes ignored preview artefacts under `data/outputs/preview_model/`, not `src/models/`.
- Preview run result:
  - Phase 3: 3,332 feature rows.
  - Phase 4: 1,700 target-complete rows before NaN feature dropping; 8 incomplete feature rows dropped during training.
  - Preview model artefacts created successfully.
  - RMSE winners printed by the preview run: Linear for t+1h, t+3h, t+6h, t+12h; RandomForest for t+24h.
- `train.py` now drops rows with NaN numeric model features after target construction, with a printed count, so incomplete WIS2/preview rows do not crash scikit-learn.

Operational timeseries warm-up completed on 2026-05-08:

- `pipeline_merge.py` now accepts:
  `python src\pipeline\pipeline_merge.py --init-timeseries-from-preview --preview-input data\processed\multisource_history_preview.csv`
- This command initialises/updates `data/processed/merged_timeseries.csv` from the reviewed multi-source preview while keeping existing scheduler/live rows when `STATION_ID + HOUR_MYT` overlaps.
- Run result:
  - Existing rows before warm-up: 544
  - Preview rows: 4,964
  - Deduped overlaps: 474
  - Added rows: 4,490
  - Final operational rows: 5,034
  - Stations: 68
  - Unique hours: 74
  - Range: `2026-05-04 23:00:00` to `2026-05-08 08:00:00`
  - Clean/live rows: 544
  - Backfilled WIS2/FIRMS rows: 4,482
  - Backfilled rows with missing WIS2 weather: 8
- Default Phase 3 was then run with:
  `python src\pipeline\feature_engineering.py`
- Result: `data/processed/features.csv` created with 3,402 rows and 33 columns.
- Important accuracy note: this means the operational file is now usable for the next development phase, but the historical warm-up rows remain flagged and should not be described as purely scheduler-collected live data.

Scheduler restart catch-up added on 2026-05-08:

- User reported laptop/script downtime causing `scheduler.py` to stop for several hours.
- `src/pipeline/scheduler.py` now checks the latest 24 completed hours before each live run.
- If completed hours are missing, it automatically builds a multi-source historical catch-up using APIMS hourly history, WIS2 SYNOP historical station observations, and NASA FIRMS historical date-window data.
- It filters by missing `STATION_ID + HOUR_MYT`, so existing scheduler/live rows are not overwritten.
- Catch-up rows are flagged with `SCHEDULER_CATCHUP;` while keeping source flags such as `BACKFILLED_PREVIEW;WIS2_SYNOP_OBSERVED;FIRMS_HISTORY;`.
- The current hour is still collected through the normal live `run_once()` step after catch-up.
- The catch-up is intentionally capped at the latest 24 completed hours, matching the FYP feature requirement (`t-1h` through `t-24h`). If downtime exceeds 24 hours, the scheduler logs a warning and fills only the latest 24 completed hours.
- Logging is now more robust: if `data/logs/scheduler.log` is locked, the scheduler falls back to terminal logging instead of crashing. Noisy third-party HTTP request logs are suppressed.
- One-time catch-up run result:
  - Missing range detected: `2026-05-08 00:00:00` to `2026-05-08 07:00:00`
  - Rows added: 544
  - Final `merged_timeseries.csv`: 5,646 rows, 68 stations, range `2026-05-04 23:00:00` to `2026-05-08 09:00:00`
  - Final `features.csv` after rerunning Phase 3: 4,014 rows and 33 columns
- Added test:
  `tests/test_scheduler_catchup.py`
- Updated test runner:
  `python tests\run_all.py` now runs 4 test files.
- Verification passed:
  `OVERALL: 4/4 passed`

Phase 5 FastAPI backend started on 2026-05-08:

- User completed previous steps and moved onto step 4 / Phase 5.
- Trained model artefacts existed before backend work:
  - `src/models/forecast_model.pkl`
  - `src/models/feature_columns.json`
  - `src/models/eval_report.json`
  - `src/models/baseline_report.json`
  - `src/models/shap_global_importance.json`
- Added:
  - `src/api/__init__.py`
  - `src/api/main.py`
  - `tests/test_api.py`
- `src/api/main.py` implements:
  - `GET /status`
  - `GET /latest`
  - `GET /forecast/{station_id}`
  - `GET /alerts`
  - `GET /explain/{station_id}`
  - `POST /refresh`
- The backend loads the trained model and feature manifest once at startup.
- It writes offline/cache outputs:
  - `data/cache/latest.json`
  - `data/airquality.db`
- These generated cache/database files are ignored by git.
- The API starts an hourly in-process background refresh loop using `asyncio` because `apscheduler` is not installed in the current environment. The loop reuses scheduler catch-up and live `run_once()` logic, rebuilds `features.csv`, and refreshes the cache.
- CORS is enabled for browser/dashboard use.
- `requirements.txt` now includes `uvicorn==0.30.6`.
- API verification passed:
  - `/status`: 200
  - `/latest`: 200
  - `/alerts`: 200
  - `/forecast/CA01R`: 200
  - `/explain/CA01R`: 200
- Full test suite now runs 5 files:
  `OVERALL: 5/5 passed`

README quick-start run order added on 2026-05-08:

- User asked whether `README.md` shows what to run first.
- Added a dedicated `Quick Start / Run Order` section near the top of `README.md`.
- The order now shown is:
  1. `pip install -r requirements.txt`
  2. create `.env` from `.env.example`
  3. `python src\pipeline\scheduler.py`
  4. `python src\pipeline\feature_engineering.py`
  5. `python src\models\train.py`
  6. `python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8010 --reload`
  7. open `http://127.0.0.1:8010/docs`
- README also warns to use either the standalone scheduler or the FastAPI backend as the active collector during testing, not both for long periods.

`.env.example` restored on 2026-05-08:

- User tried `Copy-Item .env.example .env` from the project root and got a missing-file error.
- Confirmed `.env` existed locally, but `.env.example` was missing.
- Added committed-safe `.env.example` with placeholder only:
  `FIRMS_MAP_KEY=your_firms_key_here`
- Updated README to say the command should be run from the project root in PowerShell, and if `.env` already exists, skip copying and edit `.env` directly.

FastAPI Windows port command updated on 2026-05-08:

- User ran `uvicorn src.api.main:app --reload` and got `[WinError 10013]`.
- Checked port 8000; no listener was found and Windows excluded port ranges did not include 8000.
- Verified the API works using:
  `python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8010 --reload`
- Verified `/status` on port 8010 returned rows/stations and `stale=False`.
- Updated README and PLAN to use the explicit localhost/port 8010 command and URL:
  `http://127.0.0.1:8010/docs`

FastAPI `/explain` reliability fix on 2026-05-08:

- User reported `/explain/{station_id}` did not work.
- Running API check showed `/explain/CA31J` worked, but direct local inference exposed a Windows `WinError 5` risk when the trained RandomForest tried to use parallel worker threads.
- Updated `src/api/main.py` so the loaded model and its per-horizon estimators use `n_jobs=1` at API inference time.
- This keeps training fast (`n_jobs=-1` in `train.py`) but makes FastAPI prediction/explanation more reliable on Windows, especially with Uvicorn reload.
- Verification:
  - `python tests\test_api.py` passed.
  - Running server `/explain/{station_id}` returned 200 with explanation text.

Phase 6 HTML dashboard/frontend added on 2026-05-08:

- User asked to work on Phase 6 accurately and precisely.
- Added static frontend files:
  - `src/api/static/index.html`
  - `src/api/static/style.css`
  - `src/api/static/app.js`
- Updated `src/api/main.py`:
  - Serves dashboard at `/`
  - Mounts static files at `/static`
  - Keeps API metadata at `/api`
  - Adds `GET /history/{station_id}?hours=12` for the trend chart
- Dashboard sections implemented:
  - Current station map
  - Station list with search/state filter
  - Station detail panel
  - Last-12-hour trend chart with raw/3h/12h toggle
  - 1h/3h/6h/12h/24h forecast chart
  - Alerts panel
  - Explanation panel using `/explain/{station_id}`
  - Offline/stale banner
- Accuracy notes:
  - Wind direction is shown as `N/A` because the current merged dataset does not contain a wind-direction column. Do not fabricate wind data.
  - Forecast confidence band is not implemented yet because the current model serves point forecasts only.
  - Charts use native canvas, not Chart.js.
- User asked to place these accuracy notes in the suitable `.md` file because they may implement them soon.
- Added near-term follow-ups to `PLAN.md`:
  - Add wind direction only after a real official wind field is fetched/stored.
  - Add forecast confidence bands only after implementing defensible model-derived uncertainty values.
- Verification:
  - `/` returns dashboard HTML.
  - `/static/style.css` and `/static/app.js` return 200.
  - `/history/{station_id}?hours=12` returns 12 rows for tested station.
  - `python tests\test_api.py` passed with 7/7 endpoint checks.
  - `python tests\run_all.py` passed, `OVERALL: 5/5 passed`.

Dashboard map basemap fix on 2026-05-08:

- User reported that the Current Conditions panel showed only station dots and no map.
- Replaced the coordinate-only panel with Leaflet/OpenStreetMap tiles in `src/api/static/index.html` and `src/api/static/app.js`.
- Station markers now render as Leaflet markers using APIMS latitude/longitude.
- Added fallback behavior: if Leaflet or map tiles are unavailable, the dashboard keeps the station markers usable and shows a fallback note instead of silently looking blank.
- Updated `README.md` and `PLAN.md` to state that the dashboard uses Leaflet/OpenStreetMap with a fallback.
- Hardened API cache writes in `src/api/main.py`: JSON/SQLite cache write failures are now logged but do not crash startup, because Windows can temporarily lock generated cache files.
- Verification:
  - Dashboard HTML includes Leaflet CSS/JS.
  - `app.js` contains Leaflet map initialization.
  - `python tests\run_all.py` passed, `OVERALL: 5/5 passed`.

Dashboard map bounds and latest refresh fix on 2026-05-08:

- User reported that zooming/panning could drag the map out of bounds and asked for the dashboard to update to latest data when opening the link.
- Updated `src/api/static/app.js`:
  - Added strict Leaflet `maxBounds` using the project extent.
  - Added `maxBoundsViscosity: 1.0`.
  - Set minimum zoom to the initial full-map zoom, so users can zoom in and return to the whole map but not zoom/pan away from the study area.
- Updated `src/api/main.py`:
  - `GET /latest` now refreshes from `merged_timeseries.csv` first on each request.
  - If refresh fails, it falls back to `data/cache/latest.json` and includes a cache warning.
- Verification:
  - Running server `/latest` returned the current CSV-backed row count.
  - Running server `/static/app.js` included strict bounds code.
  - `python tests\run_all.py` passed, `OVERALL: 5/5 passed`.

Dashboard open-triggered live refresh and FIRMS key note on 2026-05-08:

- User wanted opening `http://127.0.0.1:8010/` to automatically update the dataset row.
- Updated `src/api/main.py` so `GET /` starts a background `run_pipeline_refresh()` task while returning the dashboard immediately.
- Updated `src/api/main.py` again so FastAPI startup also schedules the same immediate refresh, while `GET /` only schedules another one if no startup refresh is already running.
- Updated `src/api/static/app.js` so the dashboard polls every 10 seconds for the first 2 minutes after opening, then every 60 seconds. This lets the page pick up the newly appended row after the background refresh finishes.
- This means starting the backend and/or opening the dashboard triggers catch-up + live fetch + feature rebuild + cache refresh.
- `tests/test_api.py` sets `AIRQUALITY_DISABLE_AUTO_REFRESH=1` before importing the FastAPI app, so endpoint smoke tests do not make external APIMS/METMalaysia/FIRMS calls. Normal Uvicorn runs do not set this flag.
- Verified the running server advanced from latest hour `12:00` to `13:00` after opening the dashboard.
- Checked local `.env` without printing secrets and found `FIRMS_MAP_KEY` is still set to the placeholder `your_firms_key_here`.
- Updated `src/pipeline/fetch_firms.py`:
  - `load_dotenv(..., override=False)` so a placeholder `.env` does not overwrite a real OS environment variable.
  - placeholder key now raises a clear RuntimeError only when a FIRMS URL/fetch is attempted, not at import time.
- Updated README to state that dashboard auto-refresh requires a real FIRMS key in `.env`.

Dashboard FIRMS visibility fix on 2026-05-08:

- User said no FIRMS data appeared in `http://127.0.0.1:8010/`.
- Step 1 only was completed, per user instruction to stop after each step.
- Updated `src/api/static/index.html`, `src/api/static/app.js`, and `src/api/static/style.css`.
- Station detail panel now includes a dedicated `NASA FIRMS` block showing:
  - Regional hotspots (`HOTSPOT_COUNT`)
  - Regional max FRP (`FRP_MW_MAX`)
  - Local within-100-km hotspots (`HOTSPOT_COUNT_100KM`)
  - Local max FRP (`FRP_MW_MAX_100KM`)
- The status text distinguishes no hotspot, regional fire signal, and nearby fire signal.
- Verification:
  - `python tests\test_api.py` passed.
- Do not continue to the user's steps 2-4 until they say `next`.

Dashboard FIRMS explanation contribution added on 2026-05-11:

- User said `next`, meaning proceed to Step 2 only.
- Updated `src/api/main.py`:
  - Added `firms_evidence_payload(row)`.
  - `GET /explain/{station_id}` now returns structured `firms_evidence`.
  - Explanation text now uses both regional FIRMS (`HOTSPOT_COUNT`, `FRP_MW_MAX`) and station-local FIRMS (`HOTSPOT_COUNT_100KM`, `FRP_MW_MAX_100KM`).
  - The wording distinguishes:
    - nearby FIRMS signal: direct local fire evidence that can plausibly contribute smoke particles;
    - regional-only FIRMS signal: weaker contextual haze evidence;
    - no FIRMS signal: do not rely on fire activity for the current explanation.
- Updated `src/api/static/app.js` and `style.css`:
  - The Why panel now shows a `NASA FIRMS evidence` card before SHAP/top features.
- Updated `tests/test_api.py` to require structured FIRMS evidence from `/explain`.
- Updated `README.md` and `PLAN.md`.
- Verification:
  - `python tests\test_api.py` passed.
  - Direct check against a local-FIRMS row (`Kuala Terengganu, TERENGGANU`, `2026-05-11 03:00:00`) returned `strength: nearby`.
- Do not continue to the user's steps 3-4 until they say `next`.

Dashboard click/refresh responsiveness improved on 2026-05-11:

- User said `Next`, meaning proceed to Step 3 only.
- Updated `src/api/main.py`:
  - Added `SHAP_EXPLAINER` reuse so the TreeExplainer is not rebuilt for every `/explain/{station_id}` request.
  - Added `EXPLANATION_CACHE`, keyed by station/hour/current API/FIRMS values.
  - Repeated `/explain` calls for the same station/hour return cached explanation payloads.
- Updated `src/api/static/app.js`:
  - Station selection now renders station detail immediately.
  - Trend, forecast, and Why load in the background instead of blocking the click.
  - Added request tokens so stale responses from a previous station click do not overwrite the currently selected station.
  - Refresh button no longer waits for selected-station detail calls before becoming responsive again.
- Updated `tests/test_api.py` to verify repeated `/explain` reuses the cache.
- Updated `README.md` and `PLAN.md`.
- Verification:
  - `python tests\test_api.py` passed.
  - `python tests\run_all.py` passed after rerun outside sandbox with longer timeout: `OVERALL: 5/5 passed`.
  - Local timing check: first `/explain` about `1.548s`, repeated cached `/explain` about `0.058s`.
- Do not continue to the user's Step 4/minimized layout issue until they say `next`.

Dashboard station-change root-cause fix on 2026-05-11:

- User reported two remaining issues after Step 3:
  - When changing stations, the column gets bigger.
  - Station-change delay is still long.
- Root causes found:
  - `/explain` still computed local SHAP for each new station, which took about `0.65s` per uncached station and over `2s` on the first call.
  - `/forecast` and `/explain` repeatedly rebuilt latest feature rows from `merged_timeseries.csv`.
  - Station clicks still called `renderMap()`, rebuilding all Leaflet markers.
  - Explanation/FIRMS cards did not constrain text wrapping enough, so long text could widen the grid column.
- Updated `src/api/main.py`:
  - Added `USE_LOCAL_SHAP = AIRQUALITY_USE_LOCAL_SHAP == "1"`.
  - Dashboard default now uses fast precomputed model feature evidence from `shap_global_importance.json`; local SHAP can still be enabled explicitly for debugging/evaluation.
  - Added `PREDICTION_CACHE` populated by `/alerts` and reused by `/forecast` and `/explain`.
  - Added latest feature-row cache keyed by `merged_timeseries.csv` mtime.
- Updated `src/api/static/app.js`:
  - Station clicks now call `updateMapSelection()` instead of rebuilding the full map.
  - Markers/dots have `data-station-id` so active state updates directly.
- Updated `src/api/static/style.css`:
  - Dashboard grid columns use `minmax(0, ...)`.
  - Cards and explanation text use `overflow-wrap: anywhere`.
  - Map active marker/dot uses transform scaling instead of changing element dimensions.
- Updated `README.md` and `PLAN.md`.
- Verification:
  - After `/alerts` warms forecast cache, measured `/explain` calls were about `0.009-0.075s`; `/forecast` calls were about `0.009-0.012s`.
  - `python tests\test_api.py` passed.
  - `python tests\run_all.py` passed: `OVERALL: 5/5 passed`.

Dashboard station-change column expansion fix on 2026-05-11:

- User reported that pressing different stations still made block columns expand.
- Root cause: several nested grid/flex children still had default `min-width: auto`, so station-specific text could contribute extra intrinsic width to the dashboard grid.
- Updated `src/api/static/style.css` defensively:
  - `html`, `body`, and `.app-shell` prevent horizontal overflow.
  - `.dashboard-grid` and panels use strict `min-width: 0`, `max-width: 100%`.
  - Panels use `overflow: hidden` and `overflow-wrap: anywhere`.
  - `.station-item`, `.detail-heading`, `.detail-metrics`, `.firms-block`, `.firms-grid`, `.chart-block`, `.feature-list`, `.alerts-list`, `.feature-card`, and `.alert-card` now constrain inner widths.
  - Station subtext uses ellipsis instead of expanding the station list column.
  - Feature/alert card headings and spans wrap safely.
- Verification:
  - `python tests\test_api.py` passed.
  - `python tests\run_all.py` passed: `OVERALL: 5/5 passed`.

Dashboard detail-metrics expansion fix on 2026-05-11:

- User clarified the expansion happens specifically in the `detail-metrics` block.
- Decision: make the detail metric cards fixed-format UI, not content-sized UI.
- Updated `src/api/static/style.css`:
  - `.detail-metrics` now uses `grid-auto-rows: 68px`.
  - Metric cards have `min-height` and `max-height` of `68px`.
  - Metric cards use flex layout, hidden overflow, fixed single-line label/value rendering, ellipsis, and tabular numeric values.
- Updated `src/api/static/app.js`:
  - `RAIN_FORECAST_SLOTS` now uses `formatMetric(..., 0)` so rain values display as compact numeric text instead of variable raw values.
- Verification:
  - `python tests\test_api.py` passed.
  - `python tests\run_all.py` passed: `OVERALL: 5/5 passed`.

Dashboard chart expansion fix on 2026-05-11:

- User clarified the Last 12 Hours and Forecast diagrams also get bigger after station changes.
- Root cause found in `src/api/static/app.js`: `drawLineChart()` set `canvas.height = height * devicePixelRatio`, while CSS did not lock visible canvas height. Browser layout could therefore display the larger backing-buffer height after redraws.
- Updated `src/api/static/app.js`:
  - `drawLineChart()` now sets `canvas.style.height = "<attribute height>px"` before resizing the drawing buffer.
  - Canvas backing dimensions still use `Math.round(width * ratio)` and `Math.round(height * ratio)` for sharp rendering.
- Updated `src/api/static/style.css`:
  - `#trend-chart` fixed at `170px`.
  - `#forecast-chart` fixed at `190px`.
  - `.chart-block` hides overflow and is constrained to `max-width: 100%`.
- Verification:
  - `python tests\test_api.py` passed.
  - `python tests\run_all.py` passed: `OVERALL: 5/5 passed`.

Dashboard chart sharpness fix on 2026-05-11:

- User reported that after locking chart sizes, the lines became blurry.
- Root cause: `drawLineChart()` used the mutable canvas `height` attribute as the source of visual chart height. Assigning `canvas.height = height * devicePixelRatio` updates the backing-buffer height and can mutate the attribute, causing later redraws to use the wrong visual height.
- Updated `src/api/static/index.html`:
  - Replaced canvas `height` attributes with fixed `data-chart-height` values (`170` and `190`).
- Updated `src/api/static/app.js`:
  - `drawLineChart()` now reads `canvas.dataset.chartHeight`.
  - Sets `canvas.style.height` from that fixed data value.
  - Uses `getBoundingClientRect()` and device pixel ratio only for the internal backing buffer.
  - Sets `ctx.imageSmoothingEnabled = false`.
- Verification:
  - `python tests\test_api.py` passed.
  - `python tests\run_all.py` passed: `OVERALL: 5/5 passed`.

Dashboard chart summary information added on 2026-05-11:

- User said the Last 12 Hours and Forecast blocks lacked simple details about what the diagrams mean.
- Updated `src/api/static/index.html`:
  - Added `#trend-summary` under the Last 12 Hours chart.
  - Added `#forecast-summary` under the Forecast chart.
- Updated `src/api/static/app.js`:
  - Added `summarizeTrend(rows, mode)`:
    - Uses observed APIMS API values returned by `/history/{station_id}`.
    - Reports whether recent API is rising/easing/mostly stable based on first-to-last delta threshold of 5 API points.
    - Reports observed API range and active display mode (hourly readings, 3-hour average, or 12-hour average).
  - Added `summarizeForecast(payload, currentRow)`:
    - Uses `/forecast/{station_id}` predicted values.
    - Reports forecast peak API, band, horizon, final horizon value, and whether final forecast is higher/lower/similar to current API.
    - Explicitly states forecast values are predicted, not observed readings.
- Updated `src/api/static/style.css`:
  - Added `.chart-summary` styling with fixed minimum height and safe wrapping.
- Verification:
  - `python tests\test_api.py` passed.
  - `python tests\run_all.py` passed: `OVERALL: 5/5 passed`.

## Important Correction From User

On 2026-05-07, the user pasted a long leftover chat history and clarified:

> This is just chat history. I dont ask you to change anything. Is only for our next chat purposes.

Future assistant behavior:

- Read pasted history for context.
- Do not continue executing tasks from it automatically.
- Ask or wait for explicit instruction before modifying files.

## Next Practical Step

If the user asks what to do next:

1. Keep `python src\pipeline\scheduler.py` running when possible; if it stops, restarting it will now catch up missing completed hours from the latest 24-hour window automatically.
2. Use `python check_progress.py` to monitor rows/hours collected.
3. Since `features.csv` now exists from the warmed operational file and Phase 4 has trained the model, run the FastAPI backend with:

```powershell
python -m uvicorn src.api.main:app --host 127.0.0.1 --port 8010 --reload
```

4. Open `http://127.0.0.1:8010/` to test the dashboard, or `http://127.0.0.1:8010/docs` to test API endpoints. After this, the next major phase is Phase 7 testing/evaluation, unless the user wants dashboard refinements first.
