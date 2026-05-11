"""
Phase 5 - FastAPI backend for the air-quality forecasting system.

Run:
    uvicorn src.api.main:app --reload
"""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import sys
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles


PROJECT_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_DIR = PROJECT_ROOT / "src" / "pipeline"
MODELS_DIR = PROJECT_ROOT / "src" / "models"
DATA_DIR = PROJECT_ROOT / "data"
PROCESSED_DIR = DATA_DIR / "processed"
CACHE_DIR = DATA_DIR / "cache"
DB_PATH = DATA_DIR / "airquality.db"
STATIC_DIR = Path(__file__).resolve().parent / "static"

TIMESERIES_PATH = PROCESSED_DIR / "merged_timeseries.csv"
FEATURES_PATH = PROCESSED_DIR / "features.csv"
MODEL_PATH = MODELS_DIR / "forecast_model.pkl"
FEATURE_COLUMNS_PATH = MODELS_DIR / "feature_columns.json"
SHAP_IMPORTANCE_PATH = MODELS_DIR / "shap_global_importance.json"
LATEST_CACHE_PATH = CACHE_DIR / "latest.json"

MYT = timezone(timedelta(hours=8))
FORECAST_HORIZONS = [1, 3, 6, 12, 24]
INTERVAL_SECONDS = 3600
STALE_AFTER_HOURS = 2
AUTO_REFRESH_DISABLED = os.environ.get("AIRQUALITY_DISABLE_AUTO_REFRESH") == "1"
USE_LOCAL_SHAP = os.environ.get("AIRQUALITY_USE_LOCAL_SHAP") == "1"

sys.path.insert(0, str(PIPELINE_DIR))
from feature_engineering import build_features  # noqa: E402
from scheduler import backfill_missing_history, run_once  # noqa: E402


app = FastAPI(
    title="Malaysia Air Quality Forecast API",
    description="Phase 5 backend for APIMS + METMalaysia/WIS2 + NASA FIRMS forecasting.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

MODEL = None
FEATURE_COLUMNS: list[str] = []
FEATURE_FILL_VALUES: dict[str, float] = {}
SHAP_RANKING: list[dict[str, Any]] = []
SHAP_EXPLAINER: Any = None
EXPLANATION_CACHE: dict[str, dict[str, Any]] = {}
PREDICTION_CACHE: dict[str, list[float]] = {}
LATEST_FEATURE_ROWS_CACHE: pd.DataFrame | None = None
LATEST_FEATURE_ROWS_MTIME: float | None = None
_background_task: asyncio.Task | None = None
_startup_refresh_task: asyncio.Task | None = None
_refresh_lock = asyncio.Lock()


def now_myt() -> pd.Timestamp:
    return pd.Timestamp.now(tz=MYT).tz_localize(None)


def api_band(api_value: Any) -> str:
    if api_value is None or pd.isna(api_value):
        return "Unknown"
    api = float(api_value)
    if api <= 50:
        return "Good"
    if api <= 100:
        return "Moderate"
    if api <= 200:
        return "Unhealthy"
    if api <= 300:
        return "Very Unhealthy"
    return "Hazardous"


def alert_message(api_value: float) -> str:
    if api_value >= 300:
        return "Hazardous - avoid outdoor activity and follow official guidance."
    if api_value >= 200:
        return "Very Unhealthy - avoid outdoor activity; schools should consider precautions."
    if api_value >= 100:
        return "Unhealthy - reduce outdoor activity, especially sensitive groups."
    return "No alert."


def clean_value(value: Any) -> Any:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, np.generic):
        return value.item()
    return value


def clean_record(record: dict[str, Any]) -> dict[str, Any]:
    return {str(k): clean_value(v) for k, v in record.items()}


def require_file(path: Path, label: str) -> None:
    if not path.exists():
        raise HTTPException(status_code=503, detail=f"{label} not found: {path}")


