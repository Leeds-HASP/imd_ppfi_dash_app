# utils/figures.py
import geopandas as gpd
from shapely.geometry import mapping

from utils.constants import (
    PPFI_DOMAINS_LSOA, IMD_DOMAINS_LSOA,
    PPFI_DOMAINS_LAD,  IMD_DOMAINS_LAD,
    PPFI_LSOA_PALETTE, IMD_LSOA_PALETTE,
    PPFI_LAD_PALETTE,  IMD_LAD_PALETTE,
    LSOA_NAME, LAD_NAME,
    PPFI_LSOA_DOMAIN_LABELS,
    IMD_LSOA_DOMAIN_LABELS,
)

from utils.data import gdf_lsoa_full, gdf_lad_full


# helpers
def get_domains_for_single(geo: str, dataset: str):
    if geo == "lsoa" and dataset == "ppfi":
        return PPFI_DOMAINS_LSOA
    if geo == "lsoa" and dataset == "imd":
        return IMD_DOMAINS_LSOA
    if geo == "lad" and dataset == "ppfi":
        return PPFI_DOMAINS_LAD
    return IMD_DOMAINS_LAD


def get_domains_for_compare(geo: str):
    if geo == "lsoa":
        keys = set(PPFI_DOMAINS_LSOA.keys()) | set(IMD_DOMAINS_LSOA.keys())
    else:
        keys = set(PPFI_DOMAINS_LAD.keys()) | set(IMD_DOMAINS_LAD.keys())
    return {k: k for k in sorted(keys)}


def _pick_palette(geo: str, dataset: str):
    # Use the exact custom hex arrays for both LSOA and LAD views
    if dataset == "ppfi":
        return PPFI_LSOA_PALETTE
    return IMD_LSOA_PALETTE

def _pretty_domain(domain_key: str):
    return domain_key.replace("_", " ").strip().title()


def _first_existing_col(gdf, candidates):
    for c in candidates:
        if c in getattr(gdf, "columns", []):
            return c
    return None


def _safe_series(gdf, col_name, default=""):
    if col_name and col_name in gdf.columns:
        return gdf[col_name]
    return default


def _safe(gdf, col):
    return gdf[col] if col and col in gdf.columns else None


def _join_labels(labels):
    if len(labels) == 1: return f"'{labels[0]}'"
    if len(labels) == 2: return f"'{labels[0]}' and '{labels[1]}'"
    return ', '.join(f"'{l}'" for l in labels[:-1]) + f" and '{labels[-1]}'"


