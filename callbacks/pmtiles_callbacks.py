"""Server callbacks that drive the MapLibre maps.

Each map listens to two stores: a *_lookup ({"lsoa": {id: value}, "lad": ...})
and a *_filter ({"lsoa": [ids] | None, "lad": [ids] | None}). The JS in
assets/pmtiles_map.js paints fill-color from the lookup and applies the filter
as an ["in", id, ...] expression. `None` means no filter on that level.

Lookup values come from data/pmtiles/domains.json (built by
data_creation/prep_pmtiles.py). Filters are derived from the in-memory
GeoDataFrames in utils/data.
"""
import json
import os

import pandas as pd
from dash import html
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from app import app
from utils.data import gdf_lsoa, gdf_lad
from utils.constants import (
    PPFI_DOMAINS_LSOA, PPFI_DOMAINS_LAD,
    IMD_DOMAINS_LSOA, IMD_DOMAINS_LAD,
)
from utils.figures import _hover_narrative

# ---------------------------------------------------------------- domain JSON
_DOMAINS_PATH = "data/pmtiles/domains.json"
if os.path.exists(_DOMAINS_PATH):
    with open(_DOMAINS_PATH) as f:
        _DOMAINS = json.load(f)
else:
    # graceful fallback: prep_pmtiles.py hasn't been run yet
    _DOMAINS = {"ppfi": {}, "imd": {}, "_mismatch": {"lsoa": {}, "lad": {}}}


def _title(dataset, domain):
    return f"{dataset.upper()} · {domain.replace('_', ' ').capitalize()}"


def _lsoa_col(dataset, domain):
    table = PPFI_DOMAINS_LSOA if dataset == "ppfi" else IMD_DOMAINS_LSOA
    return table.get(domain) or table.get("combined")


def _lad_col(dataset, domain):
    table = PPFI_DOMAINS_LAD if dataset == "ppfi" else IMD_DOMAINS_LAD
    return table.get(domain) or table.get("combined")


def _to_int_list(v):
    if v in (None, "", "All"):
        return []
    if not isinstance(v, (list, tuple, set)):
        v = [v]
    out = []
    for x in v:
        try: out.append(int(x))
        except Exception: pass
    return out


def _lsoa_ids_for_deciles(dataset, domain, deciles):
    """LSOA ids whose decile value is in `deciles`. Empty list -> None (no filter)."""
    deciles = _to_int_list(deciles)
    if not deciles:
        return None
    col = _lsoa_col(dataset, domain)
    if col not in gdf_lsoa.columns:
        return None
    return gdf_lsoa.loc[gdf_lsoa[col].isin(deciles), "id"].tolist()


def _lad_ids_for_percentile(dataset, domain, percent):
    """LAD ids in the top `percent` of rank (1 = most deprived). None -> no filter."""
    if percent is None or percent >= 100:
        return None
    col = _lad_col(dataset, domain)
    if col not in gdf_lad.columns:
        return None
    max_rank = gdf_lad[col].max()
    if max_rank is None or max_rank != max_rank:   # NaN guard
        return None
    cutoff = (percent / 100.0) * max_rank
    return gdf_lad.loc[gdf_lad[col] <= cutoff, "id"].tolist()


def _selected_lad_ids(selected_lads):
    """Normalise selected_lad_store payload to a list of LAD ids."""
    if not selected_lads:
        return []
    if isinstance(selected_lads, dict):
        selected_lads = [selected_lads]
    return [s["lad_id"] for s in selected_lads if isinstance(s, dict) and s.get("lad_id")]


def _lsoa_ids_within_lads(lad_ids):
    """All LSOA ids whose lad_cd is in `lad_ids`."""
    if not lad_ids or "lad_cd" not in gdf_lsoa.columns:
        return None
    return gdf_lsoa.loc[gdf_lsoa["lad_cd"].isin(lad_ids), "id"].tolist()


def _intersect(a, b):
    """Intersect two id lists, treating None as 'no filter on this axis'."""
    if a is None: return b
    if b is None: return a
    return list(set(a) & set(b))


# ============================================================================
# SINGLE MAP — view "map", map_type "single"
# ============================================================================
@app.callback(
    Output("single_lookup", "data"),
    Input("dataset_selector", "value"),
    Input("domain_selector", "value"),
)
def push_single_lookup(dataset, domain):
    payload = dict(_DOMAINS.get(dataset, {}).get(domain) or {"lsoa": {}, "lad": {}})
    payload["_title"] = _title(dataset, domain)
    return payload