def load_model_artifacts() -> None:
    global MODEL, FEATURE_COLUMNS, FEATURE_FILL_VALUES, SHAP_RANKING, SHAP_EXPLAINER

    require_file(MODEL_PATH, "Trained model")
    require_file(FEATURE_COLUMNS_PATH, "Feature column manifest")

    MODEL = joblib.load(MODEL_PATH)
    SHAP_EXPLAINER = None
    EXPLANATION_CACHE.clear()
    PREDICTION_CACHE.clear()
    # The model was trained with n_jobs=-1 for speed. At API inference time,
    # keep prediction single-threaded to avoid Windows permission/socket issues
    # when Uvicorn is running with reload enabled.
    if hasattr(MODEL, "n_jobs"):
        MODEL.n_jobs = 1
    for estimator in getattr(MODEL, "estimators_", []):
        if hasattr(estimator, "n_jobs"):
            estimator.n_jobs = 1

    manifest = json.loads(FEATURE_COLUMNS_PATH.read_text(encoding="utf-8"))
    FEATURE_COLUMNS = manifest["feature_columns"]

    if FEATURES_PATH.exists():
        features = pd.read_csv(FEATURES_PATH)
        medians = features[FEATURE_COLUMNS].median(numeric_only=True).fillna(0)
        FEATURE_FILL_VALUES = {col: float(medians.get(col, 0.0)) for col in FEATURE_COLUMNS}
    else:
        FEATURE_FILL_VALUES = {col: 0.0 for col in FEATURE_COLUMNS}

    if SHAP_IMPORTANCE_PATH.exists():
        payload = json.loads(SHAP_IMPORTANCE_PATH.read_text(encoding="utf-8"))
        SHAP_RANKING = payload.get("ranking", [])
    else:
        SHAP_RANKING = []


def load_timeseries() -> pd.DataFrame:
    require_file(TIMESERIES_PATH, "Timeseries CSV")
    df = pd.read_csv(TIMESERIES_PATH, parse_dates=["HOUR_MYT"])
    if df.empty:
        raise HTTPException(status_code=503, detail="merged_timeseries.csv is empty")
    return df


def latest_snapshot(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.sort_values(["STATION_ID", "HOUR_MYT"])
        .drop_duplicates(subset=["STATION_ID"], keep="last")
        .sort_values(["STATE_NAME", "STATION_LOCATION"])
        .reset_index(drop=True)
    )


def latest_feature_rows(df: pd.DataFrame | None = None) -> pd.DataFrame:
    global LATEST_FEATURE_ROWS_CACHE, LATEST_FEATURE_ROWS_MTIME
    if df is None and TIMESERIES_PATH.exists():
        mtime = TIMESERIES_PATH.stat().st_mtime
        if LATEST_FEATURE_ROWS_CACHE is not None and LATEST_FEATURE_ROWS_MTIME == mtime:
            return LATEST_FEATURE_ROWS_CACHE.copy()

    source = load_timeseries() if df is None else df
    features = build_features(source)
    if features.empty:
        raise HTTPException(
            status_code=503,
            detail="Not enough history to build forecast features. Need at least 25 hours per station.",
        )
    latest_rows = (
        features.sort_values(["STATION_ID", "HOUR_MYT"])
        .drop_duplicates(subset=["STATION_ID"], keep="last")
        .reset_index(drop=True)
    )
    if df is None and TIMESERIES_PATH.exists():
        LATEST_FEATURE_ROWS_CACHE = latest_rows.copy()
        LATEST_FEATURE_ROWS_MTIME = TIMESERIES_PATH.stat().st_mtime
    return latest_rows


def prepare_model_matrix(features: pd.DataFrame) -> pd.DataFrame:
    if MODEL is None:
        load_model_artifacts()

    X = features.copy()
    for col in FEATURE_COLUMNS:
        if col not in X.columns:
            X[col] = FEATURE_FILL_VALUES.get(col, 0.0)
    X = X[FEATURE_COLUMNS].apply(pd.to_numeric, errors="coerce")
    return X.fillna(FEATURE_FILL_VALUES).fillna(0)


def predict_rows(features: pd.DataFrame) -> np.ndarray:
    if MODEL is None:
        load_model_artifacts()
    X = prepare_model_matrix(features)
    return np.asarray(MODEL.predict(X.to_numpy()))


