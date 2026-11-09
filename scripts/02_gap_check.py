from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
df = pd.read_csv(ROOT / "data" / "processed" / "uac_clean.csv", parse_dates=["date"], index_col="date")

m = df["was_missing"]
run_id = (m != m.shift()).cumsum()

rows = []
for _, g in df[m].groupby(run_id[m]):
    rows.append({"start": g.index.min().date(), "end": g.index.max().date(), "days": len(g)})
gaps = pd.DataFrame(rows).sort_values("days", ascending=False)

print("Number of separate gaps:", len(gaps))
print("\nLongest 15 gaps:")
print(gaps.head(15).to_string(index=False))
print("\nGap length summary:")
print(gaps["days"].describe())
print("\nMissing days by weekday:")
print(df[m].index.day_name().value_counts())
print("\nMissing days by year:")
print(df[m].index.year.value_counts().sort_index())