@app.callback(
    Output("single_filter", "data"),
    Input("geography_selector", "value"),
    Input("dataset_selector", "value"),
    Input("domain_selector", "value"),
    Input("lsoa_decile_filter", "value"),
    Input("lad_rank_filter", "value"),
    Input("selected_lad_store", "data"),
)
def push_single_filter(geography, dataset, domain, lsoa_deciles, lad_percent, selected_lads):
    if geography == "lsoa":
        decile_ids = _lsoa_ids_for_deciles(dataset, domain, lsoa_deciles)
        within_ids = _lsoa_ids_within_lads(_selected_lad_ids(selected_lads))
        return {"lsoa": _intersect(decile_ids, within_ids), "lad": None}
    return {"lsoa": None, "lad": _lad_ids_for_percentile(dataset, domain, lad_percent)}


@app.callback(Output("single_geography", "data"), Input("geography_selector", "value"))
def push_single_geography(geography):
    return geography


@app.callback(Output("single_palette", "data"), Input("dataset_selector", "value"))
def push_single_palette(dataset):
    return dataset   # "ppfi" or "imd" — matches PALETTES key in pmtiles_map.js


# Manually flipping geography back to LAD clears any LSOA-drilldown selection.
# (Drilldown clicks set geography to "lsoa" + selected_lad_store at the same
# time via set_props in JS, so we only clear when the user moves to "lad".)
@app.callback(
    Output("selected_lad_store", "data", allow_duplicate=True),
    Input("geography_selector", "value"),
    State("selected_lad_store", "data"),
    prevent_initial_call=True,
)
def clear_selection_on_lad_view(geography, current):
    if geography == "lad" and current:
        return []
    raise PreventUpdate


# ============================================================================
# COMPARE MAPS — view "compare"
# ============================================================================
@app.callback(
    Output("compare_left_lookup",  "data"),
    Output("compare_right_lookup", "data"),
    Input("domain_selector_ppfi", "value"),
    Input("domain_selector_imd",  "value"),
)
def push_compare_lookups(domain_ppfi, domain_imd):
    left  = dict(_DOMAINS.get("ppfi", {}).get(domain_ppfi) or {"lsoa": {}, "lad": {}})
    right = dict(_DOMAINS.get("imd",  {}).get(domain_imd)  or {"lsoa": {}, "lad": {}})
    left ["_title"] = _title("ppfi", domain_ppfi)
    right["_title"] = _title("imd",  domain_imd)
    return left, right


@app.callback(
    Output("compare_left_filter",  "data"),
    Output("compare_right_filter", "data"),
    Input("geography_selector",   "value"),
    Input("domain_selector_ppfi", "value"),
    Input("domain_selector_imd",  "value"),
    Input("lsoa_decile_filter",   "value"),
    Input("lad_rank_filter",      "value"),
    Input("selected_lad_store",   "data"),
)
def push_compare_filters(geography, domain_ppfi, domain_imd, lsoa_deciles, lad_percent, selected_lads):
    if geography == "lsoa":
        within = _lsoa_ids_within_lads(_selected_lad_ids(selected_lads))
        left  = {"lsoa": _intersect(_lsoa_ids_for_deciles("ppfi", domain_ppfi, lsoa_deciles), within), "lad": None}
        right = {"lsoa": _intersect(_lsoa_ids_for_deciles("imd",  domain_imd,  lsoa_deciles), within), "lad": None}
    else:
        left  = {"lsoa": None, "lad": _lad_ids_for_percentile("ppfi", domain_ppfi, lad_percent)}
        right = {"lsoa": None, "lad": _lad_ids_for_percentile("imd",  domain_imd,  lad_percent)}
    return left, right


@app.callback(Output("compare_geography", "data"), Input("geography_selector", "value"))
def push_compare_geography(geography):
    return geography


# ============================================================================
# MISMATCH MAP — view "map", map_type "mismatch_map"
# LSOA level shows |PPFI decile − IMD decile|. LAD level shows the mean LSOA
# gap inside each LAD. The threshold slider filters by that same metric.
# ============================================================================
@app.callback(Output("mismatch_lookup", "data"), Input("view_selector", "value"))
def push_mismatch_lookup(_view):
    payload = dict(_DOMAINS.get("_mismatch") or {"lsoa": {}, "lad": {}})
    payload["_title"] = "PPFI vs IMD — absolute decile difference"
    return payload


@app.callback(Output("mismatch_geography", "data"), Input("view_selector", "value"))
def push_mismatch_geography(_view):
    # Difference map is LSOA-only — ignore the sidebar toggle here.
    return "lsoa"


@app.callback(
    Output("mismatch_filter", "data"),
    Input("mismatch_threshold_slider", "value"),
)
def push_mismatch_filter(threshold):
    if threshold is None or threshold <= 0:
        return {"lsoa": None, "lad": None}
    table = _DOMAINS.get("_mismatch", {}).get("lsoa", {})
    ids = [k for k, v in table.items() if v is not None and v >= threshold]
    return {"lsoa": ids, "lad": None}


