"""Build the inputs that the PMTiles map needs.

Writes three files into data/pmtiles/:
  lsoa.geojson  — minimal geometry + {id, name, lad_cd} for tippecanoe
  lad.geojson   — minimal geometry + {id, name} for tippecanoe
  domains.json  — every domain value keyed by feature id, plus a "_mismatch"
                  pseudo-domain (LSOA abs_diff, LAD mean abs_diff)

Geometry rides in the tiles; values ride in domains.json. The map re-styles by
fetching a new lookup, never new geometry.
"""
import json
import os
import sys

import geopandas as gpd
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.constants import (
    PPFI_DOMAINS_LSOA, PPFI_DOMAINS_LAD,
    IMD_DOMAINS_LSOA, IMD_DOMAINS_LAD,
)

SRC_LSOA  = "data/ppfi_imd_lsoa_england.geojson"
SRC_LAD   = "data/ppfi_imd_lad_england.geojson"
MISMATCH  = "data/imd_ppfi_mismatch.csv"
OUT_DIR   = "data/pmtiles"


def _to_lookup(df, id_col, val_col):
    """{id: float | None} skipping NaN."""
    out = {}
    for _id, v in zip(df[id_col], df[val_col]):
        out[str(_id)] = None if pd.isna(v) else float(v)
    return out


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    lsoa = gpd.read_file(SRC_LSOA).set_crs(27700, allow_override=True).to_crs(4326)
    lad  = gpd.read_file(SRC_LAD ).set_crs(27700, allow_override=True).to_crs(4326)

    lsoa["id"]   = lsoa["LSOA21CD"].astype(str).str.strip().str.upper()
    lsoa["name"] = lsoa.get("LSOA21NM_x", lsoa.get("LSOA21NM", lsoa["id"]))
    lad["id"]    = lad["LAD24CD"].astype(str).str.strip().str.upper()
    lad["name"]  = lad.get("LAD24NM_y", lad.get("LAD24NM", lad["id"]))

    # join LAD code onto LSOA — required so the JS layer can filter
    # LSOAs by selected LAD without an extra lookup
    mismatch = pd.read_csv(MISMATCH)
    lsoa_to_lad = (
        mismatch[["lsoa21cd", "lad24cd"]]
        .dropna().drop_duplicates("lsoa21cd")
        .assign(
            lsoa21cd=lambda d: d["lsoa21cd"].astype(str).str.strip().str.upper(),
            lad24cd =lambda d: d["lad24cd" ].astype(str).str.strip().str.upper(),
        )
        .rename(columns={"lsoa21cd": "id", "lad24cd": "lad_cd"})
    )
    lsoa = lsoa.merge(lsoa_to_lad, on="id", how="left")

    # numeric coercion for all domain columns (parallel of data_loader.py)
    for col in lsoa.columns:
        if col.startswith(("pp_", "imd_")):
            lsoa[col] = pd.to_numeric(lsoa[col], errors="coerce")
    for col in lad.columns:
        if col.startswith(("combined", "domain_", "imd_", "income_", "employment_",
                           "education_", "health_", "crime_", "barriers_", "living_")):
            lad[col] = pd.to_numeric(lad[col], errors="coerce")

    # tile-bound geojsons — minimal properties
    lsoa[["id", "name", "lad_cd", "geometry"]].to_file(
        f"{OUT_DIR}/lsoa.geojson", driver="GeoJSON")
    lad[["id", "name", "geometry"]].to_file(
        f"{OUT_DIR}/lad.geojson", driver="GeoJSON")

    # domain lookups
    domains = {"ppfi": {}, "imd": {}}
    for dname, col in PPFI_DOMAINS_LSOA.items():
        domains["ppfi"].setdefault(dname, {})["lsoa"] = _to_lookup(lsoa, "id", col) if col in lsoa else {}
    for dname, col in PPFI_DOMAINS_LAD.items():
        domains["ppfi"].setdefault(dname, {})["lad"]  = _to_lookup(lad,  "id", col) if col in lad  else {}
    for dname, col in IMD_DOMAINS_LSOA.items():
        domains["imd"].setdefault(dname, {})["lsoa"]  = _to_lookup(lsoa, "id", col) if col in lsoa else {}
    for dname, col in IMD_DOMAINS_LAD.items():
        domains["imd"].setdefault(dname, {})["lad"]   = _to_lookup(lad,  "id", col) if col in lad  else {}

    # mismatch pseudo-domain
    #   LSOA level: |PPFI decile − IMD decile|
    #   LAD level:  mean of the LSOA gap inside each LAD
    mm = lsoa[["id", "lad_cd", "pp_dec_combined", "imd_decile"]].copy()
    mm["abs_diff"] = (mm["pp_dec_combined"] - mm["imd_decile"]).abs()
    lad_mismatch = mm.dropna(subset=["lad_cd"]).groupby("lad_cd")["abs_diff"].mean()
    domains["_mismatch"] = {
        "lsoa": _to_lookup(mm, "id", "abs_diff"),
        "lad":  {str(k): float(v) for k, v in lad_mismatch.items() if pd.notna(v)},
    }

    with open(f"{OUT_DIR}/domains.json", "w") as f:
        json.dump(domains, f)

    print(f"wrote {OUT_DIR}/lsoa.geojson, lad.geojson, domains.json")
    print(f"  lsoa features: {len(lsoa)}, lad features: {len(lad)}")
    print(f"  ppfi domains: {list(domains['ppfi'])}")
    print(f"  imd  domains: {list(domains['imd'])}")


if __name__ == "__main__":
    main()
