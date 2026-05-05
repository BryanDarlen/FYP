import os
import requests
import pandas as pd
import matplotlib.pyplot as plt

OUTPUT_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "outputs")
)
os.makedirs(OUTPUT_DIR, exist_ok=True)

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


# =========================
# 1) Fetch JSON
# =========================
URL = "https://eqms.doe.gov.my/api3/publicmapproxy/PUBLIC_DISPLAY/CAQM_MCAQM_Current_Reading/MapServer/0/query?f=json&outFields=*&returnGeometry=false&spatialRel=esriSpatialRelIntersects&where=1%3D1%20"
raw = requests.get(URL, timeout=60)
raw.raise_for_status()
raw_json = raw.json()

# =========================
# 2) Preprocess
# =========================
df = preprocess_apims(raw_json)

print("=== APIMS Cleaned Data ===")
print("Rows:", df.shape[0], "Cols:", df.shape[1])
print(df.head(5))

# =========================
# 3) Terminal Output (like your screenshot)
# =========================

# A) df.describe
print("\n=== [DESCRIBE] ===")
describe_out = df.describe(include="all")
print(describe_out)

# B) df.nunique
print("\n=== [UNIQUE VALUE COUNT] ===")
nunique_out = df.nunique(dropna=False).sort_values(ascending=False)
print(nunique_out)

# =========================
# 4) Save into 1 Excel file (same outputs)
# =========================
describe_df = describe_out.T
unique_counts_df = nunique_out.to_frame(name="UNIQUE_VALUE_COUNT")

out_path = os.path.join(OUTPUT_DIR, "apims_data_understanding.xlsx")
with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
    df.to_excel(writer, sheet_name="cleaned_data", index=False)
    describe_df.to_excel(writer, sheet_name="describe", index=True)
    unique_counts_df.to_excel(writer, sheet_name="unique_value_count", index=True)

print("\nSaved:", out_path)

# =========================
# 5) Visualization (2 charts only) - aligned with Section 4.3.2
# =========================
import numpy as np
import matplotlib.pyplot as plt

# 5.1 Histogram (API distribution) - like "Histogram of ... Distribution"
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

# 5.2 Correlation Heatmap (numeric relationships) - like "Heatmap of Correlation ..."
num_cols = [c for c in ["API", "API_PM10", "LONGITUDE", "LATITUDE"] if c in df.columns]
if len(num_cols) >= 2:
    corr = df[num_cols].corr(numeric_only=True)

    plt.figure()
    plt.imshow(corr.values, aspect="auto")
    plt.title("Correlation Heatmap (Numeric Features)")
    plt.xticks(range(len(num_cols)), num_cols, rotation=45, ha="right")
    plt.yticks(range(len(num_cols)), num_cols)

    # write correlation values on cells (optional but helpful for report)
    for i in range(len(num_cols)):
        for j in range(len(num_cols)):
            val = corr.values[i, j]
            if not np.isnan(val):
                plt.text(j, i, f"{val:.2f}", ha="center", va="center")

    plt.tight_layout()
    plt.show()
else:
    print("[SKIP] Heatmap: Need at least 2 numeric columns among API/API_PM10/LONGITUDE/LATITUDE")