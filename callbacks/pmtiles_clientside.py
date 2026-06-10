# callbacks/pmtiles_clientside.py
from dash import Input, Output
from app import app


def _bridge(mount_id, lookup_id, filter_id, geography_id=None, palette_id=None,
            selected_id=None):
    inputs = [Input(lookup_id, "data"), Input(filter_id, "data")]
    args   = ["lookup", "filter"]
    if geography_id:
        inputs.append(Input(geography_id, "data")); args.append("geography")
    if palette_id:
        inputs.append(Input(palette_id, "data"));   args.append("palette")
    if selected_id:
        inputs.append(Input(selected_id, "data"));  args.append("selected")

    fn_args = ", ".join(args)
    patch_props = ", ".join(f"{a}: {a}" for a in args)
    js = f"""
        function({fn_args}) {{
            if (window.pmtilesPush) window.pmtilesPush('{mount_id}', {{{patch_props}}});
            return window.dash_clientside.no_update;
        }}
    """
    app.clientside_callback(
        js,
        Output(lookup_id, "data", allow_duplicate=True),
        *inputs,
        prevent_initial_call="initial_duplicate",
    )


_bridge("pmtiles_single",
        lookup_id="single_lookup", filter_id="single_filter",
        geography_id="single_geography", palette_id="single_palette",
        selected_id="selected_lad_store")

_bridge("pmtiles_compare_left",
        lookup_id="compare_left_lookup", filter_id="compare_left_filter",
        geography_id="compare_geography",
        selected_id="selected_lad_store")
_bridge("pmtiles_compare_right",
        lookup_id="compare_right_lookup", filter_id="compare_right_filter",
        geography_id="compare_geography",
        selected_id="selected_lad_store")

_bridge("pmtiles_mismatch",
        lookup_id="mismatch_lookup", filter_id="mismatch_filter",
        geography_id="mismatch_geography")


# mirror selected_lad_store onto window for the JS click handler
app.clientside_callback(
    """
    function(data) {
        window.__pmtilesSelectedLads = Array.isArray(data) ? data : [];
        return window.dash_clientside.no_update;
    }
    """,
    Output("selected_lad_store", "data", allow_duplicate=True),
    Input("selected_lad_store", "data"),
    prevent_initial_call="initial_duplicate",
)
