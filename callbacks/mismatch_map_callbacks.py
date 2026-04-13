# callbacks/mismatch_map_callbacks.py
import plotly.express as px
from dash import Patch
from dash.dependencies import Input, Output, State
from dash.exceptions import PreventUpdate

from app import app
from utils.data import gdf_lsoa, geojson_lsoa
from utils.constants import PPFI_LSOA_PALETTE
from utils.figures import _first_existing_col

# Diverging scale: dark green (IMD > PPFI) → white (aligned) → dark blue (PPFI > IMD)
DIFF_COLORSCALE = [
    [0.0, '#002d12'],
    [0.5, '#ffffff'],
    [1.0, '#00214d'],
]

# Pre-compute diff and name columns once at startup on the full GDF
_gdf = gdf_lsoa.copy()
_gdf['diff'] = _gdf['pp_dec_combined'] - _gdf['imd_decile']
_gdf['abs_diff'] = _gdf['diff'].abs()
_name_col = _first_existing_col(_gdf, ['LSOA21NM', 'LSOA21NM_x', 'lsoa21nm', 'lsoa_name'])
_gdf['_name'] = _gdf[_name_col] if _name_col else ''

# Pre-build customdata once — name/ppfi/imd/diff are all static
_customdata = _gdf[['_name', 'pp_dec_combined', 'imd_decile', 'diff', 'abs_diff']].values

_HOVERTEMPLATE = (
    "<b>%{customdata[0]}</b><br>"
    "PPFI Decile: <b>%{customdata[1]}</b><br>"
    "IMD Decile: <b>%{customdata[2]}</b><br>"
    "Difference (PPFI \u2212 IMD): <b>%{customdata[3]}</b><br>"
    "Absolute difference: <b>%{customdata[4]}</b>"
    "<extra></extra>"
)


def _z_for_threshold(threshold):
    """Return z array with None for rows below threshold (renders transparent)."""
    return _gdf['diff'].where(_gdf['abs_diff'] >= threshold).tolist()


# ── initial build ─────────────────────────────────────────────────────────────
# Fires when user switches to mismatch_map view. Builds full figure with geometry.

@app.callback(
    Output('mismatch_map', 'figure'),
    Input('view_selector', 'value'),
    State('mismatch_threshold_slider', 'value'),
)
def build_mismatch_map(view, threshold):
    if view != 'mismatch_map':
        raise PreventUpdate

    if threshold is None:
        threshold = 0

    fig = px.choropleth_mapbox(
        _gdf,
        geojson=geojson_lsoa,
        locations='id',
        featureidkey='properties.id',
        color='diff',
        color_continuous_scale=DIFF_COLORSCALE,
        range_color=(-9, 9),
        opacity=0.75,
    )

    fig.update_traces(
        z=_z_for_threshold(threshold),
        customdata=_customdata,
        hovertemplate=_HOVERTEMPLATE,
        marker_line_width=0.01,
    )

    fig.update_layout(
        mapbox=dict(
            style='carto-positron',
            zoom=5.3,
            center={'lat': 53.7, 'lon': -1.5},
        ),
        margin=dict(l=0, r=0, t=40, b=0),
        uirevision='mismatch_map',
        clickmode='event',
        coloraxis_colorbar=dict(
            title='PPFI \u2212 IMD',
            thickness=12,
            len=0.5,
        ),
        title={
            'text': (
                "PPFI vs IMD \u2014 Decile Difference<br>"
                f"<sup style='font-size:11px; color:#888'>"
                f"LSOAs with an absolute gap \u2265 {threshold} shown"
                f"</sup>"
            ),
            'x': 0.5,
        },
        hoverlabel=dict(
            bgcolor="rgba(255,255,255,0.97)",
            bordercolor="rgba(36,34,111,0.2)",
            font_size=13,
            font_color="#1a1a2e",
            font_family="Figtree, system-ui, sans-serif",
            namelength=0,
            align="left",
        ),
        hovermode="closest",
    )

    return fig


# ── threshold patch ───────────────────────────────────────────────────────────
# Only z and the subtitle change when the slider moves — geometry stays in browser.

@app.callback(
    Output('mismatch_map', 'figure', allow_duplicate=True),
    Input('mismatch_threshold_slider', 'value'),
    State('view_selector', 'value'),
    prevent_initial_call=True,
)
def patch_mismatch_map(threshold, view):
    if view != 'mismatch_map':
        raise PreventUpdate

    if threshold is None:
        threshold = 0

    patched = Patch()
    patched['data'][0]['z'] = _z_for_threshold(threshold)
    patched['layout']['title'] = {
        'text': (
            "PPFI vs IMD \u2014 Decile Difference<br>"
            f"<sup style='font-size:11px; color:#888'>"
            f"LSOAs with an absolute gap \u2265 {threshold} shown"
            f"</sup>"
        ),
        'x': 0.5,
    }

    return patched