def station_hour_key(row: pd.Series) -> str:
    return "|".join(
        str(clean_value(row.get(col)))
        for col in ["STATION_ID", "HOUR_MYT", "API", "API_lag1h", "HOTSPOT_COUNT", "HOTSPOT_COUNT_100KM"]
    )


def cached_prediction(row: pd.Series) -> np.ndarray:
    key = station_hour_key(row)
    if key not in PREDICTION_CACHE:
        if len(PREDICTION_CACHE) >= 512:
            PREDICTION_CACHE.clear()
        PREDICTION_CACHE[key] = [float(value) for value in predict_rows(pd.DataFrame([row]))[0]]
    return np.asarray(PREDICTION_CACHE[key])


def cache_predictions(rows: pd.DataFrame, predictions: np.ndarray) -> None:
    for i, (_, row) in enumerate(rows.iterrows()):
        PREDICTION_CACHE[station_hour_key(row)] = [float(value) for value in predictions[i]]


def forecast_payload(row: pd.Series, prediction: np.ndarray) -> dict[str, Any]:
    forecasts = [
        {
            "horizon_hours": int(h),
            "api": round(float(prediction[i]), 1),
            "band": api_band(float(prediction[i])),
        }
        for i, h in enumerate(FORECAST_HORIZONS)
    ]
    current_api = float(row.get("API", 0) or 0)
    max_api = max(item["api"] for item in forecasts)
    return {
        "station_id": str(row["STATION_ID"]),
        "station_location": clean_value(row.get("STATION_LOCATION")),
        "state_name": clean_value(row.get("STATE_NAME")),
        "source_hour_myt": clean_value(row.get("HOUR_MYT")),
        "current_api": clean_value(row.get("API")),
        "current_band": api_band(row.get("API")),
        "forecast": forecasts,
        "max_forecast_api": max_api,
        "alert": max_api >= 100 or current_api >= 100,
        "message": alert_message(max(max_api, current_api)),
    }


def status_payload(df: pd.DataFrame) -> dict[str, Any]:
    latest_hour = pd.to_datetime(df["HOUR_MYT"], errors="coerce").max()
    age_hours = (now_myt() - latest_hour).total_seconds() / 3600 if pd.notna(latest_hour) else None
    return {
        "last_updated": clean_value(latest_hour),
        "stale": bool(age_hours is None or age_hours > STALE_AFTER_HOURS),
        "age_hours": None if age_hours is None else round(float(age_hours), 2),
        "rows": int(len(df)),
        "stations": int(df["STATION_ID"].nunique()),
        "source": "data/processed/merged_timeseries.csv",
    }


