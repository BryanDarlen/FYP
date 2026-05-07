"""
End-to-end smoke test for src/models/train.py — Phase 4 training pipeline.

Generates a synthetic features.csv (20 stations x 504 hours, realistic shape),
runs train.py via subprocess, and verifies all 5 expected artefacts are
produced and structurally valid.

Run directly:
    python tests/test_train.py

The test backs up any real artefacts in src/models/ + data/processed/features.csv
before writing synthetic versions, restores them on exit, and removes synthetic
artefacts that did not exist before. Safe to run repeatedly.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT  = Path(__file__).resolve().parents[1]
FEATURES_PATH = PROJECT_ROOT / "data" / "processed" / "features.csv"
MODELS_DIR    = PROJECT_ROOT / "src" / "models"


def main() -> int:
    backup_dir = PROJECT_ROOT / "data" / "processed" / "_test_backup"
    backup_dir.mkdir(parents=True, exist_ok=True)

    real_features_backup = None
    if FEATURES_PATH.exists():
        real_features_backup = backup_dir / "features.csv.real"
        shutil.copy2(FEATURES_PATH, real_features_backup)

    artefact_names = [
        "forecast_model.pkl",
        "feature_columns.json",
        "eval_report.json",
        "baseline_report.json",
        "shap_global_importance.json",
    ]
    real_artefact_backup = {}
    for f in artefact_names:
        src = MODELS_DIR / f
        if src.exists():
            dst = backup_dir / f
            shutil.copy2(src, dst)
            real_artefact_backup[f] = dst

    try:
        rng = np.random.RandomState(42)
        stations = [f"STN_{i:02d}" for i in range(20)]
        n_hours = 24 * 21                      # 3 weeks
        base = pd.Timestamp("2026-04-15 00:00:00")
        rows = []
        for s in stations:
            baseline = rng.uniform(40, 60)
            for h in range(n_hours):
                t = base + pd.Timedelta(hours=h)
                api = baseline + 10 * np.sin(2 * np.pi * h / 24) + rng.normal(0, 5)
                api = max(0, min(api, 300))
                rows.append({
                    "STATION_ID":           s,
                    "STATION_LOCATION":     s,
                    "STATE_NAME":           "Synthetic",
                    "LATITUDE":             3.0 + rng.uniform(-0.5, 0.5),
                    "LONGITUDE":            101.0 + rng.uniform(-0.5, 0.5),
                    "API":                  api,
                    "CLASS":                "Moderate",
                    "HOUR_MYT":             t,
                    "TEMPERATURE_C":        28 + rng.normal(0, 2),
                    "RAIN_FORECAST_SLOTS":  rng.randint(0, 20),
                    "HOTSPOT_COUNT":        rng.randint(0, 5),
                    "FRP_MW_MEAN":          rng.uniform(0, 20),
                    "FRP_MW_MAX":           rng.uniform(0, 50),
                    "HIGH_CONF_COUNT":      rng.randint(0, 3),
                    "HOTSPOT_COUNT_100KM":  rng.randint(0, 3),
                    "FRP_MW_MEAN_100KM":    rng.uniform(0, 10),
                    "FRP_MW_MAX_100KM":     rng.uniform(0, 20),
                    "HIGH_CONF_COUNT_100KM": rng.randint(0, 2),
                    "DATA_FLAG":            "",
                    "DATA_MISSING":         0,
                    "API_lag1h":            api - rng.normal(0, 1),
                    "API_lag2h":            api - rng.normal(0, 2),
                    "API_lag3h":            api - rng.normal(0, 3),
                    "API_lag6h":            api - rng.normal(0, 4),
                    "API_lag12h":           api - rng.normal(0, 5),
                    "API_lag24h":           api + rng.normal(0, 5),
                    "API_roll3h":           api + rng.normal(0, 1),
                    "API_roll6h":           api + rng.normal(0, 1.5),
                    "API_roll12h":          api + rng.normal(0, 2),
                    "HOUR_OF_DAY":          t.hour,
                    "DAY_OF_WEEK":          t.dayofweek,
                    "IS_WEEKEND":           int(t.dayofweek >= 5),
                    "FIRE_AND_DRY":         rng.randint(0, 2),
                })
        synth_df = pd.DataFrame(rows)
        FEATURES_PATH.parent.mkdir(parents=True, exist_ok=True)
        synth_df.to_csv(FEATURES_PATH, index=False)

        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "src" / "models" / "train.py")],
            capture_output=True, text=True, cwd=str(PROJECT_ROOT),
        )
        if result.returncode != 0:
            print("train.py FAILED")
            print(result.stdout)
            print(result.stderr)
            return 1

        failures = []
        for f in artefact_names:
            if not (MODELS_DIR / f).exists():
                failures.append(f"missing artefact: {f}")

        if (MODELS_DIR / "feature_columns.json").exists():
            cols = json.loads((MODELS_DIR / "feature_columns.json").read_text())
            if cols.get("horizons") != [1, 3, 6, 12, 24]:
                failures.append(f"horizons mismatch: {cols.get('horizons')}")

        if (MODELS_DIR / "eval_report.json").exists():
            ev = json.loads((MODELS_DIR / "eval_report.json").read_text())
            for h in ["t+1h", "t+3h", "t+6h", "t+12h", "t+24h"]:
                if h not in ev:
                    failures.append(f"eval_report.json missing {h}")
                elif "rmse" not in ev[h] or "mae" not in ev[h]:
                    failures.append(f"eval_report.json {h} missing rmse/mae")

        if (MODELS_DIR / "shap_global_importance.json").exists():
            sh = json.loads((MODELS_DIR / "shap_global_importance.json").read_text())
            top3 = [r["feature"] for r in sh["ranking"][:3]]
            if "API_lag1h" not in top3:
                failures.append(f"API_lag1h should be in SHAP top 3 (got {top3})")

        if failures:
            print("FAIL:")
            for f in failures:
                print(f"  - {f}")
            return 1

        print(f"train: PASS (5/5 artefacts produced and structurally valid)")
        return 0

    finally:
        if real_features_backup and real_features_backup.exists():
            shutil.copy2(real_features_backup, FEATURES_PATH)
        else:
            FEATURES_PATH.unlink(missing_ok=True)
        for f, backup in real_artefact_backup.items():
            shutil.copy2(backup, MODELS_DIR / f)
        for f in artefact_names:
            if f not in real_artefact_backup:
                (MODELS_DIR / f).unlink(missing_ok=True)
        shutil.rmtree(backup_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
