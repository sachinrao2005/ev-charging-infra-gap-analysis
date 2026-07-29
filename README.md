# EV Charging Infrastructure Gap Analysis — India

A data analysis project identifying which Indian states most urgently need investment in EV charging infrastructure, built using SQL (MySQL) and Python.

## Problem

India's EV adoption is growing fast, but charging infrastructure investment hasn't kept pace evenly across states. This project quantifies exactly where the gap between EV adoption and charging access is widest, and ranks states by investment priority.

## Data Sources

- **[Vahan Dashboard](https://vahan.parivahan.gov.in/vahan4dashboard/)** (Ministry of Road Transport) — EV registrations by state, 2019–2024
- **[OpenChargeMap](https://openchargemap.org/)** — crowd-sourced charging station locations (used for map visuals)
- **Ministry of Heavy Industries / PIB** — official state-wise charging station counts (used as the primary ground-truth source)

## Key Findings

- **OpenChargeMap significantly undercounts real infrastructure**: cross-checking against official government data showed OCM captures only ~7% of India's actual charging stations, with strong regional bias toward South India.
- **Found and corrected corrupted source data**: a small number of rows in the Vahan dataset had implausible values (a single local office reporting 200,000+ EV registrations in one month), which had inflated one state's EV count by ~10x. Identified using distribution-based outlier detection and removed before analysis.
- **Corrected a partial-year data bug**: 2024 registration data only covered 5 months, which had made every state falsely appear to be declining year-over-year. Fixed by comparing full calendar years instead.

## Method

A weighted priority score combining three normalized signals:
- **Infrastructure gap (50%)** — charging stations per 1,000 registered EVs
- **Market scale (30%)** — total EV registrations
- **Adoption momentum (20%)** — year-over-year EV growth rate

## Result — Top 5 Priority States

| State | EVs Registered | Stations/1000 EV | YoY Growth | Priority Score |
|---|---|---|---|---|
| Uttar Pradesh | 133,924 | 17.29 | 70.9% | 0.819 |
| Chandigarh | 2,476 | 5.25 | 135.6% | 0.701 |
| Bihar | 41,680 | 12.43 | 58.2% | 0.622 |
| Rajasthan | 78,204 | 19.37 | 31.0% | 0.617 |
| Assam | 25,879 | 13.33 | 41.7% | 0.554 |

**Uttar Pradesh** is India's largest EV market by registrations, growing over 70% year-over-year, yet has one of the weaker charging-infrastructure ratios among major states — making it the highest-priority target for new investment.

## Repository Structure

```
├── sql/
│   └── ev_project_final.sql          # Full pipeline: load, clean, aggregate, analyze
├── python/
│   ├── extract_openchargemap.py      # OCM API data extraction
│   ├── clean_charging_stations.py    # OCM state-name cleaning + outlier handling
│   └── clean_vahan_registrations.py  # Removes corrupted Vahan rows
├── dashboard/
│   └── dashboard.html                # Interactive Plotly dashboard (map, rankings, trends)
└── report/
    └── ev_project_onepager.docx      # One-page project summary
```

## Tools Used

MySQL · Python (pandas, requests) · Plotly · SQL window functions

## Author

Sachin Rao — B.E. Electrical & Electronics Engineering, UIET, Panjab University
