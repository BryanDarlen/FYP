"""
Phase 4 - Train the API forecasting model.

Single entry point that takes data/processed/features.csv and produces:

    src/models/forecast_model.pkl     - trained MultiOutputRegressor (RandomForest)
    src/models/feature_columns.json   - feature column order (for inference)
    src/models/eval_report.json       - per-horizon RMSE/MAE/threshold metrics
    src/models/baseline_report.json   - persistence + linear regression baselines

Run:
    python src/models/train.py

Behaviour:
  - Loads features.csv produced by feature_engineering.py.
  - Builds 5 forecast targets (t+1, t+3, t+6, t+12, t+24 hours) per station.
  - Drops rows whose targets contain NaN (the trailing rows of each station
    where the future is not yet known).
  - Time-based 80/20 chronological split. NEVER random shuffle.
  - Trains and evaluates 3 models: persistence baseline, linear regression
    baseline, and MultiOutputRegressor(RandomForestRegressor) main model.
  - Saves the main model and a feature-column manifest. Inference (Phase 5)
    loads both at FastAPI startup.

Design choices (locked per PLAN.md):
  - RandomForest over GradientBoosting: faster training, low tuning, clean
    SHAP integration. Try GradientBoosting only if RF underfits.
  - MultiOutputRegressor over per-horizon models: one fit() call covers all
    5 horizons, simpler inference path.
  - Threshold metrics report precision/recall on the *crossing* event at
    API=100 and API=200, since false negatives (missed alerts) are worse
    than false positives.
"""

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import shap
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.metrics import precision_score, recall_score, confusion_matrix
from sklearn.multioutput import MultiOutputRegressor


# ----- Paths -----------------------------------------------------------------

PROJECT_ROOT      = Path(__file__).resolve().parents[2]
FEATURES_PATH     = PROJECT_ROOT / "data" / "processed" / "features.csv"
MODELS_DIR        = PROJECT_ROOT / "src" / "models"
MODEL_PATH        = MODELS_DIR / "forecast_model.pkl"
FEATURE_COLS_PATH = MODELS_DIR / "feature_columns.json"
EVAL_REPORT_PATH  = MODELS_DIR / "eval_report.json"
BASELINE_PATH     = MODELS_DIR / "baseline_report.json"
SHAP_REPORT_PATH  = MODELS_DIR / "shap_global_importance.json"


# ----- Configuration ---------------------------------------------------------

FORECAST_HORIZONS = [1, 3, 6, 12, 24]                # hours
TRAIN_FRACTION    = 0.80                              # chronological split
ALERT_THRESHOLDS  = [100, 200]                        # API band crossings
RF_PARAMS = {
    "n_estimators": 200,
    "max_depth":     None,    # let trees grow; RF averages over the variance
    "min_samples_leaf": 5,    # mild regularisation
    "n_jobs":        -1,      # use all cores
    "random_state":  42,
}

# Columns we never feed the model (identifiers, raw timestamps, validation flags)
EXCLUDED_FEATURES = {
    "STATION_ID", "STATION_LOCATION", "STATE_NAME",
    "HOUR_MYT", "CLASS", "DATA_FLAG",
}


# ----- Step 1: target construction -------------------------------------------

def build_targets(df: pd.DataFrame, horizons: list[int]) -> pd.DataFrame:
    """
    Add target columns target_t1h, target_t3h, ... per station via shift(-N).
    Rows where any target is NaN (the trailing rows of each station) are
    DROPPED at the caller to avoid training on partial labels.
    """
    df = df.copy()
    grouped = df.groupby("STATION_ID")["API"]
    for h in horizons:
        df[f"target_t{h}h"] = grouped.shift(-h)
    return df


# ----- Step 2: time-based 80/20 split ----------------------------------------

def chronological_split(df: pd.DataFrame, train_frac: float):
    """
    Split by unique HOUR_MYT, NOT by row.  All stations share the same cutoff
    hour, so the train and test sets are temporally disjoint.
    """
    unique_hours = sorted(df["HOUR_MYT"].unique())
    n_train = int(len(unique_hours) * train_frac)
    cutoff = unique_hours[n_train - 1]

    train = df[df["HOUR_MYT"] <= cutoff].copy()
    test  = df[df["HOUR_MYT"] >  cutoff].copy()
    return train, test, cutoff


# ----- Step 3: baselines -----------------------------------------------------

