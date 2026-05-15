# callbacks/navigation_callbacks.py
from dash.dependencies import Input, Output
from dash.exceptions import PreventUpdate
from app import app

NAV_H  = "84px"
SIDEBAR_W = "22%"

_PAGE_BASE = {
    "position": "fixed",
    "top": NAV_H,
    "bottom": 0,
    "left": SIDEBAR_W,
    "right": 0,
    "overflowY": "auto",
    "padding": "28px 40px",
    "boxSizing": "border-box",
    "background": "#ffffff",
    "zIndex": 800,
}

show_about    = {**_PAGE_BASE, "display": "block"}
show_mismatch = {**_PAGE_BASE, "display": "block"}
hide_page     = {**_PAGE_BASE, "display": "none"}


@app.callback(
    Output("map_row", "style"),
    Output("compare_panel", "style"),
    Output("mismatch_panel", "style"),
    Output("about_panel", "style"),

    Output("geography_block", "style"),
    Output("dataset_block", "style"),
    Output("domain_block", "style"),
    Output("compare_domains_block", "style"),
    Output("lsoa_decile_filter_block", "style"),
    Output("lad_rank_filter_block", "style"),
    Output("mismatch_threshold_block", "style"),

    Input("view_selector", "value"),
    Input("geography_selector", "value"),
)
def switch_view(view, geo):
    show = {"display": "block"}
    hide = {"display": "none"}

    show_map = {
        "display": "flex",
        "flexDirection": "column",
        "flex": 1,
        "minHeight": 0,
        "minWidth": 0,
    }
    show_compare = {
        "display": "flex",
        "flexDirection": "column",
        "height": "100%",
        "minHeight": 0,
        "minWidth": 0,
        "gap": "10px",
    }

    geography_style = show if view in ["map", "compare"] else hide
    lsoa_filter = show if geo == "lsoa" and view in ["map", "compare"] else hide
    lad_filter  = show if geo == "lad"  and view in ["map", "compare"] else hide

    if view == "map":
        return (
            show_map, hide, hide_page, hide_page,
            geography_style,
            show, show, hide,
            lsoa_filter, lad_filter,
            hide,  # threshold hidden by default; switch_map_type shows it when needed
        )

    if view == "compare":
        return (
            hide, show_compare, hide_page, hide_page,
            geography_style,
            hide, hide, show,
            lsoa_filter, lad_filter,
            hide,
        )

    if view == "mismatch":
        return (
            hide, hide, show_mismatch, hide_page,
            hide, hide, hide, hide,
            hide, hide,
            hide,
        )

    # about (default)
    return (
        hide, hide, hide_page, show_about,
        hide, hide, hide, hide,
        hide, hide,
        hide,
    )


# reset map_type_selector to "single" when leaving map view
@app.callback(
    Output("map_type_selector", "value"),
    Input("view_selector", "value"),
    prevent_initial_call=True,
)
def reset_map_type(view):
    if view != "map":
        return "single"
    raise PreventUpdate


#map type toggle, switches between single index and difference map within map view
@app.callback(
    Output("map_container", "style"),
    Output("mismatch_map_panel", "style"),
    Output("mismatch_threshold_block", "style", allow_duplicate=True),
    Output("geography_block", "style", allow_duplicate=True),
    Output("dataset_block", "style", allow_duplicate=True),
    Output("domain_block", "style", allow_duplicate=True),
    Output("lsoa_decile_filter_block", "style", allow_duplicate=True),
    Output("lad_rank_filter_block", "style", allow_duplicate=True),
    Output("map_info_bar", "style", allow_duplicate=True),
    Input("map_type_selector", "value"),
    Input("view_selector", "value"),
    prevent_initial_call=True,
)
def switch_map_type(map_type, view):
    if view != "map":
        raise PreventUpdate

    show = {"display": "block"}
    hide = {"display": "none"}

    show_container = {
        "flex": 1, "display": "flex", "minHeight": 0,
        "minWidth": 0, "width": "100%", "boxSizing": "border-box",
    }
    show_mismatch_panel = {
        "display": "flex", "flexDirection": "column", "flex": 1, "minHeight": 0, "width": "100%",
    }
    info_bar_style = {
        "flexShrink": 0, "height": "52px", "padding": "6px 14px",
        "background": "#f6f7ff", "borderTop": "1px solid var(--border)",
        "fontSize": "13px", "color": "#444", "lineHeight": "1.4",
        "overflow": "hidden", "display": "flex", "alignItems": "center",
    }

    if map_type == "mismatch_map":
        # Difference map is LSOA-only and driven by its own threshold filter.
        return (
            hide, show_mismatch_panel, show,
            hide, hide, hide, hide, hide,
            {**info_bar_style, "display": "none"},
        )
    else:
        return (
            show_container, hide, hide,
            show, show, show, hide, hide,
            info_bar_style,
        )
