# callbacks/mismatch_map_callbacks.py
from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate

from app import app
from utils.data import gdf_lsoa, geojson_lsoa
from utils.constants import PPFI_LSOA_PALETTE
from utils.figures import _first_existing_col

# Pre-compute abs_diff and name columns once at startup
_gdf = gdf_lsoa.copy()
_gdf['abs_diff'] = (_gdf['pp_dec_combined'] - _gdf['imd_decile']).abs()
_gdf['ppfi_imd_diff'] = _gdf['pp_dec_combined'] - _gdf['imd_decile']
_name_col = _first_existing_col(_gdf, ['LSOA21NM', 'LSOA21NM_x', 'lsoa21nm', 'lsoa_name'])
_gdf['_name'] = _gdf[_name_col] if _name_col else ''


@app.callback(
    Output('mismatch_map', 'figure'),
    Input('map_type_selector', 'value'),
    Input('mismatch_threshold_slider', 'value'),
)
def update_mismatch_map(map_type, threshold):
    if map_type != 'mismatch_map':
        raise PreventUpdate
    if threshold is None:
        threshold = 0

    filtered = _gdf[_gdf['abs_diff'] >= threshold]
    customdata = filtered[['_name', 'pp_dec_combined', 'imd_decile', 'ppfi_imd_diff', 'abs_diff']].values

    # Properly format the exact hex codes from constants.py to Plotly Dictionary syntax
    colorscale_raw = PPFI_LSOA_PALETTE[::-1]
    n = len(colorscale_raw)
    colorscale = [[i / (n - 1) if n > 1 else 0, c] for i, c in enumerate(colorscale_raw)]

    fig = {
        "data": [{
            "type": "choroplethmapbox",
            "geojson": geojson_lsoa,
            "locations": filtered['id'],
            "z": filtered['abs_diff'],
            "featureidkey": "properties.id",
            "colorscale": colorscale,
            "zmin": 0,
            "zmax": 9,
            "marker": {
                "opacity": 0.75,
                "line": {"width": 0.3}
            },
            "customdata": customdata,
            "hovertemplate": (
                "<b>%{customdata[0]}</b><br>"
                "PPFI Decile: <b>%{customdata[1]}</b><br>"
                "IMD Decile: <b>%{customdata[2]}</b><br>"
                "Absolute difference: <b>%{customdata[4]}</b>"
                "<extra></extra>"
            ),
            "coloraxis": "coloraxis"
        }],
        "layout": {
            "mapbox": {
                "style": "carto-positron",
                "zoom": 5.3,
                "center": {"lat": 53.7, "lon": -1.5},
            },
            "margin": {"l": 0, "r": 0, "t": 40, "b": 0},
            "uirevision": "mismatch_map",
            "clickmode": "event",
            "coloraxis": {
                "colorscale": colorscale,
                "cmin": 0,
                "cmax": 9,
                "colorbar": {
                    "title": "Decile<br>difference",
                    "thickness": 12,
                    "len": 0.5,
                }
            },
            "title": {
                "text": (
                    f"PPFI vs IMD \u2014 Absolute Difference<br>"
                    f"<sup style='font-size:11px; color:#888'>"
                    f"LSOAs with a decile gap \u2265 {threshold}"
                    f"</sup>"
                ),
                "x": 0.5,
            },
            "hoverlabel": {
                "bgcolor": "rgba(255,255,255,0.97)",
                "bordercolor": "rgba(36,34,111,0.2)",
                "font_size": 13,
                "font_color": "#1a1a2e",
                "font_family": "Figtree, system-ui, sans-serif",
                "namelength": 0,
                "align": "left",
            },
            "hovermode": "closest",
        }
    }

    return fig