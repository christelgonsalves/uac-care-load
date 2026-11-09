from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

ROOT = Path(__file__).resolve().parent.parent
IN = ROOT / "data" / "processed" / "uac_metrics.csv"
FIG = ROOT / "outputs" / "figures"
FIG.mkdir(parents=True, exist_ok=True)
sns.set_theme(style="whitegrid")

df = pd.read_csv(IN, parse_dates=["date"], index_col="date")


def save(fig, name):
    fig.tight_layout()
    fig.savefig(FIG / name, dpi=150)
    plt.close(fig)
    print("saved", name)


# ---- 1. Total load with rolling averages and strain periods ----
top = df["total_load"].max() * 1.05
fig, ax = plt.subplots(figsize=(12, 5))
ax.plot(df.index, df["total_load"], alpha=0.35, label="Daily")
ax.plot(df.index, df["total_load_ma7"], label="7-day average")
ax.plot(df.index, df["total_load_ma14"], label="14-day average")
ax.fill_between(df.index, 0, top, where=df["strain_flag"].to_numpy(), color="red", alpha=0.10, label="Strain period")
ax.set(title="Total System Load (CBP + HHS)", ylabel="Children", ylim=(0, top))
ax.legend()
save(fig, "01_total_load.png")

# ---- 2. CBP vs HHS (two panels because the scales differ) ----
fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=True)
axes[0].plot(df.index, df["cbp_custody"], color="tab:orange")
axes[0].set(title="Children in CBP Custody", ylabel="Children")
axes[1].plot(df.index, df["hhs_care"], color="tab:blue")
axes[1].set(title="Children in HHS Care", ylabel="Children")
save(fig, "02_cbp_vs_hhs.png")

# ---- 3. Net intake and cumulative net intake ----
fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=True)
axes[0].plot(df.index, df["net_intake_ma7"], color="black")
axes[0].axhline(0, color="grey", lw=0.8)
axes[0].fill_between(df.index, 0, df["net_intake_ma7"].fillna(0), where=(df["net_intake_ma7"].fillna(0) > 0).to_numpy(), color="red", alpha=0.3, label="Inflow > outflow")
axes[0].fill_between(df.index, 0, df["net_intake_ma7"].fillna(0), where=(df["net_intake_ma7"].fillna(0) < 0).to_numpy(), color="green", alpha=0.3, label="Outflow > inflow")
axes[0].set(title="Net Intake (Transfers - Discharges), 7-day average per reported day", ylabel="Children / day")
axes[0].legend()
lo, hi = df["cum_net_intake"].min(), df["cum_net_intake"].max()
axes[1].plot(df.index, df["cum_net_intake"])
axes[1].fill_between(df.index, lo, hi, where=df["backlog_flag"].to_numpy(), color="red", alpha=0.10, label="Sustained backlog")
axes[1].set(title="Cumulative Net Intake (lower bound, unreported days counted as 0)", ylabel="Children")
axes[1].legend()
save(fig, "03_net_intake_backlog.png")

# ---- 4. Monthly average load ----
monthly = df["total_load"].resample("ME").mean()
fig, ax = plt.subplots(figsize=(12, 5))
ax.bar(monthly.index, monthly.values, width=20)
ax.set(title="Average Total Load by Month", ylabel="Children")
save(fig, "04_monthly_load.png")

# ---- 5. Year comparison ----
yr = df.groupby(df.index.year)
avg_load = yr["total_load"].mean()
backlog_pct = yr["backlog_flag"].mean() * 100
fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
axes[0].bar(avg_load.index.astype(str), avg_load.values, color="tab:blue")
axes[0].set(title="Average Total Load by Year", ylabel="Children")
axes[1].bar(backlog_pct.index.astype(str), backlog_pct.values, color="tab:red")
axes[1].set(title="Days in Sustained Backlog by Year", ylabel="% of days")
save(fig, "05_year_comparison.png")

# ---- 6. Check: does CBP net intake explain the change in HHS care? ----
ok = (~df["was_missing"]) & (~df["was_missing"].shift(1, fill_value=True))
d_hhs = df["hhs_care"].diff()
implied_inflow = d_hhs + df["discharged"]            # total children who must have entered HHS
other_inflow = implied_inflow - df["transferred"]    # entered HHS but NOT via CBP transfers
chk = pd.DataFrame({
    "d_hhs": d_hhs,
    "net_intake": df["net_intake"],
    "transferred": df["transferred"],
    "implied_inflow": implied_inflow,
    "other_inflow": other_inflow,
})[ok].dropna()

print("\nCHECK: change in HHS care vs CBP net intake")
print("Days compared:", len(chk))
print("Avg daily change in HHS care:", round(chk["d_hhs"].mean(), 1))
print("Avg daily CBP net intake:", round(chk["net_intake"].mean(), 1))
print("Avg daily CBP transfers into HHS:", round(chk["transferred"].mean(), 1))
print("Avg daily total inflow needed to explain HHS change:", round(chk["implied_inflow"].mean(), 1))
print("Avg daily inflow from other sources:", round(chk["other_inflow"].mean(), 1))
print("Correlation (change in HHS care vs net intake):", round(chk["d_hhs"].corr(chk["net_intake"]), 2))

fig, ax = plt.subplots(figsize=(6.5, 6))
ax.scatter(chk["net_intake"], chk["d_hhs"], s=12, alpha=0.5)
ax.axhline(0, color="grey", lw=0.8)
ax.axvline(0, color="grey", lw=0.8)
ax.set(title="Net Intake vs Daily Change in HHS Care", xlabel="Net intake (transfers - discharges)", ylabel="Change in HHS care")
save(fig, "06_net_intake_vs_hhs_change.png")

print("\nAll charts saved in:", FIG)