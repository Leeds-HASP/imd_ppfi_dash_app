# callbacks/map_callbacks.py
import math
import dash
from dash import no_update, html, Patch
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output, State

from app import app

from utils.data import gdf_lsoa, geojson_lsoa, gdf_lad, geojson_lad, gdf_lsoa_full, gdf_lad_full
from utils.figures import (
    make_map,
    get_patch_data,
    get_domains_for_single,
    get_domains_for_compare,
)
from utils.constants import (
    PPFI_DOMAINS_LAD,
    IMD_DOMAINS_LAD,
    PPFI_DOMAINS_LSOA,
    IMD_DOMAINS_LSOA,
)

# helpers
def _map_title(text, geography):
    subtitle = "Decile 1 = highest priority" if geography == "lsoa" else "Rank 1 = highest priority"
    return {"text": f"{text}<br><sup style='font-size:11px; color:#888'>{subtitle}</sup>", "x": 0.5}

def _to_int_list(v):
    if v is None or v == '' or v == 'All':
        return []
    if isinstance(v, (list, tuple, set)):
        out = []
        for item in v:
            try:
                out.append(int(item))
            except Exception:
                pass
        return out
    try:
        return [int(v)]
    except Exception:
        return []


def _filter_lsoa_by_deciles(gdf, dataset: str, domain: str, deciles_value):
    deciles = _to_int_list(deciles_value)
    if not deciles:
        return gdf
    col = (PPFI_DOMAINS_LSOA[domain] if dataset == 'ppfi' else IMD_DOMAINS_LSOA[domain])
    if col not in gdf.columns:
        return gdf
    return gdf[gdf[col].isin(deciles)]


def _filter_lad_by_percent(gdf, dataset: str, domain: str, lad_percent):
    if lad_percent is None:
        return gdf
    rank_col = (PPFI_DOMAINS_LAD[domain] if dataset == 'ppfi' else IMD_DOMAINS_LAD[domain])
    if rank_col not in gdf.columns:
        return gdf
    max_rank_val = gdf[rank_col].max()
    if max_rank_val is None:
        return gdf
    max_rank = int((lad_percent / 100) * max_rank_val)
    return gdf[gdf[rank_col] <= max_rank]


def _filter_lsoa_to_selected_lads(gdf, selected_lads):
    if not selected_lads:
        return gdf
    if 'lad_cd' not in gdf.columns:
        return gdf
    ids = [s['lad_id'] for s in selected_lads if s.get('lad_id')]
    if not ids:
        return gdf
    return gdf[gdf['lad_cd'].isin(ids)]


def _center_zoom_from_bounds(bounds):
    minx, miny, maxx, maxy = bounds
    center = {'lon': (minx + maxx) / 2, 'lat': (miny + maxy) / 2}
    span = max(maxx - minx, maxy - miny)
    if span <= 0:
        zoom = 9.5
    else:
        zoom = 8.5 - math.log(span + 1e-9, 2)
    zoom = max(5.3, min(10.5, zoom))
    return center, zoom


def _extract_lad_from_click(clickData, geography='lad'):
    if not clickData or not clickData.get('points'):
        return None, None
    pt = clickData['points'][0]
    cd = pt.get('customdata')

    if geography == 'lsoa' and isinstance(cd, (list, tuple)) and len(cd) > 6:
        lad_id = cd[6] or None
        lad_name = None
        return lad_id, lad_name

    lad_id = pt.get('location') or pt.get('id')
    lad_name = None
    if isinstance(cd, (list, tuple)) and len(cd) > 0:
        lad_name = cd[0]
    return lad_id, lad_name


def _make_lad_label(selected_lads):
    if not selected_lads:
        return None
    names = [s.get('lad_name') or s.get('lad_id') for s in selected_lads]
    if len(names) == 1:
        return names[0]
    if len(names) <= 3:
        return ', '.join(names)
    return f'{names[0]}, {names[1]} + {len(names) - 2} more'


def _normalise_store(store):
    if not store:
        return []
    if isinstance(store, dict):
        return [store] if store.get('lad_id') else []
    return store


