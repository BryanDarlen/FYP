"""
Smoke tests for the Phase 5 FastAPI backend.

Run directly:
    python tests/test_api.py
"""
import os
import sys
from pathlib import Path

from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
os.environ["AIRQUALITY_DISABLE_AUTO_REFRESH"] = "1"

from src.api.main import app
import src.api.main as api_main


def main() -> int:
    failures = []

    with TestClient(app) as client:
        root = client.get("/")
        if root.status_code != 200:
            failures.append(f"/ returned {root.status_code}")
        elif "text/html" not in root.headers.get("content-type", ""):
            failures.append("/ should return dashboard HTML")

        status = client.get("/status")
        if status.status_code != 200:
            failures.append(f"/status returned {status.status_code}")

        latest = client.get("/latest")
        if latest.status_code != 200:
            failures.append(f"/latest returned {latest.status_code}")
            station_id = None
        else:
            rows = latest.json().get("latest", [])
            if not rows:
                failures.append("/latest returned no rows")
                station_id = None
            else:
                station_id = rows[0]["STATION_ID"]

        alerts = client.get("/alerts")
        if alerts.status_code != 200:
            failures.append(f"/alerts returned {alerts.status_code}")
        elif not api_main.PREDICTION_CACHE:
            failures.append("/alerts should populate the station-hour prediction cache")

        if station_id:
            history = client.get(f"/history/{station_id}?hours=12")
            if history.status_code != 200:
                failures.append(f"/history/{station_id} returned {history.status_code}")
            elif history.json().get("count", 0) < 1:
                failures.append("/history should return station rows")

            forecast = client.get(f"/forecast/{station_id}")
            if forecast.status_code != 200:
                failures.append(f"/forecast/{station_id} returned {forecast.status_code}")
            else:
                payload = forecast.json()
                if len(payload.get("forecast", [])) != 5:
                    failures.append("/forecast should return 5 horizons")

            explain = client.get(f"/explain/{station_id}")
            if explain.status_code != 200:
                failures.append(f"/explain/{station_id} returned {explain.status_code}")
            elif not explain.json().get("explanation"):
                failures.append("/explain should return explanation text")
            else:
                firms = explain.json().get("firms_evidence", {})
                required = {"strength", "regional_hotspots", "local_hotspots_100km", "interpretation"}
                if not required.issubset(firms):
                    failures.append("/explain should return structured FIRMS evidence")
                cache_size = len(api_main.EXPLANATION_CACHE)
                repeat = client.get(f"/explain/{station_id}")
                if repeat.status_code != 200:
                    failures.append(f"repeat /explain/{station_id} returned {repeat.status_code}")
                elif len(api_main.EXPLANATION_CACHE) != cache_size:
                    failures.append("repeat /explain should reuse the station-hour explanation cache")

    if failures:
        print("api: FAIL")
        for failure in failures:
            print(f" - {failure}")
        return 1

    print("api: PASS (7/7 endpoints)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
