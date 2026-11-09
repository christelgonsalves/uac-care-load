# System Capacity & Care Load Analytics for Unaccompanied Children

Healthcare capacity analytics for the HHS Unaccompanied Alien Children program (Unified Mentor internship project).

## What it does
- Cleans daily CBP/HHS data (Jan 2023 - Dec 2025) and flags reporting gaps and anomalies
- Computes total system load, net intake, backlog and strain indicators, and 5 KPIs
- Interactive Streamlit dashboard with date range, metric and granularity filters

## Run it
pip install -r requirements.txt
python scripts/01_load_and_clean.py
python scripts/03_metrics.py
python -m streamlit run app/dashboard.py

## Folders
- data/ raw dataset and processed files
- scripts/ analysis scripts 01-05
- app/ Streamlit dashboard
- outputs/ figures and report tables
- docs/ research paper and executive summary

## Live dashboard
(paste your Streamlit link here after deployment)