def _hover_narrative(row, geography: str, n_lad: int = 0) -> str:
    try:
        diff     = float(row.get('diff') or 0)
        ppfi_val = row.get('ppfi_combined')
        imd_val  = row.get('imd_combined')
    except (TypeError, ValueError):
        return ''
    if ppfi_val is None or imd_val is None:
        return ''

    ppfi_int = int(ppfi_val)
    imd_int  = int(imd_val)
    abs_diff = abs(diff)
    lines    = []

    if geography == 'lsoa':
        if diff > 3:
            lines.append(
                f'IMD decile {imd_int} (1 = most deprived) indicates significantly greater '
                f'deprivation than PPFI decile {ppfi_int} (1 = highest priority) indicates '
                'food vulnerability for this area.'
            )
            ppfi_vals = {col: row[col] for col, _ in PPFI_LSOA_DOMAIN_LABELS if row.get(col) is not None}
            if ppfi_vals:
                best2  = sorted(ppfi_vals.items(), key=lambda x: -x[1])[:2]
                labels = [lbl for col, lbl in PPFI_LSOA_DOMAIN_LABELS if col in dict(best2)]
                if labels:
                    lines.append(
                        f'Relatively better PPFI performance on {_join_labels(labels)} '
                        'may be cushioning the overall PPFI food priority score.'
                    )
            imd_vals = {col: row[col] for col, _ in IMD_LSOA_DOMAIN_LABELS if row.get(col) is not None}
            if imd_vals:
                worst = [lbl for col, lbl in IMD_LSOA_DOMAIN_LABELS
                         if imd_vals.get(col) is not None and imd_vals[col] <= 3]
                if not worst:
                    top2  = sorted(imd_vals.items(), key=lambda x: x[1])[:2]
                    worst = [lbl for col, lbl in IMD_LSOA_DOMAIN_LABELS if col in dict(top2)]
                if worst:
                    lines.append(
                        f'IMD score driven primarily by {_join_labels(worst)}, '
                        'which are distinct from food access indicators.'
                    )

        elif diff < -3:
            lines.append(
                f'PPFI decile {ppfi_int} (1 = highest priority) indicates significantly '
                f'greater food vulnerability than IMD decile {imd_int} (1 = most deprived) '
                'indicates general deprivation for this area.'
            )
            ppfi_vals = {col: row[col] for col, _ in PPFI_LSOA_DOMAIN_LABELS if row.get(col) is not None}
            if ppfi_vals:
                worst = [lbl for col, lbl in PPFI_LSOA_DOMAIN_LABELS
                         if ppfi_vals.get(col) is not None and ppfi_vals[col] <= 3]
                if not worst:
                    top2  = sorted(ppfi_vals.items(), key=lambda x: x[1])[:2]
                    worst = [lbl for col, lbl in PPFI_LSOA_DOMAIN_LABELS if col in dict(top2)]
                if worst:
                    lines.append(
                        f'PPFI score particularly driven by {_join_labels(worst)}, '
                        'reflecting food access challenges not captured by IMD.'
                    )

        elif abs_diff <= 1:
            lines.append(
                f'IMD decile {imd_int} and PPFI decile {ppfi_int} closely agree for this area '
                '(decile 1 = most deprived / highest priority). Both indices tell a consistent story.'
            )

        else:
            if diff > 0:
                lines.append(
                    f'IMD decile {imd_int} (1 = most deprived) indicates more deprivation than '
                    f'PPFI decile {ppfi_int} (1 = highest priority) indicates food vulnerability '
                    f'({abs_diff:.0f} decile gap).'
                )
            else:
                lines.append(
                    f'PPFI decile {ppfi_int} (1 = highest priority) indicates greater food '
                    f'vulnerability than IMD decile {imd_int} (1 = most deprived) indicates '
                    f'general deprivation ({abs_diff:.0f} decile gap).'
                )

    else:
        slight_thr   = max(1, int(round(0.10 * n_lad))) if n_lad else 10
        moderate_thr = max(slight_thr + 1, int(round(0.25 * n_lad))) if n_lad else 25

        if diff > moderate_thr:
            lines.append(
                f'IMD rank {imd_int} (1 = most deprived) indicates significantly greater '
                f'deprivation than PPFI rank {ppfi_int} (1 = highest priority) indicates '
                'food vulnerability for this local authority.'
            )
        elif diff < -moderate_thr:
            lines.append(
                f'PPFI rank {ppfi_int} (1 = highest priority) indicates significantly greater '
                f'food vulnerability than IMD rank {imd_int} (1 = most deprived) indicates '
                'general deprivation for this local authority.'
            )
        elif abs_diff <= slight_thr:
            lines.append(
                f'IMD rank {imd_int} and PPFI rank {ppfi_int} closely agree for this local authority '
                '(rank 1 = most deprived / highest priority).'
            )
        else:
            if diff > 0:
                lines.append(
                    f'IMD rank {imd_int} (1 = most deprived) indicates more deprivation than '
                    f'PPFI rank {ppfi_int} (1 = highest priority) indicates food vulnerability.'
                )
            else:
                lines.append(
                    f'PPFI rank {ppfi_int} (1 = highest priority) indicates greater food '
                    f'vulnerability than IMD rank {imd_int} (1 = most deprived) indicates '
                    'general deprivation.'
                )

    return '<br>'.join(lines)