def _choropleth_trace_index(selected_lads):
    """
    When drilled into LADs the lad_trace is prepended to data[0],
    pushing the choropleth to data[1]. Otherwise it's data[0].
    """
    return 1 if selected_lads else 0


# ── drilldown ────────────────────────────────────────────────────────────────

@app.callback(
    Output('selected_lad_store', 'data'),
    Output('geography_selector', 'value'),
    Input('map_single', 'clickData'),
    Input('map_compare_left', 'clickData'),
    Input('map_compare_right', 'clickData'),
    Input('geography_selector', 'value'),
    Input('view_selector', 'value'),
    State('selected_lad_store', 'data'),
    prevent_initial_call=True,
)
def drilldown_lad_to_lsoa(click_single, click_left, click_right, geography, view, current_store):
    triggered = (
        dash.callback_context.triggered[0]['prop_id'].split('.')[0]
        if dash.callback_context.triggered else None
    )

    if triggered == 'geography_selector' and geography == 'lad':
        return [], no_update

    if geography not in ('lad', 'lsoa'):
        raise PreventUpdate

    if view == 'map' and triggered == 'map_single':
        lad_id, lad_name = _extract_lad_from_click(click_single, geography)
    elif view == 'compare' and triggered in ('map_compare_left', 'map_compare_right'):
        clickData = click_left if triggered == 'map_compare_left' else click_right
        lad_id, lad_name = _extract_lad_from_click(clickData, geography)
    else:
        raise PreventUpdate

    if not lad_id:
        raise PreventUpdate

    current_store = _normalise_store(current_store)

    if not lad_name:
        from utils.constants import LAD_NAME
        from utils.data import gdf_lad as _gdf_lad
        name_col = next((c for c in [LAD_NAME, "LAD24NM", "LAD23NM", "lad_name", "NAME", "name"]
                         if c in _gdf_lad.columns), None)
        if name_col:
            match = _gdf_lad[_gdf_lad['id'] == lad_id]
            if not match.empty:
                lad_name = match.iloc[0][name_col]

    existing_ids = [s['lad_id'] for s in current_store]

    if lad_id in existing_ids:
        new_store = [s for s in current_store if s['lad_id'] != lad_id]
    else:
        new_store = current_store + [{'lad_id': lad_id, 'lad_name': lad_name}]

    if not new_store:
        return [], 'lad'
    return new_store, 'lsoa'


# ── domain options ────────────────────────────────────────────────────────────

@app.callback(
    Output('domain_selector', 'options'),
    Output('domain_selector', 'value'),
    Input('view_selector', 'value'),
    Input('geography_selector', 'value'),
    Input('dataset_selector', 'value'),
    Input('domain_selector', 'value'),
)
def update_domain_options(view, geo, dataset, current_domain):
    domains = get_domains_for_compare(geo) if view == 'compare' else get_domains_for_single(geo, dataset)
    opts = [{'label': k.replace('_', ' ').title(), 'value': k} for k in domains.keys()]
    if current_domain not in domains:
        current_domain = 'combined'
    return opts, current_domain


# ── single map: full rebuild ──────────────────────────────────────────────────
# Triggers: geography change, drilldown, view change — geometry or traces change

