"""
Clean charging_stations_india.csv before loading into MySQL:
  1. Reconcile the messy `state` field (typos, abbreviations, city names,
     non-India entries) against the trustworthy `query_state` (bounding box).
  2. Cap the unrealistic max_power_kw outlier.
  3. Save a final clean CSV ready for MySQL.

Usage:
    python clean_charging_stations.py
"""

import pandas as pd

INPUT_FILE = "charging_stations_india.csv"
OUTPUT_FILE = "charging_stations_india_clean.csv"

# Known typos, abbreviations, and city->state mappings found in the raw OCM data.
# Keys are lowercased+stripped for matching.
STATE_CLEAN_MAP = {
    # abbreviations
    "gj": "Gujarat", "ka": "Karnataka", "mh": "Maharashtra",
    "mp": "Madhya Pradesh", "rj": "Rajasthan",
    # typos / casing variants
    "karnatak": "Karnataka", "karnataka": "Karnataka",
    "keraka": "Kerala", "keral": "Kerala", "lerala": "Kerala", "kerala": "Kerala",
    "mahrashtra": "Maharashtra", "maharashtra": "Maharashtra",
    "uttarakhnad": "Uttarakhand", "uttarakhand": "Uttarakhand",
    "new dehi": "Delhi", "delhi": "Delhi", "burari": "Delhi",
    "tamilnadu": "Tamil Nadu", "tamil nadu": "Tamil Nadu", "tamil nad": "Tamil Nadu",
    "uttar pradesh": "Uttar Pradesh",
    "west bengal": "West Bengal",
    "rajasthan": "Rajasthan",
    "punjab": "Punjab",
    "telangana": "Telangana",
    "gujarat": "Gujarat",
    "haryana": "Haryana",
    # city -> state
    "bangalore east": "Karnataka", "bangalore urban": "Karnataka",
    "chennai": "Tamil Nadu", "villupuram": "Tamil Nadu",
}

# Values that are known to be outside India, or too vague to map -
# for these we always trust query_state (the bounding box) instead.
NON_INDIA_OR_VAGUE = {"india", "morang", "north central province", "nort central province"}


def clean_state(raw_state, query_state):
    if pd.isna(raw_state):
        return query_state

    key = str(raw_state).strip().lower()

    if key in NON_INDIA_OR_VAGUE:
        return query_state

    if key in STATE_CLEAN_MAP:
        return STATE_CLEAN_MAP[key]

    # Non-Latin script or anything unrecognized -> fall back to the bounding box result
    if not key.isascii():
        return query_state

    # Last resort: title-case it and hope it's already a valid clean name
    # (covers any correctly-spelled state we didn't explicitly list)
    return str(raw_state).strip().title()


def main():
    df = pd.read_csv(INPUT_FILE)
    print(f"Loaded {len(df)} rows")

    df["state_clean"] = df.apply(
        lambda row: clean_state(row["state"], row["query_state"]), axis=1
    )

    # Cap the power outlier - no public charger legitimately exceeds ~500 kW
    before_outliers = (df["max_power_kw"] > 500).sum()
    df.loc[df["max_power_kw"] > 500, "max_power_kw"] = None
    print(f"Nulled {before_outliers} unrealistic max_power_kw values (>500 kW)")

    print("\nFinal state_clean distribution:")
    print(df["state_clean"].value_counts())

    df.to_csv(OUTPUT_FILE, index=False)
    print(f"\nSaved cleaned file to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
