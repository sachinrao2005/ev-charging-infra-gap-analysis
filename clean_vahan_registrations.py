"""
Clean vahan-vehicle-registrations-by-fuel-type.csv before loading into MySQL.

Problem found: a small number of rows (<1%) contain registration values in the
tens/hundreds of thousands for a SINGLE RTO office in a SINGLE month - e.g. a
"Vehicle Fitness Center" office reporting 200,000+ EV registrations in one month.
These are almost certainly a data pipeline/scraping error (e.g. a state or
national aggregate value mistakenly attributed to one local office row), and
they were dominating state-level totals (e.g. one such row accounted for 87%
of Rajasthan's entire 2024 EV count).

Fix: flag and remove rows above a realistic per-office-per-month threshold,
chosen from the data's own distribution (99.5th percentile ~8,559 vs 99.9th
percentile ~83,103 - a huge, unnatural jump that marks the boundary between
real and corrupted values).

Usage:
    python clean_vahan_registrations.py
"""

import pandas as pd

INPUT_FILE = "vahan-vehicle-registrations-by-fuel-type.csv"
OUTPUT_FILE = "vahan-vehicle-registrations-clean.csv"

# A single RTO office realistically does not register more than this many
# EVs in one calendar month, even in a busy metro. Chosen conservatively
# above the 99.5th percentile of the real data (~8,559).
MAX_PLAUSIBLE_MONTHLY_REGISTRATIONS = 10000


def main():
    df = pd.read_csv(INPUT_FILE)
    print(f"Loaded {len(df)} rows")

    is_ev = df["fuel_type"].isin(["Electric(Bov)", "Pure Ev", "Plug-In Hybrid Ev"])
    flagged = is_ev & (df["registrations"] > MAX_PLAUSIBLE_MONTHLY_REGISTRATIONS)

    print(f"Flagging {flagged.sum()} rows as implausible (EV rows > {MAX_PLAUSIBLE_MONTHLY_REGISTRATIONS} in one office-month)")
    print(f"These flagged rows account for {df.loc[flagged, 'registrations'].sum():,} registrations "
          f"out of {df.loc[is_ev, 'registrations'].sum():,} total EV registrations "
          f"({df.loc[flagged, 'registrations'].sum() / df.loc[is_ev, 'registrations'].sum() * 100:.1f}%)")

    print("\nTop offices/states affected:")
    print(df.loc[flagged, ["state_name", "office_name", "date", "registrations"]]
          .sort_values("registrations", ascending=False).head(10).to_string(index=False))

    df_clean = df[~flagged].copy()
    df_clean.to_csv(OUTPUT_FILE, index=False)
    print(f"\nSaved cleaned file with {len(df_clean)} rows to {OUTPUT_FILE}")

    # Quick sanity check: recompute state EV totals for 2024 after cleaning
    df_clean["date"] = pd.to_datetime(df_clean["date"])
    df_clean["year"] = df_clean["date"].dt.year
    df_clean["is_ev"] = df_clean["fuel_type"].isin(["Electric(Bov)", "Pure Ev", "Plug-In Hybrid Ev"])
    check = df_clean[df_clean["is_ev"] & (df_clean["year"] == 2024)].groupby("state_name")["registrations"].sum()
    print("\nTop 10 states by 2024 EV registrations AFTER cleaning:")
    print(check.sort_values(ascending=False).head(10))


if __name__ == "__main__":
    main()
