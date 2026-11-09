from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed" / "uac_clean.csv"

# ---- 1. Load the file ----
files = [p for p in RAW_DIR.iterdir() if p.suffix.lower() in (".csv", ".xlsx", ".xls")]
path = files[0]
print("Reading:", path.name)
if path.suffix.lower() == ".csv":
    df = pd.read_csv(path)
else:
    df = pd.read_excel(path)

print("\nShape:", df.shape)
print("\nColumns:")
for c in df.columns:
    print("  -", repr(c))
print("\nFirst 5 rows:")
print(df.head())
print("\nData types:")
print(df.dtypes)

# ---- 2. Give the columns short names ----
rename = {}
for col in df.columns:
    c = str(col).lower()
    if "apprehended" in c:
        rename[col] = "apprehended"
    elif "transferred" in c:
        rename[col] = "transferred"
    elif "discharged" in c:
        rename[col] = "discharged"
    elif "in cbp custody" in c:
        rename[col] = "cbp_custody"
    elif "in hhs care" in c:
        rename[col] = "hhs_care"
    elif "date" in c:
        rename[col] = "date"
df = df.rename(columns=rename)
df = df[["date", "apprehended", "cbp_custody", "transferred", "hhs_care", "discharged"]]

# ---- 3. Fix types ----
df["date"] = pd.to_datetime(df["date"], errors="coerce")
print("\nBad dates:", df["date"].isna().sum())
df = df.dropna(subset=["date"])
for c in df.columns.drop("date"):
    df[c] = pd.to_numeric(df[c].astype(str).str.replace(r"[,*\s]", "", regex=True), errors="coerce")

# ---- 4. Duplicates, order, missing dates ----
print("Duplicate dates:", df["date"].duplicated().sum())
df = df.drop_duplicates(subset="date", keep="last").sort_values("date").set_index("date")
full = pd.date_range(df.index.min(), df.index.max(), freq="D")
print("Missing dates:", len(full) - len(df))
print("Date range:", df.index.min().date(), "to", df.index.max().date())

df = df.reindex(full)
df.index.name = "date"
print("\nNull values per column (after full daily index):")
print(df.isna().sum())

# Mark the days that were not reported
df["was_missing"] = df["cbp_custody"].isna() | df["hhs_care"].isna()

# Fill only the STOCK columns (headcounts that change gradually).
# FLOW columns (apprehended, transferred, discharged) stay empty on missing days.
num = ["apprehended", "cbp_custody", "transferred", "hhs_care", "discharged"]
stocks = ["cbp_custody", "hhs_care"]
df[stocks] = df[stocks].interpolate(limit_direction="both")

# ---- 5. Logical checks ----
print("\nTransfers > CBP custody:", (df["transferred"] > df["cbp_custody"]).sum(), "days")
print("Discharges > HHS care:", (df["discharged"] > df["hhs_care"]).sum(), "days")
print("Negative values:", (df[num] < 0).any(axis=1).sum(), "days")

# ---- 6. Save ----
df.to_csv(OUT)
print("\nSaved clean file:", OUT)
print(df[num].describe().round(1))