def init_database() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS latest_rows (
                station_id TEXT PRIMARY KEY,
                hour_myt TEXT NOT NULL,
                payload_json TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS api_status (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )


def write_cache(payload: dict[str, Any]) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    try:
        LATEST_CACHE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError as exc:
        print(f"[API] Could not write latest JSON cache: {exc}")

    try:
        init_database()
        generated_at = payload.get("generated_at", "")
        with sqlite3.connect(DB_PATH) as conn:
            for row in payload.get("latest", []):
                conn.execute(
                    """
                    INSERT OR REPLACE INTO latest_rows (station_id, hour_myt, payload_json)
                    VALUES (?, ?, ?)
                    """,
                    (str(row.get("STATION_ID")), str(row.get("HOUR_MYT")), json.dumps(row)),
                )
            conn.execute(
                "INSERT OR REPLACE INTO api_status (key, value) VALUES (?, ?)",
                ("generated_at", generated_at),
            )
    except (OSError, sqlite3.Error) as exc:
        print(f"[API] Could not write SQLite cache: {exc}")


def read_cache() -> dict[str, Any] | None:
    if not LATEST_CACHE_PATH.exists():
        return None
    return json.loads(LATEST_CACHE_PATH.read_text(encoding="utf-8"))


def refresh_cache_from_files() -> dict[str, Any]:
    df = load_timeseries()
    latest = latest_snapshot(df)
    payload = {
        "generated_at": clean_value(now_myt()),
        "status": status_payload(df),
        "latest": [clean_record(row) for row in latest.to_dict(orient="records")],
    }
    write_cache(payload)
    return payload


def rebuild_features_file() -> pd.DataFrame:
    df = load_timeseries()
    features = build_features(df)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    features.to_csv(FEATURES_PATH, index=False)
    return features


async def run_pipeline_refresh() -> dict[str, Any]:
    async with _refresh_lock:
        await backfill_missing_history()
        await run_once()
        rebuild_features_file()
        return refresh_cache_from_files()


async def run_startup_refresh() -> None:
    try:
        await run_pipeline_refresh()
    except Exception:
        print("[API] Dashboard startup refresh failed:")
        print(traceback.format_exc())


def schedule_startup_refresh() -> None:
    global _startup_refresh_task
    if AUTO_REFRESH_DISABLED:
        return
    if _startup_refresh_task and not _startup_refresh_task.done():
        return
    _startup_refresh_task = asyncio.create_task(run_startup_refresh())


async def periodic_pipeline_loop() -> None:
    while True:
        await asyncio.sleep(INTERVAL_SECONDS)
        try:
            await run_pipeline_refresh()
        except Exception:
            print("[API] Scheduled refresh failed:")
            print(traceback.format_exc())


@app.on_event("startup")
async def startup() -> None:
    global _background_task
    load_model_artifacts()
    init_database()
    if TIMESERIES_PATH.exists():
        refresh_cache_from_files()
    _background_task = asyncio.create_task(periodic_pipeline_loop())
    schedule_startup_refresh()


@app.on_event("shutdown")
async def shutdown() -> None:
    if _background_task:
        _background_task.cancel()
    if _startup_refresh_task:
        _startup_refresh_task.cancel()


@app.get("/")
async def root() -> FileResponse:
    schedule_startup_refresh()
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api")
def api_info() -> dict[str, Any]:
    return {
        "name": "Malaysia Air Quality Forecast API",
        "phase": "Phase 5/6",
        "endpoints": [
            "/status",
            "/latest",
            "/history/{station_id}",
            "/forecast/{station_id}",
            "/alerts",
            "/explain/{station_id}",
        ],
    }


@app.get("/status")
def get_status() -> dict[str, Any]:
    df = load_timeseries()
    status = status_payload(df)
    status["model_loaded"] = MODEL is not None
    status["cache_file"] = str(LATEST_CACHE_PATH.relative_to(PROJECT_ROOT))
    status["sqlite_db"] = str(DB_PATH.relative_to(PROJECT_ROOT))
    return status


@app.get("/latest")
def get_latest() -> JSONResponse:
    try:
        payload = refresh_cache_from_files()
    except Exception as exc:
        cache = read_cache()
        if cache is None:
            raise HTTPException(status_code=503, detail=f"Latest data unavailable: {exc}") from exc
        cache["cache_warning"] = f"Serving cached data because refresh failed: {exc}"
        payload = cache
    return JSONResponse(payload)


@app.get("/forecast/{station_id}")
def get_forecast(station_id: str) -> dict[str, Any]:
    rows = latest_feature_rows()
    match = rows[rows["STATION_ID"].astype(str) == str(station_id)]
    if match.empty:
        raise HTTPException(status_code=404, detail=f"Station not found or not forecast-ready: {station_id}")
    row = match.iloc[0]
    prediction = cached_prediction(row)
    return forecast_payload(row, prediction)


@app.get("/history/{station_id}")
def get_history(
    station_id: str,
    hours: int = Query(default=12, ge=1, le=168),
) -> dict[str, Any]:
    df = load_timeseries()
    station_rows = df[df["STATION_ID"].astype(str) == str(station_id)].copy()
    if station_rows.empty:
        raise HTTPException(status_code=404, detail=f"Station not found: {station_id}")

    station_rows["HOUR_MYT"] = pd.to_datetime(station_rows["HOUR_MYT"], errors="coerce")
    station_rows = station_rows.dropna(subset=["HOUR_MYT"]).sort_values("HOUR_MYT")
    cutoff = station_rows["HOUR_MYT"].max() - pd.Timedelta(hours=hours - 1)
    station_rows = station_rows[station_rows["HOUR_MYT"] >= cutoff].copy()

    keep = [
        "STATION_ID", "STATION_LOCATION", "STATE_NAME", "HOUR_MYT", "API", "CLASS",
        "TEMPERATURE_C", "RAIN_FORECAST_SLOTS", "HOTSPOT_COUNT",
        "HOTSPOT_COUNT_100KM", "DATA_FLAG",
    ]
    for col in keep:
        if col not in station_rows.columns:
            station_rows[col] = pd.NA

    return {
        "station_id": str(station_id),
        "hours_requested": int(hours),
        "count": int(len(station_rows)),
        "history": [
            clean_record(row)
            for row in station_rows[keep].to_dict(orient="records")
        ],
    }


@app.get("/alerts")
def get_alerts() -> dict[str, Any]:
    rows = latest_feature_rows()
    predictions = predict_rows(rows)
    cache_predictions(rows, predictions)
    forecasts = [forecast_payload(row, predictions[i]) for i, (_, row) in enumerate(rows.iterrows())]
    alerts = [item for item in forecasts if item["alert"]]
    alerts.sort(key=lambda item: item["max_forecast_api"], reverse=True)
    return {
        "generated_at": clean_value(now_myt()),
        "count": len(alerts),
        "alerts": alerts,
    }


def shap_local_ranking(row: pd.Series) -> list[dict[str, Any]]:
    global SHAP_EXPLAINER
    if MODEL is None:
        load_model_artifacts()
    try:
        import shap

        estimator = MODEL.estimators_[0]
        X = prepare_model_matrix(pd.DataFrame([row]))
        if SHAP_EXPLAINER is None:
            SHAP_EXPLAINER = shap.TreeExplainer(estimator)
        values = np.asarray(SHAP_EXPLAINER.shap_values(X.to_numpy()))[0]
        ranking = sorted(zip(FEATURE_COLUMNS, values), key=lambda pair: abs(float(pair[1])), reverse=True)
        return [
            {"feature": feature, "shap_value": round(float(value), 4)}
            for feature, value in ranking[:5]
        ]
    except Exception:
        return [
            {"feature": item.get("feature"), "mean_abs_shap": item.get("mean_abs_shap")}
            for item in SHAP_RANKING[:5]
        ]


def fast_feature_ranking(row: pd.Series) -> list[dict[str, Any]]:
    if SHAP_RANKING:
        return [
            {
                "feature": item.get("feature"),
                "mean_abs_shap": item.get("mean_abs_shap"),
                "value": clean_value(row.get(str(item.get("feature")))),
            }
            for item in SHAP_RANKING[:5]
            if item.get("feature")
        ]

    return [
        {"feature": col, "value": clean_value(row.get(col))}
        for col in FEATURE_COLUMNS[:5]
    ]


def feature_ranking(row: pd.Series) -> list[dict[str, Any]]:
    if USE_LOCAL_SHAP:
        return shap_local_ranking(row)
    return fast_feature_ranking(row)


def explanation_cache_key(row: pd.Series) -> str:
    return "|".join(
        str(clean_value(row.get(col)))
        for col in ["STATION_ID", "HOUR_MYT", "API", "HOTSPOT_COUNT", "HOTSPOT_COUNT_100KM"]
    )


def firms_evidence_payload(row: pd.Series) -> dict[str, Any]:
    regional_hotspots = float(row.get("HOTSPOT_COUNT", 0) or 0)
    regional_frp_max = float(row.get("FRP_MW_MAX", 0) or 0)
    local_hotspots = float(row.get("HOTSPOT_COUNT_100KM", 0) or 0)
    local_frp_max = float(row.get("FRP_MW_MAX_100KM", 0) or 0)

    if local_hotspots > 0:
        strength = "nearby"
        interpretation = (
            f"NASA FIRMS detected {local_hotspots:.0f} hotspot(s) within 100 km "
            f"of this station, with local max FRP {local_frp_max:.2f} MW. "
            "This is direct local fire evidence that can plausibly contribute smoke particles."
        )
    elif regional_hotspots > 0:
        strength = "regional"
        interpretation = (
            f"NASA FIRMS detected {regional_hotspots:.0f} regional hotspot(s), "
            f"with regional max FRP {regional_frp_max:.2f} MW, but none within 100 km "
            "of this station. This is weaker contextual haze evidence rather than a direct local fire signal."
        )
    else:
        strength = "none"
        interpretation = (
            "NASA FIRMS detected no regional or nearby hotspot signal for this station hour, "
            "so the current explanation should not rely on fire activity."
        )

    return {
        "strength": strength,
        "regional_hotspots": round(regional_hotspots, 0),
        "regional_frp_max": round(regional_frp_max, 2),
        "local_hotspots_100km": round(local_hotspots, 0),
        "local_frp_max_100km": round(local_frp_max, 2),
        "interpretation": interpretation,
    }


def explanation_text(row: pd.Series, forecast: dict[str, Any], top_features: list[dict[str, Any]]) -> str:
    current_api = float(row.get("API", 0) or 0)
    roll3 = float(row.get("API_roll3h", current_api) or current_api)
    rain = float(row.get("RAIN_FORECAST_SLOTS", 0) or 0)
    firms = firms_evidence_payload(row)

    direction = "stable"
    if roll3 > current_api + 3:
        direction = "recently easing"
    elif roll3 + 3 < current_api:
        direction = "recently rising"

    reasons = [f"the recent API pattern is {direction}"]
    if rain <= 0:
        reasons.append("rain signal is low, so washout is unlikely")
    else:
        reasons.append("rain signal is present, which may help reduce particles")
    if firms["strength"] == "nearby":
        reasons.append(
            f"NASA FIRMS shows {firms['local_hotspots_100km']:.0f} nearby hotspot detections "
            f"within 100 km, with max FRP {firms['local_frp_max_100km']:.2f} MW"
        )
    elif firms["strength"] == "regional":
        reasons.append(
            f"NASA FIRMS shows {firms['regional_hotspots']:.0f} regional hotspot detections, "
            "but none within 100 km of this station"
        )
    else:
        reasons.append("NASA FIRMS does not show a fire hotspot signal for this station hour")

    top = ", ".join(str(item.get("feature")) for item in top_features[:3] if item.get("feature"))
    return (
        f"{row.get('STATION_LOCATION')} is currently {api_band(current_api)} "
        f"with API {current_api:.0f}. The highest forecast in the next 24 hours is "
        f"{forecast['max_forecast_api']:.1f}. The main explanation is that "
        f"{'; '.join(reasons)}. Model explanation features include: {top}."
    )


@app.get("/explain/{station_id}")
def get_explain(station_id: str) -> dict[str, Any]:
    rows = latest_feature_rows()
    match = rows[rows["STATION_ID"].astype(str) == str(station_id)]
    if match.empty:
        raise HTTPException(status_code=404, detail=f"Station not found or not explanation-ready: {station_id}")
    row = match.iloc[0]
    cache_key = explanation_cache_key(row)
    if cache_key in EXPLANATION_CACHE:
        return EXPLANATION_CACHE[cache_key]

    prediction = cached_prediction(row)
    forecast = forecast_payload(row, prediction)
    top_features = feature_ranking(row)
    payload = {
        "station_id": str(row["STATION_ID"]),
        "station_location": clean_value(row.get("STATION_LOCATION")),
        "state_name": clean_value(row.get("STATE_NAME")),
        "source_hour_myt": clean_value(row.get("HOUR_MYT")),
        "explanation": explanation_text(row, forecast, top_features),
        "firms_evidence": firms_evidence_payload(row),
        "top_features": top_features,
        "forecast": forecast["forecast"],
    }
    if len(EXPLANATION_CACHE) >= 256:
        EXPLANATION_CACHE.clear()
    EXPLANATION_CACHE[cache_key] = payload
    return payload


@app.post("/refresh")
async def refresh_now() -> dict[str, Any]:
    payload = await run_pipeline_refresh()
    return {
        "ok": True,
        "status": payload["status"],
        "latest_rows": len(payload["latest"]),
    }
