# callbacks/map_callbacks.py
import math
import dash
import plotly.graph_objects as go
from dash import no_update, html
from dash.exceptions import PreventUpdate
from dash.dependencies import Input, Output

from app import app

from utils.data import gdf_lsoa, geojson_lsoa, gdf_lad, geojson_lad
from utils.figures import (
    make_map,
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
    subtitle = "Decile 1 = most deprived" if geography == "lsoa" else "Rank 1 = most deprived"
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
        lad_name = None  # we don't store LAD name in LSOA customdata; callback will look it up
        return lad_id, lad_name

    #click on LAD choropleth trace (initial drilldown or background trace)
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


def _make_select_lad_figure(title_text: str):
    fig = go.Figure()
    fig.update_layout(
        mapbox=dict(
            style='carto-positron',
            zoom=5.3,
            center={'lat': 53.7, 'lon': -1.5},
        ),
        margin=dict(l=0, r=0, t=40, b=0),
        clickmode='event',
        title={'text': title_text, 'x': 0.5},
        annotations=[
            dict(
                text='Select one or more LADs in LAD view, then switch to LSOA.',
                x=0.5,
                y=0.5,
                xref='paper',
                yref='paper',
                showarrow=False,
                font=dict(size=14, color='#444'),
                bgcolor='rgba(255,255,255,0.9)',
            )
        ],
    )
    return fig


# drilldown: clicking a LAD toggles it in/out of the selected list
from dash.dependencies import State

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
        if dash.callback_context.triggered
        else None
    )

    #switching back to LAD view clears selection
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

    # current_store is a list of dicts; normalise in case it's legacy format or None
    if not current_store:
        current_store = []
    elif isinstance(current_store, dict):
        current_store = [current_store] if current_store.get('lad_id') else []

    #if lad_name is missing (click came from LSOA polygon), look it up from gdf_lad
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
        # clicking an already-selected LAD (or any LSOA within it) deselects it
        new_store = [s for s in current_store if s['lad_id'] != lad_id]
    else:
        new_store = current_store + [{'lad_id': lad_id, 'lad_name': lad_name}]

    return new_store, no_update


@app.callback(
    Output('geography_selector', 'className'),
    Output('lsoa_switch_hint', 'children'),
    Output('lsoa_switch_hint', 'style'),
    Input('selected_lad_store', 'data'),
    Input('geography_selector', 'value'),
    Input('view_selector', 'value'),
)
def update_lsoa_switch_hint(selected_lads, geography, view):
    base_style = {
        'fontSize': '11px',
        'color': '#666',
        'marginTop': '6px',
        'padding': '6px 8px',
        'background': 'rgba(36,34,111,0.06)',
        'border': '1px solid rgba(36,34,111,0.12)',
        'borderRadius': '8px',
    }

    if view not in ('map', 'compare'):
        return 'nav-radio', 'Tip: LSOA maps load after selecting one or more LADs.', {**base_style, 'display': 'none'}

    if not selected_lads:
        selected_lads = []
    elif isinstance(selected_lads, dict):
        selected_lads = [selected_lads] if selected_lads.get('lad_id') else []

    if geography == 'lad' and selected_lads:
        n = len(selected_lads)
        noun = 'LAD' if n == 1 else 'LADs'
        return (
            'nav-radio lsoa-ready',
            f'{n} {noun} selected. Switch Geography to LSOA to load detailed areas.',
            {**base_style, 'display': 'block'}
        )

    if geography == 'lsoa' and not selected_lads:
        return (
            'nav-radio',
            'Select one or more LADs in LAD view, then switch to LSOA.',
            {**base_style, 'display': 'block'}
        )

    return 'nav-radio', 'Tip: LSOA maps load after selecting one or more LADs.', {**base_style, 'display': 'block'}


# domain opts
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


# single map
@app.callback(
    Output('map_single', 'figure'),
    Input('geography_selector', 'value'),
    Input('dataset_selector', 'value'),
    Input('domain_selector', 'value'),
    Input('view_selector', 'value'),
    Input('lsoa_decile_filter', 'value'),
    Input('lad_rank_filter', 'value'),
    Input('selected_lad_store', 'data'),
)
def update_map(geography, dataset, domain, view, lsoa_decile, lad_percent, selected_lads):
    if view != 'map':
        raise PreventUpdate

    # normalise store
    if not selected_lads:
        selected_lads = []
    elif isinstance(selected_lads, dict):
        selected_lads = [selected_lads] if selected_lads.get('lad_id') else []

    if geography == 'lsoa' and not selected_lads:
        pretty = domain.replace('_', ' ').title()
        return _make_select_lad_figure(
            f"{dataset.upper()} – {pretty} (LSOA)<br><sup style='font-size:11px; color:#888'>LAD selection required</sup>"
        )

    filtered_lsoa = gdf_lsoa.copy()
    filtered_lad = gdf_lad.copy()

    if geography == 'lsoa':
        filtered_lsoa = _filter_lsoa_by_deciles(filtered_lsoa, dataset, domain, lsoa_decile)
        filtered_lsoa = _filter_lsoa_to_selected_lads(filtered_lsoa, selected_lads)

    if geography == 'lad':
        filtered_lad = _filter_lad_by_percent(filtered_lad, dataset, domain, lad_percent)

    lad_rev = '_'.join(sorted(s['lad_id'] for s in selected_lads)) or 'none'
    fig = make_map(
        geography,
        dataset,
        domain,
        filtered_lsoa,
        geojson_lsoa,
        filtered_lad,
        geojson_lad,
        selected_lads=selected_lads,
        show_lad_boundaries=False,
        uirevision=f"{geography}_{lad_rev}",
    )

    if geography == 'lsoa' and selected_lads and hasattr(filtered_lsoa, 'empty') and not filtered_lsoa.empty:
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