def _alignment_band(mismatch_value, geography: str, n_lad: int):
    if mismatch_value is None:
        return ""

    try:
        m = int(mismatch_value)
    except Exception:
        return ""

    if m > 0:
        direction = "General deprivation (IMD) is higher than food-related vulnerability (PPFI) for this area."
    elif m < 0:
        direction = "Food-related vulnerability (PPFI) is higher than general deprivation (IMD) for this area."
    else:
        return "Alignment: Both indices closely agree for this area."

    a = abs(m)

    if geography == "lsoa":
        if a == 1:
            return f"Slightly misaligned: {direction}"
        elif a in (2, 3):
            return f"Moderately misaligned: {direction}"
        else:
            return f"Strongly misaligned: {direction}"

    slight_thr = max(1, int(round(0.10 * n_lad)))
    moderate_thr = max(slight_thr + 1, int(round(0.25 * n_lad)))

    if a <= slight_thr:
        return f"Slightly misaligned: {direction}"
    elif a <= moderate_thr:
        return f"Moderately misaligned: {direction}"
    else:
        return f"Strongly misaligned: {direction}"


def add_union_outline_layer(fig, gdf_lsoa_subset, width=3):
    if gdf_lsoa_subset is None or getattr(gdf_lsoa_subset, "empty", True):
        return fig

    try:
        from shapely.ops import unary_union

        geoms = gdf_lsoa_subset.geometry.dropna()
        if geoms.empty:
            return fig

        union_geom = unary_union([g.buffer(0) for g in geoms])

        lons, lats = [], []

        def add_ring(coords):
            for lon, lat in coords:
                lons.append(lon)
                lats.append(lat)
            lons.append(float("nan"))
            lats.append(float("nan"))

        if union_geom.geom_type == "Polygon":
            add_ring(union_geom.exterior.coords)
        elif union_geom.geom_type == "MultiPolygon":
            for poly in union_geom.geoms:
                add_ring(poly.exterior.coords)

        trace = {
            "type": "scattermapbox",
            "lon": lons,
            "lat": lats,
            "mode": "lines",
            "line": {"color": "#24226f", "width": width},
            "hoverinfo": "skip",
            "showlegend": False,
            "name": "",
        }
        fig["data"].append(trace)

    except Exception as e:
        import traceback
        print(f"[add_union_outline_layer] failed: {e}")

    return fig


