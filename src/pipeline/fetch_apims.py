import os
import argparse
import time
import requests
import pandas as pd
import matplotlib.pyplot as plt
from typing import Optional

OUTPUT_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "outputs")
)
os.makedirs(OUTPUT_DIR, exist_ok=True)

URL = "https://eqms.doe.gov.my/api3/publicmapproxy/PUBLIC_DISPLAY/CAQM_MCAQM_Current_Reading/MapServer/0/query?f=json&outFields=*&returnGeometry=false&spatialRel=esriSpatialRelIntersects&where=1%3D1%20"
HOURLY_URL = "https://eqms.doe.gov.my/api3/publicportalapims/apitablehourly"
DEFAULT_STATE_IDS = tuple(range(1, 17))
PROJECT_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
)
DEFAULT_HISTORY_PREVIEW_PATH = os.path.join(
    PROJECT_ROOT, "data", "processed", "apims_history_preview.csv"
)
MERGED_TIMESERIES_COLUMNS = [
    "STATION_ID", "STATION_LOCATION", "STATE_NAME", "LATITUDE", "LONGITUDE",
    "API", "CLASS", "HOUR_MYT", "TEMPERATURE_C", "RAIN_FORECAST_SLOTS",
    "HOTSPOT_COUNT", "FRP_MW_MEAN", "FRP_MW_MAX", "HIGH_CONF_COUNT",
    "HOTSPOT_COUNT_100KM", "FRP_MW_MEAN_100KM", "FRP_MW_MAX_100KM",
    "HIGH_CONF_COUNT_100KM", "DATA_FLAG",
]