@app.callback(
    Output('map_single', 'figure'),
    Input('geography_selector', 'value'),
    Input('selected_lad_store', 'data'),
    Input('view_selector', 'value'),
    State('dataset_selector', 'value'),
    State('domain_selector', 'value'),
    State('lsoa_decile_filter', 'value'),
    State('lad_rank_filter', 'value'),
)
def rebuild_map_single(geography, selected_lads, view, dataset, domain, lsoa_decile, lad_percent):
    if view != 'map':
        raise PreventUpdate

    selected_lads = _normalise_store(selected_lads)

    filtered_lsoa = gdf_lsoa
    filtered_lad = gdf_lad

    if geography == 'lsoa':
        filtered_lsoa = _filter_lsoa_by_deciles(gdf_lsoa, dataset, domain, lsoa_decile)
        filtered_lsoa = _filter_lsoa_to_selected_lads(filtered_lsoa, selected_lads)
    if geography == 'lad':
        filtered_lad = _filter_lad_by_percent(gdf_lad, dataset, domain, lad_percent)

    lad_rev = '_'.join(sorted(s['lad_id'] for s in selected_lads)) or 'none'
    fig = make_map(
        geography, dataset, domain,
        filtered_lsoa, geojson_lsoa,
        filtered_lad, geojson_lad,
        selected_lads=selected_lads,
        show_lad_boundaries=(geography == 'lsoa'),
        uirevision=f"{geography}_{lad_rev}",
    )

    if geography == 'lsoa' and selected_lads and not filtered_lsoa.empty:
        try:
            minx, miny, maxx, maxy = filtered_lsoa.total_bounds
            center, zoom = _center_zoom_from_bounds((minx, miny, maxx, maxy))
            fig.update_layout(mapbox_center=center, mapbox_zoom=zoom)
            lad_label = _make_lad_label(selected_lads)
            if lad_label:
                fig.update_layout(
                    title=_map_title(f'{dataset.upper()} – {domain.replace("_"," ").title()} (LSOA) within {lad_label}', geography)
                )
        except Exception:
            pass

    return fig


# ── single map: colour/filter patch ──────────────────────────────────────────
# Triggers: dataset, domain, filter changes only — geometry stays, only z + customdata update

@app.callback(
    Output('map_single', 'figure', allow_duplicate=True),
    Input('dataset_selector', 'value'),
    Input('domain_selector', 'value'),
    Input('lsoa_decile_filter', 'value'),
    Input('lad_rank_filter', 'value'),
    State('geography_selector', 'value'),
    State('selected_lad_store', 'data'),
    State('view_selector', 'value'),
    prevent_initial_call=True,
)
def patch_map_single(dataset, domain, lsoa_decile, lad_percent, geography, selected_lads, view):
    if view != 'map':
        raise PreventUpdate

    selected_lads = _normalise_store(selected_lads)

    if geography == 'lsoa':
        filtered = _filter_lsoa_by_deciles(gdf_lsoa_full, dataset, domain, lsoa_decile)
        filtered = _filter_lsoa_to_selected_lads(filtered, selected_lads)
        valid_ids = set(filtered['id'])
        z, customdata, hovertemplate = get_patch_data(
            geography, dataset, domain, gdf_lsoa_full, valid_ids
        )
    else:
        filtered = _filter_lad_by_percent(gdf_lad_full, dataset, domain, lad_percent)
        valid_ids = set(filtered['id'])
        z, customdata, hovertemplate = get_patch_data(
            geography, dataset, domain, gdf_lad_full, valid_ids
        )

    trace_idx = _choropleth_trace_index(selected_lads)
    pretty = domain.replace("_", " ").title()

    patched = Patch()
    patched['data'][trace_idx]['z'] = z
    patched['data'][trace_idx]['customdata'] = customdata.tolist()
    patched['data'][trace_idx]['hovertemplate'] = hovertemplate
    patched['layout']['title'] = _map_title(f'{dataset.upper()} – {pretty} ({geography.upper()})', geography)

    return patched


# ── compare maps: full rebuild ────────────────────────────────────────────────