# compare maps
@app.callback(
    Output('map_compare_left', 'figure'),
    Output('map_compare_right', 'figure'),
    Input('geography_selector', 'value'),
    Input('domain_selector_ppfi', 'value'),
    Input('domain_selector_imd', 'value'),
    Input('lsoa_decile_filter', 'value'),
    Input('lad_rank_filter', 'value'),
    Input('view_selector', 'value'),
    Input('selected_lad_store', 'data'),
)
def update_compare_maps(geography, domain_ppfi, domain_imd, lsoa_decile, lad_percent, view, selected_lads):
    if not selected_lads:
        selected_lads = []
    elif isinstance(selected_lads, dict):
        selected_lads = [selected_lads] if selected_lads.get('lad_id') else []

    if geography == 'lsoa' and not selected_lads:
        left_title = f"PPFI – {domain_ppfi.replace('_', ' ').title()} (LSOA)<br><sup style='font-size:11px; color:#888'>LAD selection required</sup>"
        right_title = f"IMD – {domain_imd.replace('_', ' ').title()} (LSOA)<br><sup style='font-size:11px; color:#888'>LAD selection required</sup>"
        return _make_select_lad_figure(left_title), _make_select_lad_figure(right_title)

    lsoa_base = gdf_lsoa.copy()
    lad_base = gdf_lad.copy()

    if geography == 'lsoa':
        filtered_lsoa_left = _filter_lsoa_by_deciles(lsoa_base, 'ppfi', domain_ppfi, lsoa_decile)
        filtered_lsoa_right = _filter_lsoa_by_deciles(lsoa_base, 'imd', domain_imd, lsoa_decile)

        filtered_lsoa_left = _filter_lsoa_to_selected_lads(filtered_lsoa_left, selected_lads)
        filtered_lsoa_right = _filter_lsoa_to_selected_lads(filtered_lsoa_right, selected_lads)

        filtered_lad_left = lad_base
        filtered_lad_right = lad_base
    else:
        filtered_lsoa_left = lsoa_base
        filtered_lsoa_right = lsoa_base

        filtered_lad_left = _filter_lad_by_percent(lad_base, 'ppfi', domain_ppfi, lad_percent)
        filtered_lad_right = _filter_lad_by_percent(lad_base, 'imd', domain_imd, lad_percent)

    lad_rev = '_'.join(sorted(s['lad_id'] for s in selected_lads)) or 'none'
    compare_rev = f"compare_{geography}_{lad_rev}"

    left_fig = make_map(
        geography,
        'ppfi',
        domain_ppfi,
        filtered_lsoa_left,
        geojson_lsoa,
        filtered_lad_left,
        geojson_lad,
        compact_hover=True,
        selected_lads=selected_lads,
        show_lad_boundaries=False,
        uirevision=compare_rev,
    )

    right_fig = make_map(
        geography,
        'imd',
        domain_imd,
        filtered_lsoa_right,
        geojson_lsoa,
        filtered_lad_right,
        geojson_lad,
        compact_hover=True,
        selected_lads=selected_lads,
        show_lad_boundaries=False,
        uirevision=compare_rev,
    )

    if geography == 'lsoa' and selected_lads:
        bounds_gdf = filtered_lsoa_left if hasattr(filtered_lsoa_left, 'empty') and not filtered_lsoa_left.empty else filtered_lsoa_right
        if bounds_gdf is not None and hasattr(bounds_gdf, 'empty') and not bounds_gdf.empty:
            try:
                minx, miny, maxx, maxy = bounds_gdf.total_bounds
                center, zoom = _center_zoom_from_bounds((minx, miny, maxx, maxy))
                left_fig.update_layout(mapbox_center=center, mapbox_zoom=zoom)
                right_fig.update_layout(mapbox_center=center, mapbox_zoom=zoom)
            except Exception:
                pass

    pretty_ppfi = domain_ppfi.replace("_"," ").title()
    pretty_imd  = domain_imd.replace("_"," ").title()
    geo_label   = geography.upper()

    if not selected_lads:
        left_fig.update_layout(title=_map_title(f"PPFI – {pretty_ppfi} ({geo_label})", geography))
        right_fig.update_layout(title=_map_title(f"IMD – {pretty_imd} ({geo_label})", geography))
        return left_fig, right_fig

    lad_label = _make_lad_label(selected_lads)
    left_fig.update_layout(title=_map_title(f"PPFI – {pretty_ppfi} ({geo_label}) within {lad_label}", geography))
    right_fig.update_layout(title=_map_title(f"IMD – {pretty_imd} ({geo_label}) within {lad_label}", geography))
    return left_fig, right_fig


#info bar. single map:
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

#info bar. compare maps
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
