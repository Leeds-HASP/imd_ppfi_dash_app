from collections import defaultdict

from utils.data import geojson_lsoa, gdf_lsoa

_lsoa_feature_by_id = {
    feature.get("properties", {}).get("id"): feature
    for feature in geojson_lsoa.get("features", [])
}

_lsoa_ids_by_lad = defaultdict(list)
for row in gdf_lsoa[["id", "lad_cd"]].dropna(subset=["id", "lad_cd"]).itertuples(index=False):
    _lsoa_ids_by_lad[str(row.lad_cd)].append(str(row.id))

_lsoa_geojson_by_lads_cache = {}


def get_lsoa_geojson_for_lads(lad_ids):
    if not lad_ids:
        return geojson_lsoa

    key = tuple(sorted({str(lad_id) for lad_id in lad_ids if lad_id}))
    if not key:
        return geojson_lsoa

    cached = _lsoa_geojson_by_lads_cache.get(key)
    if cached is not None:
        return cached

    selected_ids = []
    for lad_id in key:
        selected_ids.extend(_lsoa_ids_by_lad.get(lad_id, []))

    features = [
        _lsoa_feature_by_id[lsoa_id]
        for lsoa_id in selected_ids
        if lsoa_id in _lsoa_feature_by_id
    ]

    subset = {
        "type": "FeatureCollection",
        "features": features,
    }
    _lsoa_geojson_by_lads_cache[key] = subset
    return subset
