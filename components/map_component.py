"""Map mounts and their per-map dcc.Stores.

Each factory returns a Div the JS in assets/pmtiles_map.js will discover and
turn into a MapLibre map. Stores listed here are populated by
callbacks/pmtiles_callbacks.py and forwarded to JS by pmtiles_clientside.py.
"""
from dash import html, dcc

_MAPLIBRE_CSS = "https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl.css"


def _map_div(map_id, palette, drilldown=False, style=None):
    return html.Div(
        id=map_id,
        className="pmtiles-map",
        style=style or {"flex": 1, "minHeight": 0, "width": "100%"},
        **{
            "data-palette":   palette,
            "data-drilldown": "1" if drilldown else "0",
        },
    )


def maplibre_css():
    """Inject the MapLibre stylesheet once. Place near the top of the layout."""
    return html.Link(rel="stylesheet", href=_MAPLIBRE_CSS)


def single_map():
    return html.Div(
        style={"flex": 1, "display": "flex", "flexDirection": "column",
               "minHeight": 0, "width": "100%"},
        children=[
            _map_div("pmtiles_single", palette="ppfi", drilldown=True),
            dcc.Store(id="single_lookup"),
            dcc.Store(id="single_filter"),
            dcc.Store(id="single_geography"),
            dcc.Store(id="single_palette"),
        ],
    )


def compare_maps():
    return html.Div(
        style={"flex": 1, "display": "flex", "minHeight": 0, "width": "100%", "gap": "4px"},
        children=[
            html.Div(
                style={"flex": 1, "display": "flex", "flexDirection": "column", "minHeight": 0},
                children=[
                    html.Div("PPFI", style={"padding": "4px 8px", "fontSize": "12px",
                                            "background": "#f6f7ff", "borderBottom": "1px solid var(--border)"}),
                    _map_div("pmtiles_compare_left", palette="ppfi", drilldown=True),
                ],
            ),
            html.Div(
                style={"flex": 1, "display": "flex", "flexDirection": "column", "minHeight": 0},
                children=[
                    html.Div("IMD", style={"padding": "4px 8px", "fontSize": "12px",
                                           "background": "#f6f7ff", "borderBottom": "1px solid var(--border)"}),
                    _map_div("pmtiles_compare_right", palette="imd", drilldown=True),
                ],
            ),
            dcc.Store(id="compare_left_lookup"),
            dcc.Store(id="compare_left_filter"),
            dcc.Store(id="compare_right_lookup"),
            dcc.Store(id="compare_right_filter"),
            dcc.Store(id="compare_geography"),
        ],
    )


def mismatch_map():
    return html.Div(
        style={"flex": 1, "display": "flex", "flexDirection": "column",
               "minHeight": 0, "width": "100%"},
        children=[
            _map_div("pmtiles_mismatch", palette="mismatch"),
            dcc.Store(id="mismatch_lookup"),
            dcc.Store(id="mismatch_filter"),
            dcc.Store(id="mismatch_geography"),
        ],
    )