@app.callback(
    Output('map_compare_left', 'figure'),
    Output('map_compare_right', 'figure'),
    Input('geography_selector', 'value'),
    Input('selected_lad_store', 'data'),
    Input('view_selector', 'value'),
    State('domain_selector_ppfi', 'value'),
    State('domain_selector_imd', 'value'),
    State('lsoa_decile_filter', 'value'),
    State('lad_rank_filter', 'value'),
)
def rebuild_compare_maps(geography, selected_lads, view, domain_ppfi, domain_imd, lsoa_decile, lad_percent):
    selected_lads = _normalise_store(selected_lads)
    lad_rev = '_'.join(sorted(s['lad_id'] for s in selected_lads)) or 'none'
    compare_rev = f"compare_{geography}_{lad_rev}"

    if geography == 'lsoa':
        fl_left  = _filter_lsoa_to_selected_lads(_filter_lsoa_by_deciles(gdf_lsoa, 'ppfi', domain_ppfi, lsoa_decile), selected_lads)
        fl_right = _filter_lsoa_to_selected_lads(_filter_lsoa_by_deciles(gdf_lsoa, 'imd',  domain_imd,  lsoa_decile), selected_lads)
        fl_lad_left = fl_lad_right = gdf_lad
    else:
        fl_left = fl_right = gdf_lsoa
        fl_lad_left  = _filter_lad_by_percent(gdf_lad, 'ppfi', domain_ppfi, lad_percent)
        fl_lad_right = _filter_lad_by_percent(gdf_lad, 'imd',  domain_imd,  lad_percent)

    left_fig = make_map(
        geography, 'ppfi', domain_ppfi,
        fl_left, geojson_lsoa, fl_lad_left, geojson_lad,
        compact_hover=True, selected_lads=selected_lads,
        show_lad_boundaries=(geography == 'lsoa'), uirevision=compare_rev,
    )
    right_fig = make_map(
        geography, 'imd', domain_imd,
        fl_right, geojson_lsoa, fl_lad_right, geojson_lad,
        compact_hover=True, selected_lads=selected_lads,
        show_lad_boundaries=(geography == 'lsoa'), uirevision=compare_rev,
    )

    if geography == 'lsoa' and selected_lads:
        bounds_gdf = fl_left if not fl_left.empty else fl_right
        if not bounds_gdf.empty:
            try:
                minx, miny, maxx, maxy = bounds_gdf.total_bounds
                center, zoom = _center_zoom_from_bounds((minx, miny, maxx, maxy))
                left_fig.update_layout(mapbox_center=center, mapbox_zoom=zoom)
                right_fig.update_layout(mapbox_center=center, mapbox_zoom=zoom)
            except Exception:
                pass

    pretty_ppfi = domain_ppfi.replace("_", " ").title()
    pretty_imd  = domain_imd.replace("_", " ").title()
    geo_label   = geography.upper()

    if selected_lads:
        lad_label = _make_lad_label(selected_lads)
        left_fig.update_layout(title=_map_title(f"PPFI – {pretty_ppfi} ({geo_label}) within {lad_label}", geography))
        right_fig.update_layout(title=_map_title(f"IMD – {pretty_imd} ({geo_label}) within {lad_label}", geography))
    else:
        left_fig.update_layout(title=_map_title(f"PPFI – {pretty_ppfi} ({geo_label})", geography))
        right_fig.update_layout(title=_map_title(f"IMD – {pretty_imd} ({geo_label})", geography))

    return left_fig, right_fig


# ── compare maps: colour/filter patch ────────────────────────────────────────

@app.callback(
    Output('map_compare_left', 'figure', allow_duplicate=True),
    Output('map_compare_right', 'figure', allow_duplicate=True),
    Input('domain_selector_ppfi', 'value'),
    Input('domain_selector_imd', 'value'),
    Input('lsoa_decile_filter', 'value'),
    Input('lad_rank_filter', 'value'),
    State('geography_selector', 'value'),
    State('selected_lad_store', 'data'),
    State('view_selector', 'value'),
    prevent_initial_call=True,
)
def patch_compare_maps(domain_ppfi, domain_imd, lsoa_decile, lad_percent, geography, selected_lads, view):
    selected_lads = _normalise_store(selected_lads)
    trace_idx = _choropleth_trace_index(selected_lads)

    if geography == 'lsoa':
        fl_left  = _filter_lsoa_to_selected_lads(_filter_lsoa_by_deciles(gdf_lsoa_full, 'ppfi', domain_ppfi, lsoa_decile), selected_lads)
        fl_right = _filter_lsoa_to_selected_lads(_filter_lsoa_by_deciles(gdf_lsoa_full, 'imd',  domain_imd,  lsoa_decile), selected_lads)
        valid_left  = set(fl_left['id'])
        valid_right = set(fl_right['id'])
        z_left,  cd_left,  ht_left  = get_patch_data(geography, 'ppfi', domain_ppfi, gdf_lsoa_full, valid_left,  compact_hover=True)
        z_right, cd_right, ht_right = get_patch_data(geography, 'imd',  domain_imd,  gdf_lsoa_full, valid_right, compact_hover=True)
    else:
        fl_left  = _filter_lad_by_percent(gdf_lad_full, 'ppfi', domain_ppfi, lad_percent)
        fl_right = _filter_lad_by_percent(gdf_lad_full, 'imd',  domain_imd,  lad_percent)
        valid_left  = set(fl_left['id'])
        valid_right = set(fl_right['id'])
        z_left,  cd_left,  ht_left  = get_patch_data(geography, 'ppfi', domain_ppfi, gdf_lad_full, valid_left,  compact_hover=True)
        z_right, cd_right, ht_right = get_patch_data(geography, 'imd',  domain_imd,  gdf_lad_full, valid_right, compact_hover=True)

    pretty_ppfi = domain_ppfi.replace("_", " ").title()
    pretty_imd  = domain_imd.replace("_", " ").title()
    geo_label   = geography.upper()

    left_patch = Patch()
    left_patch['data'][trace_idx]['z'] = z_left
    left_patch['data'][trace_idx]['customdata'] = cd_left.tolist()
    left_patch['data'][trace_idx]['hovertemplate'] = ht_left
    left_patch['layout']['title'] = _map_title(f"PPFI – {pretty_ppfi} ({geo_label})", geography)

    right_patch = Patch()
    right_patch['data'][trace_idx]['z'] = z_right
    right_patch['data'][trace_idx]['customdata'] = cd_right.tolist()
    right_patch['data'][trace_idx]['hovertemplate'] = ht_right
    right_patch['layout']['title'] = _map_title(f"IMD – {pretty_imd} ({geo_label})", geography)

    return left_patch, right_patch