def make_map(
    geography: str,
    dataset: str,
    domain: str,
    gdf_lsoa, geojson_lsoa,
    gdf_lad, geojson_lad,
    *,
    compact_hover: bool = False,
    selected_lads: list | None = None,
    show_lad_boundaries: bool = False,
    uirevision: str = "keep",
):

    pretty = _pretty_domain(domain)
    metric = "Decile" if geography == "lsoa" else "Rank"

    if geography == "lsoa":
        gdf = gdf_lsoa
        geojson = geojson_lsoa
        dom_ppfi = PPFI_DOMAINS_LSOA.get(domain)
        dom_imd  = IMD_DOMAINS_LSOA.get(domain)
        range_color = (1, 10)
        colorbar_title = "Decile"
        name_col = _first_existing_col(
            gdf, [LSOA_NAME, "LSOA21NM", "LSOA11NM", "lsoa_name", "name"]
        )
    else:
        gdf = gdf_lad
        geojson = geojson_lad
        dom_ppfi = PPFI_DOMAINS_LAD.get(domain)
        dom_imd  = IMD_DOMAINS_LAD.get(domain)

        full_max = None
        if dom_ppfi and dom_ppfi in gdf_lad_full.columns:
            full_max = gdf_lad_full[dom_ppfi].max()

        range_color = (1, full_max) if full_max else None
        colorbar_title = "Rank"
        name_col = _first_existing_col(
            gdf, [LAD_NAME, "LAD24NM", "LAD23NM", "lad_name", "NAME", "name"]
        )

    color_col = dom_ppfi if dataset == "ppfi" else dom_imd
    
    # Format the custom hex arrays into Plotly's continuous scale dictionary syntax
    colorscale_raw = _pick_palette(geography, dataset)
    n = len(colorscale_raw)
    colorscale = [[i / (n - 1) if n > 1 else 0, c] for i, c in enumerate(colorscale_raw)]

    gdf["name"] = _safe_series(gdf, name_col, "")

    if compact_hover:
        gdf["ppfi_val"] = _safe(gdf, dom_ppfi)
        gdf["imd_val"]  = _safe(gdf, dom_imd)

        customdata = gdf[["name", "ppfi_val", "imd_val"]].values

        if domain == "combined":
            hovertemplate = (
                "<b>%{customdata[0]}</b><br>"
                f"Combined {metric}<br>"
                "PPFI: %{customdata[1]}<br>"
                "IMD: %{customdata[2]}<br>"
                "<extra></extra>"
            )
        else:
            if dataset == "ppfi":
                hovertemplate = (
                    "<b>%{customdata[0]}</b><br>"
                    f"{pretty} {metric}<br>"
                    "PPFI: %{customdata[1]}<br>"
                    "<extra></extra>"
                )
            else:
                hovertemplate = (
                    "<b>%{customdata[0]}</b><br>"
                    f"{pretty} {metric}<br>"
                    "IMD: %{customdata[2]}<br>"
                    "<extra></extra>"
                )
    else:
        if geography == "lsoa":
            ppfi_comb = _safe(gdf, "pp_dec_combined")
            imd_comb  = _safe(gdf, "imd_decile")
        else:
            ppfi_comb = _safe(gdf, "combined")
            imd_comb  = _safe(gdf, "imd_rank")

        gdf["ppfi_combined"] = ppfi_comb
        gdf["imd_combined"]  = imd_comb
        if ppfi_comb is not None and imd_comb is not None:
            gdf["diff"] = gdf["ppfi_combined"] - gdf["imd_combined"]
        else:
            gdf["diff"] = None

        if domain != "combined" and color_col in gdf.columns:
            gdf["domain_line"] = f"{pretty} {metric} ({dataset.upper()}): " + gdf[color_col].astype(str)
        else:
            gdf["domain_line"] = ""

        # Convert to dict records once (bypasses pandas Series overhead)
        records = gdf.to_dict('records')
        n_lad = len(gdf_lad_full)
        gdf["narrative"] = [_hover_narrative(r, geography, n_lad) for r in records]

        gdf["_lad_cd"] = _safe_series(gdf, "lad_cd", "")

        customdata = gdf[[
            "name",          
            "ppfi_combined", 
            "imd_combined",  
            "diff",          
            "domain_line",   
            "narrative",     
            "_lad_cd",       
        ]].values

        metric_label = "Decile" if geography == "lsoa" else "Rank"
        hovertemplate = (
            "<b>%{customdata[0]}</b><br>"
            f"<span style='color:#888'>PPFI {metric_label}:</span> <b>%{{customdata[1]}}</b><br>"
            f"<span style='color:#888'>IMD {metric_label}:</span> <b>%{{customdata[2]}}</b><br>"
            f"<span style='color:#888'>Difference:</span> <b>%{{customdata[3]}}</b><br>"
            "%{customdata[4]}"
            "<extra></extra>"
        )

    # Core dictionary representation to bypass Plotly class deepcopy
    fig = {
        "data": [{
            "type": "choroplethmapbox",
            "geojson": geojson,
            "locations": gdf["id"],
            "z": gdf[color_col],
            "featureidkey": "properties.id",
            "colorscale": colorscale,
            "zmin": range_color[0] if range_color else None,
            "zmax": range_color[1] if range_color else None,
            "marker": {
                "opacity": 0.85,
                "line": {
                    "width": 0.5 if geography == "lsoa" else 0.3,
                    "color": "rgba(255,255,255,0.4)" if geography == "lsoa" else "rgba(0,0,0,0.3)"
                }
            },
            "customdata": customdata,
            "hovertemplate": hovertemplate,
            "coloraxis": "coloraxis"
        }],
        "layout": {
            "mapbox": {
                "style": "carto-positron",
                "zoom": 5.3,
                "center": {"lat": 53.7, "lon": -1.5},
                "layers": []
            },
            "margin": {"l": 0, "r": 0, "t": 40, "b": 0},
            "uirevision": uirevision,
            "clickmode": "event",
            "coloraxis": {
                "colorscale": colorscale,
                "cmin": range_color[0] if range_color else None,
                "cmax": range_color[1] if range_color else None,
                "colorbar": {
                    "title": colorbar_title,
                    "thickness": 12,
                    "len": 0.5,
                }
            },
            "title": {
                "text": (
                    f"{dataset.upper()} – {pretty} ({geography.upper()})<br>"
                    f"<sup style='font-size:11px; color:#888'>"
                    f"{'Decile 1 = highest priority' if geography == 'lsoa' else 'Rank 1 = highest priority'}"
                    f"</sup>"
                ),
                "x": 0.5,
            },
            "hoverlabel": {
                "bgcolor": "rgba(255,255,255,0.97)",
                "bordercolor": "rgba(36,34,111,0.3)",
                "font_size": 13,
                "font_color": "#1a1a2e",
                "font_family": "Figtree, system-ui, sans-serif",
                "namelength": 0,
                "align": "left",
            },
            "hovermode": "closest",
        }
    }

    if geography == "lsoa" and selected_lads:
        fig = add_union_outline_layer(fig, gdf_lsoa, width=3)

    if show_lad_boundaries and geojson_lad:
        selected_lads = selected_lads or []
        drilled = bool(selected_lads)
        selected_ids = {s["lad_id"] for s in selected_lads if s.get("lad_id")}

        if drilled:
            lad_bg = gdf_lad_full
            lad_name_col = _first_existing_col(
                lad_bg, [LAD_NAME, "LAD24NM", "LAD23NM", "lad_name", "NAME", "name"]
            )
            lad_bg["name"] = _safe_series(lad_bg, lad_name_col, "")
            lad_bg["_sel"] = lad_bg["id"].isin(selected_ids).astype(int)

            lad_trace = {
                "type": "choroplethmapbox",
                "geojson": geojson_lad,
                "locations": lad_bg["id"],
                "z": lad_bg["_sel"],
                "featureidkey": "properties.id",
                "colorscale": [
                    [0, "rgba(160,160,180,0.08)"],
                    [1, "rgba(100,100,140,0.18)"],
                ],
                "showscale": False,
                "marker": {
                    "line": {"color": "rgba(0,0,0,0)", "width": 0},
                    "opacity": 0,
                },
                "customdata": lad_bg[["name"]].values,
                "hovertemplate": "<b>%{customdata[0]}</b><br>Click to select / deselect<extra></extra>",
                "name": "LAD boundaries",
            }
            fig["data"].insert(0, lad_trace)

            lad_outline_layer = {
                "sourcetype": "geojson",
                "source": geojson_lad,
                "type": "line",
                "color": "#555577",
                "line": {"width": 0.8},
                "opacity": 0.35,
                "below": "",
            }
            fig["layout"]["mapbox"]["layers"].append(lad_outline_layer)

        else:
            lad_layer = {
                "sourcetype": "geojson",
                "source": geojson_lad,
                "type": "line",
                "color": "#1a1a2e",
                "line": {"width": 0.8},
                "opacity": 0.45,
                "below": "",
            }
            fig["layout"]["mapbox"]["layers"].append(lad_layer)

    return fig


def add_highlight_outline(fig, gdf, geojson, feature_id: str):
    return fig