def preprocess_apims(raw_json: dict) -> pd.DataFrame:
    #extract the attributes from each feature
    features = raw_json.get("features", [])
    rows = [f.get("attributes", {}) for f in features]
    df = pd.DataFrame(rows)

    #keep only the main fields in this stage
    keep_cols = [
        "STATION_ID", "DATETIME", "API", "API_PM10", "PARAM_SELECTED", "CLASS",
        "STATION_LOCATION", "LONGITUDE", "LATITUDE", "STATION_CATEGORY",
        "STATE_NAME", "REGION_NAME"
    ]
    df = df[[c for c in keep_cols if c in df.columns]]

    #convert the epoch miliseconds to datetime
    if "DATETIME" in df.columns:
        df["DATETIME"] = pd.to_datetime(df["DATETIME"], unit="ms", errors="coerce")

    #standardize the text fields
    text_cols = ["STATION_ID", "PARAM_SELECTED", "CLASS", "STATION_LOCATION",
                 "STATION_CATEGORY", "STATE_NAME", "REGION_NAME"]
    for c in text_cols:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()

    #handle duplicates, for now if 2 rows have same station id and datetime, remove it
    if "STATION_ID" in df.columns and "DATETIME" in df.columns:
        df = df.drop_duplicates(subset=["STATION_ID", "DATETIME"])

    #make sure these columns store numeric values
    for c in ["API", "API_PM10", "LONGITUDE", "LATITUDE"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    return df


def fetch_apims_data() -> dict:
    """Fetch APIMS current readings and return the raw JSON response."""
    raw = requests.get(URL, timeout=60)
    raw.raise_for_status()
    return raw.json()


def _normalise_hour_param(value: Optional[str]) -> str:
    """Return an APIMS-compatible hourly datetime string."""
    if value:
        return pd.to_datetime(value).strftime("%Y-%m-%d %H:%M")
    return pd.Timestamp.now().floor("h").strftime("%Y-%m-%d %H:%M")


def parse_state_ids(value: Optional[str]) -> list[int]:
    """
    Parse state ids from a comma/range string, e.g. "1-16" or "1,2,14".
    Defaults to all APIMS state ids currently used by the public hourly table.
    """
    if not value:
        return list(DEFAULT_STATE_IDS)

    state_ids: list[int] = []
    for part in value.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = part.split("-", 1)
            state_ids.extend(range(int(start), int(end) + 1))
        else:
            state_ids.append(int(part))

    return sorted(set(state_ids))


def fetch_apims_hourly_rows(
    end_datetime: Optional[str] = None,
    state_ids: Optional[list[int]] = None,
) -> list[dict]:
    """
    Fetch recent hourly APIMS table rows for the requested state ids.

    The public APIMS endpoint returns a recent rolling window ending at the
    requested datetime. This is useful for preview/backfill, but it is not a
    complete substitute for the scheduler because historical weather is not
    available from the current METMalaysia endpoint.
    """
    end_hour = _normalise_hour_param(end_datetime)
    selected_state_ids = state_ids or list(DEFAULT_STATE_IDS)
    rows: list[dict] = []

    for state_id in selected_state_ids:
        params = {"stateid": state_id, "datetime": end_hour}
        for attempt in range(1, 4):
            response = requests.get(HOURLY_URL, params=params, timeout=60)
            if response.status_code == 429 and attempt < 3:
                wait_seconds = 5 * attempt
                print(
                    f"[APIMS HISTORY] State {state_id}: rate limited; "
                    f"retrying in {wait_seconds}s..."
                )
                time.sleep(wait_seconds)
                continue

            if response.status_code == 429:
                print(f"[APIMS HISTORY] State {state_id}: skipped after repeated 429 responses.")
                break

            response.raise_for_status()
            payload = response.json()
            rows.extend(payload.get("api_table_hourly", []))
            time.sleep(0.5)
            break

    return rows


def preprocess_apims_hourly(rows: list[dict]) -> pd.DataFrame:
    """Clean APIMS hourly table rows from the public historical endpoint."""
    keep_cols = [
        "STATION_ID", "STATION_LOCATION", "STATE_ID", "DATETIME", "API",
        "PARAM_SYMBOL",
    ]
    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=keep_cols)

    df = df[[c for c in keep_cols if c in df.columns]].copy()
    if "DATETIME" in df.columns:
        df["DATETIME"] = pd.to_datetime(df["DATETIME"], errors="coerce")

    for c in ["STATION_ID", "STATION_LOCATION", "PARAM_SYMBOL"]:
        if c in df.columns:
            df[c] = df[c].astype(str).str.strip()

    for c in ["STATE_ID", "API"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    if {"STATION_ID", "DATETIME"}.issubset(df.columns):
        df = df.drop_duplicates(subset=["STATION_ID", "DATETIME"])

    return df.sort_values(["STATION_ID", "DATETIME"]).reset_index(drop=True)


def classify_api(api_value) -> str:
    """Return Malaysia API class label for a numeric API value."""
    if pd.isna(api_value):
        return ""
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


def build_apims_history_preview(
    end_datetime: Optional[str] = None,
    state_ids: Optional[list[int]] = None,
) -> pd.DataFrame:
    """
    Build an APIMS-only history preview in merged_timeseries.csv column shape.

    Weather and FIRMS columns are intentionally left missing and marked in
    DATA_FLAG. This keeps the preview honest: it is useful for inspecting
    recent API history, but should not be silently treated as a fully merged
    training dataset.
    """
    hourly_rows = fetch_apims_hourly_rows(end_datetime=end_datetime, state_ids=state_ids)
    history = preprocess_apims_hourly(hourly_rows)
    if history.empty:
        return pd.DataFrame(columns=MERGED_TIMESERIES_COLUMNS)

    metadata = preprocess_apims(fetch_apims_data())
    metadata_cols = [
        "STATION_ID", "STATION_LOCATION", "STATE_NAME", "LATITUDE", "LONGITUDE",
    ]
    metadata = metadata[[c for c in metadata_cols if c in metadata.columns]].drop_duplicates(
        subset=["STATION_ID"]
    )

    preview = history.merge(metadata, on="STATION_ID", how="left", suffixes=("", "_CURRENT"))
    if "STATION_LOCATION_CURRENT" in preview.columns:
        preview["STATION_LOCATION"] = preview["STATION_LOCATION"].replace("", pd.NA)
        preview["STATION_LOCATION"] = preview["STATION_LOCATION"].fillna(
            preview["STATION_LOCATION_CURRENT"]
        )

    preview["CLASS"] = preview["API"].apply(classify_api)
    preview["HOUR_MYT"] = pd.to_datetime(preview["DATETIME"], errors="coerce").dt.floor("h")
    preview["DATA_FLAG"] = "BACKFILLED_APIMS_ONLY;WEATHER_MISSING;FIRMS_MISSING;"

    missing_cols = [
        "TEMPERATURE_C", "RAIN_FORECAST_SLOTS", "HOTSPOT_COUNT",
        "FRP_MW_MEAN", "FRP_MW_MAX", "HIGH_CONF_COUNT",
        "HOTSPOT_COUNT_100KM", "FRP_MW_MEAN_100KM", "FRP_MW_MAX_100KM",
        "HIGH_CONF_COUNT_100KM",
    ]
    for col in missing_cols:
        preview[col] = pd.NA

    for col in MERGED_TIMESERIES_COLUMNS:
        if col not in preview.columns:
            preview[col] = pd.NA

    preview = preview[MERGED_TIMESERIES_COLUMNS]
    return preview.sort_values(["STATION_ID", "HOUR_MYT"]).reset_index(drop=True)


def save_apims_history_preview(df: pd.DataFrame, output_path: str) -> None:
    """Save APIMS history preview rows to CSV."""
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    df.to_csv(output_path, index=False)
    print(f"[APIMS HISTORY] Saved preview: {output_path}")
    print(f"[APIMS HISTORY] Rows: {len(df):,}")
    if not df.empty:
        print(f"[APIMS HISTORY] Stations: {df['STATION_ID'].nunique()}")
        print(f"[APIMS HISTORY] Hours: {df['HOUR_MYT'].nunique()}")
        print(f"[APIMS HISTORY] Range: {df['HOUR_MYT'].min()} -> {df['HOUR_MYT'].max()}")


def understand_apims(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    """Print APIMS data-understanding summaries and return them for export."""
    print("=== APIMS Cleaned Data ===")
    print("Rows:", df.shape[0], "Cols:", df.shape[1])
    print(df.head(5))

    print("\n=== [DESCRIBE] ===")
    describe_out = df.describe(include="all")
    print(describe_out)

    print("\n=== [UNIQUE VALUE COUNT] ===")
    nunique_out = df.nunique(dropna=False).sort_values(ascending=False)
    print(nunique_out)

    return describe_out, nunique_out


def save_understanding_workbook(
    df: pd.DataFrame,
    describe_out: pd.DataFrame,
    nunique_out: pd.Series,
) -> None:
    """Save cleaned APIMS data and data-understanding summaries to Excel."""
    describe_df = describe_out.T
    unique_counts_df = nunique_out.to_frame(name="UNIQUE_VALUE_COUNT")

    out_path = os.path.join(OUTPUT_DIR, "apims_data_understanding.xlsx")
    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="cleaned_data", index=False)
        describe_df.to_excel(writer, sheet_name="describe", index=True)
        unique_counts_df.to_excel(writer, sheet_name="unique_value_count", index=True)

    print("\nSaved:", out_path)


def visualize_apims(df: pd.DataFrame) -> None:
    """Generate APIMS histogram and correlation heatmap visualizations."""
    import numpy as np

    if "API" in df.columns:
        api = df["API"].dropna()
        if len(api) == 0:
            print("[SKIP] Histogram: API has no numeric values")
        else:
            plt.figure()
            plt.hist(api, bins=20)
            plt.title("Histogram of API Distribution")
            plt.xlabel("API")
            plt.ylabel("Count")
            plt.show()
    else:
        print("[SKIP] Histogram: 'API' column not found")

    num_cols = [c for c in ["API", "API_PM10", "LONGITUDE", "LATITUDE"] if c in df.columns]
    if len(num_cols) >= 2:
        corr = df[num_cols].corr(numeric_only=True)

        plt.figure()
        plt.imshow(corr.values, aspect="auto")
        plt.title("Correlation Heatmap (Numeric Features)")
        plt.xticks(range(len(num_cols)), num_cols, rotation=45, ha="right")
        plt.yticks(range(len(num_cols)), num_cols)

        for i in range(len(num_cols)):
            for j in range(len(num_cols)):
                val = corr.values[i, j]
                if not np.isnan(val):
                    plt.text(j, i, f"{val:.2f}", ha="center", va="center")

        plt.tight_layout()
        plt.show()
    else:
        print("[SKIP] Heatmap: Need at least 2 numeric columns among API/API_PM10/LONGITUDE/LATITUDE")


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch and inspect APIMS data.")
    parser.add_argument(
        "--history",
        action="store_true",
        help="Fetch recent APIMS hourly history and save an APIMS-only preview CSV.",
    )
    parser.add_argument(
        "--datetime",
        dest="end_datetime",
        default=None,
        help='Ending hour for APIMS history, for example "2026-05-07 15:00".',
    )
    parser.add_argument(
        "--state-ids",
        default="1-16",
        help='APIMS state ids to fetch, for example "1-16" or "1,2,14".',
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_HISTORY_PREVIEW_PATH,
        help="Output CSV path for --history mode.",
    )
    args = parser.parse_args()

    if args.history:
        df = build_apims_history_preview(
            end_datetime=args.end_datetime,
            state_ids=parse_state_ids(args.state_ids),
        )
        save_apims_history_preview(df, args.output)
        return

    raw_json = fetch_apims_data()
    df = preprocess_apims(raw_json)
    describe_out, nunique_out = understand_apims(df)
    save_understanding_workbook(df, describe_out, nunique_out)
    visualize_apims(df)


if __name__ == "__main__":
    main()
