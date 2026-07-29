# ⚡ EV Charging Infrastructure Gap Analysis — India

An end-to-end data analytics model identifying priority Indian states for electric vehicle (EV) charging infrastructure investment, built using MySQL, Python, and Plotly.

🔗 **[View Live Interactive Dashboard](https://sachinrao2005.github.io/ev-charging-infra-gap-analysis/dashboard.html)**

---

## 📌 Executive Summary

India's EV adoption is expanding rapidly, but public charging infrastructure deployment remains uneven[cite: 2]. 
This project quantifies the state-level imbalance between EV adoption density and charging access, delivering a data-driven investment ranking to optimize capital deployment[cite: 1, 2].

### 🏆 Top 5 Priority Investment States

| Priority Rank | State | EVs Registered (2024) | Stations / 1,000 EVs | YoY Growth (2022→2023) | Priority Score |
| :---: | :--- | :---: | :---: | :---: | :---: |
| **1** | **Uttar Pradesh** | 133,924 | 17.29 | 70.9% | **0.819** |
| **2** | **Chandigarh** | 2,476 | 5.25 | 135.6% | **0.701** |
| **3** | **Bihar** | 41,680 | 12.43 | 58.2% | **0.622** |
| **4** | **Rajasthan** | 78,204 | 19.37 | 31.0% | **0.617** |
| **5** | **Assam** | 25,879 | 13.33 | 41.7% | **0.554** |

> **Key Takeaway:** **Uttar Pradesh** represents India's largest single EV market (>133k registrations) and continues to grow at >70% YoY, yet maintains a low ratio of 17.29 stations per 1,000 EVs[cite: 1, 2]. It stands out as the single highest-priority market for immediate infrastructure expansion[cite: 1, 2].

---

## 🛠️ Data Quality & Analytics Engineering Wins

Raw public datasets contained major structural flaws that required rigorous data validation and cleaning[cite: 1, 2]:

1. **Crowdsourced Bias Resolution (OpenChargeMap):**[cite: 1, 2]
   * *Issue:* OpenChargeMap (OCM) captured only **~7% of India's real charging stations**, with severe regional bias toward Southern states (up to 64% coverage in Kerala vs. 0% in others)[cite: 1].
   * *Fix:* Used official Lok Sabha / Ministry of Heavy Industries parliamentary data as the primary ground truth for gap calculations, reserving OCM strictly for supplementary geospatial mapping[cite: 1, 2].

2. **Distribution-Based Outlier Detection (Vahan Scraping Errors):**[cite: 1]
   * *Issue:* Corrupted source rows caused isolated local RTO offices to report >200,000 monthly registrations, artificially inflating Rajasthan's 2024 total by **~10x** (falsely placing it as the #1 state)[cite: 1].
   * *Fix:* Analyzed the monthly registration distribution percentile[cite: 1]. Applied a strict **10,000 monthly threshold** (based on the 99.5th percentile jumping unnaturally from ~8,559 to over 83,103) to filter corrupted entries cleanly[cite: 1].

3. **Partial-Year Growth Adjustment:**[cite: 1, 2]
   * *Issue:* 2024 data covered only 5 months (Jan–May), causing naive YoY SQL queries to reflect artificial negative growth (-30% to -80%) across all regions[cite: 1].
   * *Fix:* Restructured SQL window functions (`LAG()`) to compute growth rates strictly across complete calendar years (2022 $\rightarrow$ 2023)[cite: 1, 2].

4. **Scope Filtering:**[cite: 1]
   * Excluded non-plug-in *Strong Hybrid EVs* to evaluate public grid-charging infrastructure demand accurately[cite: 1].

---

## 📐 Scoring Methodology

The composite **Priority Score** (0 to 1 scale) synthesizes three min-max normalized metrics[cite: 1, 2]:

Priority Score = 0.5 × Gap Score norm + 0.3 × Scale Score norm + 0.2 × Growth Score norm
​[cite: 1, 2]

Where:
* **Infrastructure Gap (50%):** Inverted ratio of official charging stations per 1,000 registered plug-in EVs[cite: 1, 2].
* **Market Scale (30%):** Total EV registration volume to ensure investment targets impactful markets[cite: 1, 2].
* **Adoption Momentum (20%):** Full-year YoY adoption growth percentage[cite: 1, 2].

---

## 📂 Repository Structure

```text
├── sql/
│   └── ev_project_final.sql          # Full pipeline: Load, clean, aggregate, window calculations, & priority scoring
├── python/
│   ├── extract_openchargemap.py      # OCM API extraction via bounding boxes
│   ├── clean_charging_stations.py    # Geospatial address cleaning & boundary overlap resolution
│   └── clean_vahan_registrations.py  # Vahan anomaly detection & outlier filtering
├── dashboard/
│   └── dashboard.html                # Standalone interactive Plotly HTML dashboard
└── report/
    └── ev_project_onepager.docx      # Project executive summary brief
```[cite: 1]

---

## ⚙️ Local Execution Setup

1. **Database Setup:** Run `sql/ev_project_final.sql` in MySQL 8.0+ to construct tables, data-cleansing views, and analytical models[cite: 1].
2. **Python Environment:** Install dependencies:
   ```bash
   pip install pandas plotly requests