# ============================================================================
# DOMAIN DROPDOWN OPTIONS (moved from map_callbacks.py)
# ============================================================================
def _get_domains_for_single(geo, dataset):
    if geo == "lsoa" and dataset == "ppfi":  return PPFI_DOMAINS_LSOA
    if geo == "lsoa" and dataset == "imd":   return IMD_DOMAINS_LSOA
    if geo == "lad"  and dataset == "ppfi":  return PPFI_DOMAINS_LAD
    return IMD_DOMAINS_LAD


def _get_domains_for_compare(geo):
    if geo == "lsoa":
        keys = set(PPFI_DOMAINS_LSOA) | set(IMD_DOMAINS_LSOA)
    else:
        keys = set(PPFI_DOMAINS_LAD) | set(IMD_DOMAINS_LAD)
    return {k: k for k in sorted(keys)}


@app.callback(
    Output("domain_selector", "options"),
    Output("domain_selector", "value"),
    Input("view_selector", "value"),
    Input("geography_selector", "value"),
    Input("dataset_selector", "value"),
    Input("domain_selector", "value"),
)
def update_domain_options(view, geo, dataset, current_domain):
    domains = (_get_domains_for_compare(geo) if view == "compare"
               else _get_domains_for_single(geo, dataset))
    opts = [{"label": k.replace("_", " ").capitalize(), "value": k} for k in domains.keys()]
    if current_domain not in domains:
        current_domain = "combined"
    return opts, current_domain


# ============================================================================
# INFO BAR NARRATIVE — driven by hover, falls back to current LAD selection
# Narrative text comes from utils.figures._hover_narrative.
# ============================================================================
_N_LADS     = len(gdf_lad)
_LSOA_NAMES = dict(zip(gdf_lsoa["id"].astype(str), gdf_lsoa.get("LSOA21NM_x", gdf_lsoa["id"])))
_LAD_NAMES  = dict(zip(gdf_lad["id"].astype(str),  gdf_lad.get("LAD24NM_y",  gdf_lad.get("LAD24NM", gdf_lad["id"]))))


def _row_for(level, fid):
    """Build the row dict _hover_narrative expects (with ppfi_combined / imd_combined / diff)."""
    src = gdf_lad if level == "lad" else gdf_lsoa
    match = src[src["id"] == fid]
    if match.empty:
        return None
    row = match.iloc[0].to_dict()
    if level == "lad":
        ppfi, imd = row.get("combined"), row.get("imd_rank")
    else:
        ppfi, imd = row.get("pp_dec_combined"), row.get("imd_decile")
    row["ppfi_combined"] = None if pd.isna(ppfi) else ppfi
    row["imd_combined"]  = None if pd.isna(imd)  else imd
    row["diff"] = (row["ppfi_combined"] - row["imd_combined"]
                   if row["ppfi_combined"] is not None and row["imd_combined"] is not None
                   else 0)
    return row


def _info_children(level, fid, name):
    row = _row_for(level, fid)
    body = _hover_narrative(row, level, _N_LADS) if row else ""
    label = name or (_LAD_NAMES.get(fid, fid) if level == "lad" else _LSOA_NAMES.get(fid, fid))
    if not body:
        return label
    parts = body.split("<br>")
    out = [html.Span(f"{label} — {parts[0]}")]
    for p in parts[1:]:
        out.append(html.Br())
        out.append(html.Span(p))
    return out


_INFO_BLANK = "Hover over an area to see insight."
_INFO_BLANK_STYLE  = {"color": "#aaa", "fontStyle": "italic"}
_INFO_ACTIVE_STYLE = {"color": "#444", "fontStyle": "normal"}


@app.callback(
    Output("map_info_bar_text",     "children"),
    Output("map_info_bar_text",     "style"),
    Output("compare_info_bar_text", "children"),
    Output("compare_info_bar_text", "style"),
    Input("hovered_feature",    "data"),
    Input("selected_lad_store", "data"),
)
def update_info_bar(hovered, selected):
    if hovered and hovered.get("id"):
        children = _info_children(hovered.get("level", "lsoa"), hovered["id"], hovered.get("name", ""))
        return children, _INFO_ACTIVE_STYLE, children, _INFO_ACTIVE_STYLE
    if selected:
        last = selected[-1]
        children = _info_children("lad", last.get("lad_id"), last.get("lad_name", ""))
        return children, _INFO_ACTIVE_STYLE, children, _INFO_ACTIVE_STYLE
    return _INFO_BLANK, _INFO_BLANK_STYLE, _INFO_BLANK, _INFO_BLANK_STYLE
