from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
IN = ROOT / "data" / "processed" / "uac_metrics.csv"
REP = ROOT / "outputs" / "reports"
REP.mkdir(parents=True, exist_ok=True)

df = pd.read_csv(IN, parse_dates=["date"], index_col="date")


def kpis(d):
    reported = d[~d["was_missing"]]
    transferred = reported["transferred"].sum()
    discharged = reported["discharged"].sum()
    backlog_net = d.loc[d["backlog_flag"], "net_intake"].mean()
    return {
        "Total children under care (last day)": int(d["total_load"].iloc[-1]),
        "Average children under care": round(d["total_load"].mean(), 1),
        "Peak children under care": int(d["total_load"].max()),
        "Net intake pressure (avg per reported day)": round(reported["net_intake"].mean(), 2),
        "Care load volatility index (std of daily growth %)": round(d["growth_pct"].std(), 2),
        "Backlog accumulation rate (avg net intake per reported day in backlog)": 0.0 if pd.isna(backlog_net) else round(backlog_net, 2),
        "Days in sustained backlog (%)": round(100 * d["backlog_flag"].mean(), 1),
        "Discharge offset ratio (discharged / transferred)": round(discharged / transferred, 3),
    }


# ---- 1. Overall KPIs ----
overall = pd.Series(kpis(df))
overall.to_csv(REP / "kpis_overall.csv", header=["value"])
print("OVERALL KPIs")
print(overall.to_string())

# ---- 2. KPIs by year (early vs late comparison) ----
by_year = pd.DataFrame({str(y): kpis(g) for y, g in df.groupby(df.index.year)})
by_year.to_csv(REP / "kpis_by_year.csv")
print("\nKPIs BY YEAR")
print(by_year.to_string())

# ---- 3. Monthly table (flows are averages per reported day) ----
monthly = df.resample("ME").agg({
    "total_load": "mean",
    "cbp_custody": "mean",
    "hhs_care": "mean",
    "apprehended": "mean",
    "transferred": "mean",
    "discharged": "mean",
    "net_intake": "mean",
}).round(1)
monthly.to_csv(REP / "monthly_summary.csv")
print("\nMONTHLY SUMMARY (first 6 and last 6 months)")
print(pd.concat([monthly.head(6), monthly.tail(6)]).to_string())

# ---- 4. Months with the highest and lowest load ----
print("\nHighest-load months:")
print(monthly["total_load"].nlargest(3).to_string())
print("\nLowest-load months:")
print(monthly["total_load"].nsmallest(3).to_string())