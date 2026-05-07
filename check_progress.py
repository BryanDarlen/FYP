"""
Quick read-only inspector for merged_timeseries.csv.

Run anytime — does not interfere with the scheduler writing to the file:
    python check_progress.py
"""
import pandas as pd
from pathlib import Path

CSV_PATH = Path(__file__).parent / "data" / "processed" / "merged_timeseries.csv"

if not CSV_PATH.exists():
    print(f"No data yet — {CSV_PATH} does not exist.")
    print("Start the scheduler first: python src/pipeline/scheduler.py")
    raise SystemExit(0)

df = pd.read_csv(CSV_PATH, parse_dates=["HOUR_MYT"])

print(f"Rows           : {len(df):,}")
print(f"Unique hours   : {df['HOUR_MYT'].nunique()}")
print(f"Unique stations: {df['STATION_ID'].nunique()}")
print(f"First hour     : {df['HOUR_MYT'].min()}")
print(f"Latest hour    : {df['HOUR_MYT'].max()}")
print(f"API range      : {df['API'].min():.0f} - {df['API'].max():.0f} (mean {df['API'].mean():.1f})")

# Validation flag breakdown
flags = df["DATA_FLAG"].fillna("").astype(str)
flagged = (flags != "").sum()
print(f"\nFlagged rows   : {flagged} of {len(df):,} ({100*flagged/max(len(df),1):.1f}%)")
if flagged:
    for tag in ["INVALID_API", "INVALID_TEMP", "INVALID_HOTSPOT", "FLATLINE", "SPIKE"]:
        n = flags.str.contains(tag).sum()
        if n:
            print(f"  {tag:<20} {n}")
