from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
IN = ROOT / "data" / "processed" / "uac_clean.csv"
OUT = ROOT / "data" / "processed" / "uac_metrics.csv"

df = pd.read_csv(IN, parse_dates=["date"], index_col="date")

# ---- 1. Core metrics from the brief ----
df["total_load"] = df["cbp_custody"] + df["hhs_care"]          # CBP custody + HHS care
df["net_intake"] = df["transferred"] - df["discharged"]        # empty on unreported days

# Day-over-day % change, only between two really reported days
growth = df["total_load"].pct_change() * 100
unreliable = df["was_missing"] | df["was_missing"].shift(fill_value=False)
df["growth_pct"] = growth.mask(unreliable)

# Cumulative net intake (unreported days count as 0, so this is a lower bound)
df["cum_net_intake"] = df["net_intake"].fillna(0).cumsum()

# ---- 2. Rolling averages and variability ----
df["total_load_ma7"] = df["total_load"].rolling(7).mean()
df["total_load_ma14"] = df["total_load"].rolling(14).mean()
df["net_intake_ma7"] = df["net_intake"].rolling(7, min_periods=3).mean()   # per reported day
df["load_volatility_7"] = df["total_load"].rolling(7).std() / df["total_load"].rolling(7).mean()

# ---- 3. Backlog: 7-day avg net intake positive for 7+ days in a row ----
pos = df["net_intake_ma7"] > 0
run_id = (pos != pos.shift()).cumsum()
run_len = pos.groupby(run_id).cumsum()
df["backlog_flag"] = pos & (run_len >= 7)

# ---- 4. Strain: 7-day avg load above the 75th percentile ----
threshold = df["total_load_ma7"].quantile(0.75)
df["strain_flag"] = df["total_load_ma7"] > threshold

# ---- 5. Save and print a quick summary ----
df.to_csv(OUT)
print("Saved:", OUT)
print("Rows:", len(df))
print("Strain threshold (75th pct of 7-day avg load):", round(threshold, 1))
print("Strain days:", int(df["strain_flag"].sum()))
print("Backlog days:", int(df["backlog_flag"].sum()))

print("\nTotal load summary:")
print(df["total_load"].describe().round(1))
print("\nNet intake summary (reported days only):")
print(df["net_intake"].describe().round(1))

print("\nPeak total load:", int(df["total_load"].max()), "on", df["total_load"].idxmax().date())
print("Lowest total load:", int(df["total_load"].min()), "on", df["total_load"].idxmin().date())

# Strain windows of 7+ days
flag = df["strain_flag"]
run = (flag != flag.shift()).cumsum()
print("\nStrain windows (7+ days):")
for _, g in df[flag].groupby(run[flag]):
    if len(g) >= 7:
        print(" ", g.index.min().date(), "to", g.index.max().date(), "-", len(g), "days, peak", int(g["total_load"].max()))