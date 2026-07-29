"""
Extract EV charging station data for India from the OpenChargeMap API.
Handles pagination, flattens nested JSON, and saves a clean CSV
ready to load into MySQL.

Usage:
    pip install requests pandas
    python extract_openchargemap.py
"""

import requests
import pandas as pd
import time

API_KEY = "YOUR_API_KEY_HERE"   # paste your free key from openchargemap.org
BASE_URL = "https://api.openchargemap.io/v3/poi/"
MAX_RESULTS_PER_QUERY = 1000    # OCM caps this; we rely on bounding boxes, not offset, for coverage
OUTPUT_FILE = "charging_stations_india.csv"

# OCM's `offset` parameter does not actually paginate (confirmed community issue -
# every request just returns the same newest N results). So instead we query
# state-by-state using a bounding box, which OCM DOES respect, and then dedupe
# by station_id across all the per-state results.
# Boxes are approximate (SW corner, NE corner) - generous enough to catch border stations;
# duplicates across neighboring states are removed later by station_id.
STATE_BOUNDING_BOXES = {
    "Andhra Pradesh":      (12.6, 76.7, 19.9, 84.8),
    "Arunachal Pradesh":   (26.6, 91.6, 29.5, 97.4),
    "Assam":               (24.1, 89.7, 28.2, 96.0),
    "Bihar":               (24.2, 83.3, 27.5, 88.2),
    "Chhattisgarh":        (17.7, 80.2, 24.1, 84.4),
    "Delhi":               (28.4, 76.8, 28.9, 77.4),
    "Goa":                 (14.9, 73.7, 15.8, 74.3),
    "Gujarat":             (20.1, 68.1, 24.7, 74.5),
    "Haryana":             (27.6, 74.4, 30.9, 77.6),
    "Himachal Pradesh":    (30.4, 75.6, 33.3, 79.0),
    "Jammu and Kashmir":   (32.2, 73.7, 37.1, 80.3),
    "Jharkhand":           (21.9, 83.3, 25.4, 87.9),
    "Karnataka":           (11.5, 74.0, 18.5, 78.6),
    "Kerala":              (8.2, 74.8, 12.8, 77.4),
    "Madhya Pradesh":      (21.0, 74.0, 26.9, 82.8),
    "Maharashtra":         (15.6, 72.6, 22.1, 80.9),
    "Manipur":             (23.8, 92.9, 25.7, 94.8),
    "Meghalaya":           (25.0, 89.8, 26.1, 92.8),
    "Mizoram":             (21.9, 92.2, 24.5, 93.5),
    "Nagaland":            (25.2, 93.3, 27.0, 95.2),
    "Odisha":              (17.8, 81.4, 22.6, 87.5),
    "Punjab":              (29.5, 73.9, 32.5, 76.9),
    "Rajasthan":           (23.0, 69.5, 30.2, 78.3),
    "Sikkim":              (27.0, 88.0, 28.1, 88.9),
    "Tamil Nadu":          (8.1, 76.2, 13.6, 80.4),
    "Tripura":             (22.9, 91.1, 24.5, 92.3),
    "Uttar Pradesh":       (23.8, 77.0, 30.4, 84.6),
    "Uttarakhand":         (28.7, 77.6, 31.5, 81.1),
    "West Bengal":         (21.5, 85.8, 27.2, 89.9),
    "Puducherry":          (10.7, 79.7, 12.0, 79.9),
    "Chandigarh":          (30.6, 76.7, 30.8, 76.9),
    "Telangana":           (15.8, 77.2, 19.9, 81.3),
}


def fetch_state(state_name: str, box: tuple) -> list:
    """Fetch all POI results within a state's bounding box."""
    lat1, lng1, lat2, lng2 = box
    params = {
        "output": "json",
        "boundingbox": f"({lat1},{lng1}),({lat2},{lng2})",
        "maxresults": MAX_RESULTS_PER_QUERY,
        "compact": "false",     # false = includes full nested detail (operator, connections, etc.)
        "verbose": "false",     # false = trims unnecessary metadata
        "key": API_KEY,
    }
    resp = requests.get(BASE_URL, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def flatten_poi(poi: dict) -> dict:
    """Flatten one POI record into a single flat row for CSV/SQL."""
    address = poi.get("AddressInfo") or {}
    operator = poi.get("OperatorInfo") or {}
    connections = poi.get("Connections") or []

    # A station can have multiple charging connectors (Type 2, CCS, CHAdeMO, etc.)
    # We take the max power output across connectors as a useful summary field,
    # and count how many connectors the station has.
    max_power_kw = max(
        [c.get("PowerKW") for c in connections if c.get("PowerKW")], default=None
    )

    return {
        "station_id": poi.get("ID"),
        "title": address.get("Title"),
        "address_line": address.get("AddressLine1"),
        "town": address.get("Town"),
        "state": address.get("StateOrProvince"),
        "postcode": address.get("Postcode"),
        "latitude": address.get("Latitude"),
        "longitude": address.get("Longitude"),
        "operator_name": operator.get("Title") if operator else None,
        "num_connections": len(connections),
        "max_power_kw": max_power_kw,
        "date_created": poi.get("DateCreated"),
        "is_operational": poi.get("StatusTypeID"),
    }


def main():
    all_rows = []

    for state_name, box in STATE_BOUNDING_BOXES.items():
        print(f"Fetching {state_name}...")
        try:
            results = fetch_state(state_name, box)
        except requests.exceptions.RequestException as e:
            print(f"  -> ERROR fetching {state_name}: {e}")
            continue

        print(f"  -> got {len(results)} results")
        for poi in results:
            row = flatten_poi(poi)
            row["query_state"] = state_name  # our own reliable state label
            all_rows.append(row)

        time.sleep(1)  # be polite to the free API - avoid rate limiting

    df = pd.DataFrame(all_rows)
    before = len(df)
    df = df.drop_duplicates(subset="station_id")  # border overlaps between neighboring boxes
    print(f"Removed {before - len(df)} duplicate stations from overlapping borders")

    df.to_csv(OUTPUT_FILE, index=False)
    print(f"Saved {len(df)} unique charging stations to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