def persistence_predict(X_features: pd.DataFrame, horizons: list[int]) -> np.ndarray:
    """
    Persistence baseline: predict next-hour API = current API.
    Same prediction is used for every horizon (worst at long horizons,
    surprisingly hard to beat at t+1h).
    """
    current_api = X_features["API"].to_numpy().reshape(-1, 1)
    return np.repeat(current_api, len(horizons), axis=1)


def linear_baseline_predict(X_train, y_train, X_test):
    """
    Per-horizon linear regression. Wraps in MultiOutputRegressor for symmetry
    with the main model API. Returns predictions only — the linear baseline
    model itself is not persisted because it is not used for inference.
    """
    lr = MultiOutputRegressor(LinearRegression())
    lr.fit(X_train, y_train)
    return lr.predict(X_test)


# ----- Step 4: evaluation ----------------------------------------------------

def evaluate(y_true: np.ndarray, y_pred: np.ndarray, horizons: list[int]) -> dict:
    """
    Per-horizon RMSE, MAE, and threshold metrics at API=100 / API=200.

    Threshold reporting follows PLAN.md: precision/recall on the CROSSING
    event (predicted >= threshold).  Missing a crossing is worse than a
    false alarm because alerts drive school closures and outdoor decisions.
    """
    report = {}
    for i, h in enumerate(horizons):
        y_t = y_true[:, i]
        y_p = y_pred[:, i]

        rmse = float(np.sqrt(mean_squared_error(y_t, y_p)))
        mae  = float(mean_absolute_error(y_t, y_p))
        h_report = {
            "rmse": round(rmse, 3),
            "mae":  round(mae, 3),
            "thresholds": {},
        }

        for thr in ALERT_THRESHOLDS:
            true_cross = (y_t >= thr).astype(int)
            pred_cross = (y_p >= thr).astype(int)
            tn, fp, fn, tp = confusion_matrix(true_cross, pred_cross, labels=[0, 1]).ravel()
            # zero_division=0 keeps precision/recall numeric (0.0) instead of NaN
            # when the test slice contains no positive crossings at this threshold.
            # The positive_cases field surfaces that situation so downstream readers
            # can tell "0.0 because no positives" from "0.0 because all wrong".
            h_report["thresholds"][f"api_ge_{thr}"] = {
                "precision":      round(precision_score(true_cross, pred_cross, zero_division=0), 3),
                "recall":         round(recall_score(true_cross, pred_cross, zero_division=0), 3),
                "true_positives":  int(tp),
                "false_positives": int(fp),
                "false_negatives": int(fn),
                "true_negatives":  int(tn),
                "positive_cases":  int(true_cross.sum()),
            }
        report[f"t+{h}h"] = h_report
    return report


# ----- Main ------------------------------------------------------------------

