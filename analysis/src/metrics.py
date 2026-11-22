"""Shared loading, cleaning and metric definitions for AirlineDataAnalysis-PBI.

Mirrors the Power BI model (AirlineDataAnalysis-PBI.SemanticModel) exactly:
- Departure date parsed as dd-mm-yyyy.
- Distance used = recorded distance when it is within 0.9x-1.25x of the great-circle distance between the two
  airports (reference/airports.csv), otherwise the great-circle distance rounded to the km. About 14% of flights
  carry another route's distance (for example PNQ-BOM recorded as 1,138 km, the Delhi-Mumbai distance).
- ASK = seats x distance used; RPK = passengers x distance used.
- Fare outlier = fare per passenger above 3x that route's median fare (flagged, not removed). A per-km test is
  wrong here: short routes naturally earn more per km (stage-length effect).
- No rows are removed: repeated flight numbers on the same day are separate flights (different seats, pax, revenue).
"""
from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parents[2]
ANALYSIS_DIR = PROJECT_DIR / "analysis"
DATA_DIR = ANALYSIS_DIR / "data"
OUTPUT_DIR = ANALYSIS_DIR / "output"
RAW_PATH = Path(os.environ.get("AIRLINE_RAW_CSV", PROJECT_DIR / "Raw Data" / "Flight Data Assessment 2025.csv"))
AIRPORTS_PATH = PROJECT_DIR / "reference" / "airports.csv"
DATA_END = pd.Timestamp("2025-05-31")
DIST_LOW, DIST_HIGH, OUTLIER_X = 0.9, 1.25, 3.0


def great_circle_km(lat1, lon1, lat2, lon2):
    la1, lo1, la2, lo2 = map(np.radians, [lat1, lon1, lat2, lon2])
    a = np.sin((la2 - la1) / 2) ** 2 + np.cos(la1) * np.cos(la2) * np.sin((lo2 - lo1) / 2) ** 2
    return 6371 * 2 * np.arcsin(np.sqrt(a))


def load_raw(path: Path | str = RAW_PATH) -> pd.DataFrame:
    return pd.read_csv(path)


def load_airports() -> pd.DataFrame:
    return pd.read_csv(AIRPORTS_PATH)


def clean(raw: pd.DataFrame, airports: pd.DataFrame) -> pd.DataFrame:
    f = raw.copy()
    f["date"] = pd.to_datetime(f["DepartureDate"], format="%d-%m-%Y")
    ap = airports.set_index("IATA")
    for side, col in (("o", "Origin"), ("d", "Destination")):
        f[f"{side}_lat"] = f[col].map(ap["Latitude"]); f[f"{side}_lon"] = f[col].map(ap["Longitude"])
        f[f"{side}_country"] = f[col].map(ap["Country"])
    f["gc_km"] = great_circle_km(f.o_lat, f.o_lon, f.d_lat, f.d_lon)
    ratio = f["Distance"] / f["gc_km"]
    f["distance_corrected"] = ~ratio.between(DIST_LOW, DIST_HIGH)
    f["distance_km"] = np.where(f.distance_corrected, f.gc_km.round(), f.Distance)
    f["route"] = f.Origin + "-" + f.Destination
    f["international"] = (f.o_country != "India") | (f.d_country != "India")
    f["market"] = np.where(f.international, "International", "Domestic")
    f["ask"] = f.Capacity * f.distance_km
    f["rpk"] = f.PaxCount * f.distance_km
    f["load_factor"] = f.PaxCount / f.Capacity
    f["fare"] = f.Revenue / f.PaxCount
    f["fare_outlier"] = f.fare > OUTLIER_X * f.groupby("route").fare.transform("median")
    f["month"] = f.date.dt.to_period("M").dt.to_timestamp()
    return f.drop(columns=["o_lat", "o_lon", "d_lat", "d_lon"])


def load_clean() -> dict[str, pd.DataFrame]:
    raw, ap = load_raw(), load_airports()
    return {"raw": raw, "airports": ap, "flights": clean(raw, ap)}


def headline(f: pd.DataFrame) -> pd.Series:
    """The totals the Power BI cards must show."""
    return pd.Series({
        "flights": len(f), "passengers": f.PaxCount.sum(), "seats": f.Capacity.sum(), "revenue": f.Revenue.sum(),
        "ask": f.ask.sum(), "rpk": f.rpk.sum(), "load_factor": f.PaxCount.sum() / f.Capacity.sum(),
        "rask": f.Revenue.sum() / f.ask.sum(), "yield_per_rpk": f.Revenue.sum() / f.rpk.sum(),
        "routes": f.route.nunique(), "distance_corrected_flights": int(f.distance_corrected.sum()),
        "fare_outliers": int(f.fare_outlier.sum()),
    })