# ── info bars ─────────────────────────────────────────────────────────────────

@app.callback(
    dash.dependencies.Output("map_info_bar_text", "style"),
    dash.dependencies.Output("map_info_bar_text", "children"),
    dash.dependencies.Input("map_single", "hoverData"),
    prevent_initial_call=True,
)
def update_single_info_bar(hover):
    blank_style = {"color": "#aaa", "fontStyle": "italic"}
    blank_text  = "Hover over an area to see insight."
    if not hover or not hover.get("points"):
        raise PreventUpdate
    pt = hover["points"][0]
    cd = pt.get("customdata") or []
    name      = cd[0] if len(cd) > 0 else ""
    narrative = cd[5] if len(cd) > 5 and cd[5] else ""
    if narrative:
        parts = [p.strip() for p in narrative.split("<br>") if p.strip()]
        if name:
            parts[0] = f"{name} - {parts[0]}"
        children = []
        for i, part in enumerate(parts):
            children.append(html.Span(part))
            if i < len(parts) - 1:
                children.append(html.Br())
        return {"color": "#444", "fontStyle": "normal"}, children
    if name:
        return {"color": "#555", "fontStyle": "normal"}, name
    return blank_style, blank_text


@app.callback(
    dash.dependencies.Output("compare_info_bar_text", "style"),
    dash.dependencies.Output("compare_info_bar_text", "children"),
    dash.dependencies.Input("map_compare_left", "hoverData"),
    dash.dependencies.Input("map_compare_right", "hoverData"),
    prevent_initial_call=True,
)
def update_compare_info_bar(hover_left, hover_right):
    blank_style = {"color": "#aaa", "fontStyle": "italic"}
    blank_text  = "Hover over an area to see the name and scores."

    triggered = (
        dash.callback_context.triggered[0]["prop_id"].split(".")[0]
        if dash.callback_context.triggered else None
    )
    hover = hover_left if triggered == "map_compare_left" else hover_right

    if not hover or not hover.get("points"):
        raise PreventUpdate

    pt = hover["points"][0]
    cd = pt.get("customdata") or []
    name  = cd[0] if len(cd) > 0 else ""
    ppfi  = f"PPFI: {cd[1]}" if len(cd) > 1 and cd[1] is not None else ""
    imd   = f"IMD: {cd[2]}"  if len(cd) > 2 and cd[2] is not None else ""
    scores = "  |  ".join(filter(None, [ppfi, imd]))

    if name and scores:
        return {"color": "#444", "fontStyle": "normal"}, f"{name} - {scores}"
    if name:
        return {"color": "#555", "fontStyle": "normal"}, name
    return blank_style, blank_text