def main() -> None:
    if not FEATURES_PATH.exists():
        print(f"[TRAIN] features.csv not found at {FEATURES_PATH}")
        print("[TRAIN] Run feature engineering first:")
        print("[TRAIN]   python src/pipeline/feature_engineering.py")
        sys.exit(0)

    print(f"[TRAIN] Loading {FEATURES_PATH.name} ...")
    df = pd.read_csv(FEATURES_PATH, parse_dates=["HOUR_MYT"])
    print(f"[TRAIN]   Rows           : {len(df):,}")
    print(f"[TRAIN]   Stations       : {df['STATION_ID'].nunique()}")

    # 1. Build targets and drop rows with any NaN target (trailing rows per station)
    df = build_targets(df, FORECAST_HORIZONS)
    target_cols = [f"target_t{h}h" for h in FORECAST_HORIZONS]
    n_before = len(df)
    df = df.dropna(subset=target_cols).reset_index(drop=True)
    print(f"[TRAIN]   After targets  : {len(df):,}  (dropped {n_before - len(df):,} trailing rows)")

    if len(df) < 100:
        print(f"[TRAIN] Only {len(df)} rows after target construction. Need more")
        print("[TRAIN] data — keep the scheduler running and re-run this script.")
        sys.exit(0)

    # 2. Chronological 80/20 split
    train_df, test_df, cutoff = chronological_split(df, TRAIN_FRACTION)
    print(f"[TRAIN]   Cutoff hour    : {cutoff}")
    print(f"[TRAIN]   Train rows     : {len(train_df):,}")
    print(f"[TRAIN]   Test rows      : {len(test_df):,}")

    # 3. Identify feature columns (numeric, excluding identifiers and targets)
    feature_cols = sorted([
        c for c in df.columns
        if c not in EXCLUDED_FEATURES
        and not c.startswith("target_t")
        and pd.api.types.is_numeric_dtype(df[c])
    ])
    print(f"[TRAIN]   Features       : {len(feature_cols)}")

    X_train = train_df[feature_cols].to_numpy()
    y_train = train_df[target_cols].to_numpy()
    X_test  = test_df[feature_cols].to_numpy()
    y_test  = test_df[target_cols].to_numpy()

    # 4. Persistence baseline (predict t+N = current API for all N)
    print("[TRAIN] Evaluating persistence baseline ...")
    y_pred_persistence = persistence_predict(test_df, FORECAST_HORIZONS)
    persistence_report = evaluate(y_test, y_pred_persistence, FORECAST_HORIZONS)

    # 5. Linear regression baseline
    print("[TRAIN] Training linear regression baseline ...")
    y_pred_linear = linear_baseline_predict(X_train, y_train, X_test)
    linear_report = evaluate(y_test, y_pred_linear, FORECAST_HORIZONS)

    # 6. Main model — MultiOutputRegressor(RandomForestRegressor)
    print(f"[TRAIN] Training Random Forest ({RF_PARAMS['n_estimators']} trees) ...")
    rf = MultiOutputRegressor(RandomForestRegressor(**RF_PARAMS))
    rf.fit(X_train, y_train)
    y_pred_rf = rf.predict(X_test)
    rf_report = evaluate(y_test, y_pred_rf, FORECAST_HORIZONS)

    # 7. SHAP global feature importance — uses the t+1h horizon RF (the most
    # accurate horizon and the most directly actionable). Per-prediction SHAP
    # is computed at inference time (Phase 5) via the saved model.
    print("[TRAIN] Computing SHAP global importance (t+1h horizon) ...")
    rf_t1 = rf.estimators_[0]                            # RF for first horizon
    sample_size = min(500, len(X_test))                  # cap for speed; SHAP is O(n)
    sample_idx = np.random.RandomState(42).choice(len(X_test), sample_size, replace=False)
    explainer = shap.TreeExplainer(rf_t1)
    shap_values = explainer.shap_values(X_test[sample_idx])  # (sample_size, n_features)
    mean_abs = np.abs(shap_values).mean(axis=0)
    importance = sorted(
        zip(feature_cols, mean_abs.tolist()),
        key=lambda kv: kv[1],
        reverse=True,
    )
    shap_report = {
        "horizon":     "t+1h",
        "sample_size": sample_size,
        "ranking":     [{"feature": f, "mean_abs_shap": round(v, 4)} for f, v in importance],
    }

    # 8. Persist artefacts
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(rf, MODEL_PATH)
    FEATURE_COLS_PATH.write_text(json.dumps({
        "feature_columns": feature_cols,
        "target_columns":  target_cols,
        "horizons":        FORECAST_HORIZONS,
    }, indent=2))
    EVAL_REPORT_PATH.write_text(json.dumps(rf_report, indent=2))
    BASELINE_PATH.write_text(json.dumps({
        "persistence":       persistence_report,
        "linear_regression": linear_report,
    }, indent=2))
    SHAP_REPORT_PATH.write_text(json.dumps(shap_report, indent=2))

    # 9. Summary
    print()
    print("[TRAIN] Done. Artefacts:")
    print(f"[TRAIN]   {MODEL_PATH}")
    print(f"[TRAIN]   {FEATURE_COLS_PATH}")
    print(f"[TRAIN]   {EVAL_REPORT_PATH}")
    print(f"[TRAIN]   {BASELINE_PATH}")
    print(f"[TRAIN]   {SHAP_REPORT_PATH}")
    print()
    print("[TRAIN] Top 5 features (by mean |SHAP value|, t+1h horizon):")
    for entry in shap_report["ranking"][:5]:
        print(f"[TRAIN]   {entry['feature']:<25} {entry['mean_abs_shap']:.4f}")
    print()
    print("[TRAIN] RMSE per horizon  (Persistence | Linear | RandomForest):")
    for h in FORECAST_HORIZONS:
        p = persistence_report[f"t+{h}h"]["rmse"]
        l = linear_report[f"t+{h}h"]["rmse"]
        r = rf_report[f"t+{h}h"]["rmse"]
        winner = "RF" if r <= min(p, l) else ("Linear" if l < p else "Persistence")
        print(f"[TRAIN]   t+{h:>2}h  {p:>7.3f}  |  {l:>7.3f}  |  {r:>7.3f}    -> {winner}")
    print()
    print("[TRAIN] If RF does not beat both baselines on RMSE/MAE,")
    print("[TRAIN] more data / feature work is needed before relying on it.")


if __name__ == "__main__":
    main()
