from pathlib import Path
import pandas as pd
import streamlit as st

st.set_page_config(page_title="UAC Care Load Analytics", layout="wide")
DATA = Path(__file__).resolve().parent.parent / "data" / "processed" / "uac_metrics.csv"

LABELS = {
    "total_load": "Total system load",
    "cbp_custody": "Children in CBP custody",
    "hhs_care": "Children in HHS care",
    "apprehended": "Apprehended into CBP custody",
    "transferred": "Transferred out of CBP",
    "discharged": "Discharged from HHS",
    "net_intake": "Net intake (transfers - discharges)",
    "hhs_change": "Observed change in HHS care",
}


@st.cache_data
def load():
    d = pd.read_csv(DATA, parse_dates=["date"], index_col="date")
    ok = (~d["was_missing"]) & (~d["was_missing"].shift(1, fill_value=True))
    d["hhs_change"] = d["hhs_care"].diff().where(ok)
    return d


def kpis(d):
    reported = d[~d["was_missing"]]
    transferred = reported["transferred"].sum()
    discharged = reported["discharged"].sum()
    backlog_net = d.loc[d["backlog_flag"], "net_intake"].mean()
    return {
        "Total children under care (last day)": int(d["total_load"].iloc[-1]),
        "Average children under care": round(d["total_load"].mean(), 1),
        "Peak children under care": int(d["total_load"].max()),
        "Net intake pressure (avg/reported day)": round(reported["net_intake"].mean(), 2),
        "Care load volatility index (%)": round(d["growth_pct"].std(), 2),
        "Backlog accumulation rate (avg/day)": 0.0 if pd.isna(backlog_net) else round(backlog_net, 2),
        "Days in sustained backlog (%)": round(100 * d["backlog_flag"].mean(), 1),
        "Discharge offset ratio": round(discharged / transferred, 3),
    }


if not DATA.exists():
    st.error("Run scripts 01 to 04 first to create data/processed/uac_metrics.csv")
    st.stop()

df_all = load()

# ---------------- Sidebar ----------------
st.sidebar.header("Filters")
min_d, max_d = df_all.index.min().date(), df_all.index.max().date()
picked = st.sidebar.date_input("Date range", (min_d, max_d), min_value=min_d, max_value=max_d)
if isinstance(picked, (tuple, list)) and len(picked) == 2:
    start, end = picked
else:
    start, end = min_d, max_d

gran = st.sidebar.radio("Time granularity", ["Daily", "Weekly", "Monthly"], horizontal=True)
rule = {"Daily": "D", "Weekly": "W", "Monthly": "ME"}[gran]

options = list(LABELS.keys())
chosen = st.sidebar.multiselect(
    "Metrics to plot", options,
    default=["total_load", "cbp_custody", "hhs_care"],
    format_func=lambda c: LABELS[c],
)

df = df_all.loc[str(start):str(end)]
if df.empty:
    st.warning("No data in the selected range.")
    st.stop()


def view(cols):
    """Stocks and flows are both averaged, so flows are 'per reported day'."""
    v = df[cols]
    if rule != "D":
        v = v.resample(rule).mean()
    return v.rename(columns=LABELS)


# ---------------- Header and KPI cards ----------------
st.title("System Capacity & Care Load Analytics - Unaccompanied Children")
st.caption(f"{start} to {end}  |  {len(df)} days  |  flows are averages per reported day")

items = list(kpis(df).items())
for row in (items[:4], items[4:]):
    cols = st.columns(4)
    for col, (name, val) in zip(cols, row):
        col.metric(name, f"{val:,}" if isinstance(val, int) else f"{val:,.2f}")

# ---------------- Tabs ----------------
t1, t2, t3, t4 = st.tabs(["System Load Overview", "CBP vs HHS", "Net Intake & Backlog", "Data Quality & Strain"])

with t1:
    st.subheader(f"{gran} trend of selected metrics")
    if chosen:
        st.line_chart(view(chosen))
    else:
        st.info("Select at least one metric in the sidebar.")
    st.subheader("Total load with 7-day and 14-day averages")
    st.line_chart(df[["total_load", "total_load_ma7", "total_load_ma14"]].rename(
        columns={"total_load": "Daily", "total_load_ma7": "7-day avg", "total_load_ma14": "14-day avg"}))
    st.subheader("Care load volatility (7-day std / mean)")
    st.line_chart(df[["load_volatility_7"]])

with t2:
    st.subheader("CBP custody")
    st.line_chart(view(["cbp_custody"]))
    st.subheader("HHS care")
    st.line_chart(view(["hhs_care"]))
    share = (df["hhs_care"] / df["total_load"] * 100).rename("HHS share of total load (%)")
    st.subheader("HHS share of total load")
    st.line_chart(share)

with t3:
    st.subheader(f"Net intake ({gran.lower()}, per reported day)")
    st.bar_chart(view(["net_intake"]))
    st.subheader("Transfers into HHS vs discharges")
    st.line_chart(view(["transferred", "discharged"]))
    st.subheader("Observed change in HHS care (supplementary)")
    st.line_chart(view(["hhs_change"]))
    st.caption("Net intake covers the CBP-to-HHS pipeline only. The observed change in HHS care "
               "is higher on average, which suggests other inflow into HHS care that this dataset does not show.")
    st.subheader("Cumulative net intake (lower bound)")
    st.line_chart(df[["cum_net_intake"]])

with t4:
    flag = df["strain_flag"]
    run = (flag != flag.shift()).cumsum()
    rows = []
    for _, g in df[flag].groupby(run[flag]):
        if len(g) >= 7:
            rows.append({"start": g.index.min().date(), "end": g.index.max().date(),
                         "days": len(g), "peak_total_load": int(g["total_load"].max())})
    st.subheader("Prolonged strain windows (7-day avg load above the 75th percentile, 7+ days)")
    st.dataframe(pd.DataFrame(rows) if rows else pd.DataFrame({"info": ["No strain windows in this range"]}))

    st.subheader("Data quality in this range")
    c1, c2, c3 = st.columns(3)
    c1.metric("Unreported days", int(df["was_missing"].sum()))
    c2.metric("Days with transfers > CBP custody", int((df["transferred"] > df["cbp_custody"]).sum()))
    c3.metric("Days with discharges > HHS care", int((df["discharged"] > df["hhs_care"]).sum()))

    st.download_button("Download filtered data (CSV)", df.to_csv().encode(), "uac_filtered.csv", "text/csv")