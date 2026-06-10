# data_creation/prep_pmtiles.py
#
# Writes data/pmtiles/{lsoa,lad}.geojson for tippecanoe and domains.json keyed
# by feature id. Geometry lives in the tiles, values in domains.json.
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

SRC_LSOA_fullres = "data/Lower_layer_Super_Output_Areas_December_2021_Boundaries_EW_BGC_V5_-3761339731474027792.geojson"
SRC_LSOA  = "data/ppfi_imd_lsoa_england.geojson"
SRC_LAD   = "data/ppfi_imd_lad_england.geojson"
MISMATCH  = "data/imd_ppfi_mismatch.csv"
OUT_DIR   = "data/pmtiles"


def _to_lookup(df, id_col, val_col):
    out = {}
    for _id, v in zip(df[id_col], df[val_col]):
        out[str(_id)] = None if pd.isna(v) else float(v)
    return out


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    lsoa = gpd.read_file(SRC_LSOA).set_crs(27700, allow_override=True).to_crs(4326)

    # swap in the full-res ONS geometry for nicer zoom-in detail
    lsoa_fullres = gpd.read_file(SRC_LSOA_fullres)
    if lsoa_fullres.crs is None:
        lsoa_fullres = lsoa_fullres.set_crs(27700)
    lsoa_fullres = lsoa_fullres.to_crs(4326)

    lsoa = lsoa.drop(columns="geometry").merge(
        lsoa_fullres[["LSOA21CD", "geometry"]], on="LSOA21CD", how="left")
    lsoa = gpd.GeoDataFrame(lsoa, geometry="geometry", crs="EPSG:4326")

    lad  = gpd.read_file(SRC_LAD ).set_crs(27700, allow_override=True).to_crs(4326)

    lsoa["id"]   = lsoa["LSOA21CD"].astype(str).str.strip().str.upper()
    lsoa["name"] = lsoa.get("LSOA21NM_x", lsoa.get("LSOA21NM", lsoa["id"]))
    lad["id"]    = lad["LAD24CD"].astype(str).str.strip().str.upper()
    lad["name"]  = lad.get("LAD24NM_y", lad.get("LAD24NM", lad["id"]))

    # attach lad_cd to each LSOA so the map can filter LSOAs by selected LAD
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

    for col in lsoa.columns:
        if col.startswith(("pp_", "imd_")):
            lsoa[col] = pd.to_numeric(lsoa[col], errors="coerce")
    for col in lad.columns:
        if col.startswith(("combined", "domain_", "imd_", "income_", "employment_",
                           "education_", "health_", "crime_", "barriers_", "living_")):
            lad[col] = pd.to_numeric(lad[col], errors="coerce")

    lsoa[["id", "name", "lad_cd", "geometry"]].to_file(
        f"{OUT_DIR}/lsoa.geojson", driver="GeoJSON")
    lad[["id", "name", "geometry"]].to_file(
        f"{OUT_DIR}/lad.geojson", driver="GeoJSON")

    domains = {"ppfi": {}, "imd": {}}
    for dname, col in PPFI_DOMAINS_LSOA.items():
        domains["ppfi"].setdefault(dname, {})["lsoa"] = _to_lookup(lsoa, "id", col) if col in lsoa else {}
    for dname, col in PPFI_DOMAINS_LAD.items():
        domains["ppfi"].setdefault(dname, {})["lad"]  = _to_lookup(lad,  "id", col) if col in lad  else {}
    for dname, col in IMD_DOMAINS_LSOA.items():
        domains["imd"].setdefault(dname, {})["lsoa"]  = _to_lookup(lsoa, "id", col) if col in lsoa else {}
    for dname, col in IMD_DOMAINS_LAD.items():
        domains["imd"].setdefault(dname, {})["lad"]   = _to_lookup(lad,  "id", col) if col in lad  else {}

    # mismatch: LSOA = |PPFI decile − IMD decile|, LAD = mean LSOA gap
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
