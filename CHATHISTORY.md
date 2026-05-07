# Chat History / Continuity Notes

Last updated: 2026-05-07

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

## Important Correction From User

On 2026-05-07, the user pasted a long leftover chat history and clarified:

> This is just chat history. I dont ask you to change anything. Is only for our next chat purposes.

Future assistant behavior:

- Read pasted history for context.
- Do not continue executing tasks from it automatically.
- Ask or wait for explicit instruction before modifying files.

## Next Practical Step

If the user asks what to do next:

1. Keep `python src\pipeline\scheduler.py` running to accumulate 2-4 weeks of data.
2. Use `python check_progress.py` to monitor rows/hours collected.
3. Once about 25 hours per station exist, run:

```powershell
python src\pipeline\feature_engineering.py
```

4. Once `features.csv` exists and has enough rows, run:

```powershell
python src\models\train.py
```

5. Only after a real trained model exists should Phase 5 FastAPI/backend work begin, unless the user explicitly wants to scaffold it earlier.
