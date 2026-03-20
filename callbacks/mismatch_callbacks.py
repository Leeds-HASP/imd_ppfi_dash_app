# callbacks/mismatch_callbacks.py

from dash.dependencies import Input, Output, State
from dash import html, dcc
import pandas as pd
import plotly.graph_objects as go

from app import app
from utils.data import df_mismatch, gdf_lsoa_full
from utils.constants import (
    PPFI_LSOA_DOMAIN_LABELS as PPFI_DOMAIN_COLS,
    IMD_LSOA_DOMAIN_LABELS  as IMD_DOMAIN_COLS,
)

LSOA_CODE_COL = 'lsoa21cd'
LSOA_NAME_COL = 'lsoa21nm'
LAD_NAME_COL  = 'lad24nm'
WARD_NAME_COL = 'ward_name'


# helpers

def _bar_colour(decile):
    try:
        d = float(decile)
    except (TypeError, ValueError):
        return '#bdc3c7'
    if d <= 2:  return '#c0392b'
    if d <= 4:  return '#e67e22'
    return '#27ae60'


def _make_domain_bar(domain_cols, values_dict, composite_decile, composite_label):
    labels     = [lbl for _, lbl in domain_cols]
    cols       = [col for col, _ in domain_cols]
    vals       = [values_dict.get(c) for c in cols]
    colours    = [_bar_colour(v) for v in vals]
    plot_vals  = [v if v is not None else 0 for v in vals]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=plot_vals, y=labels, orientation='h',
        marker_color=colours,
        text=[str(int(v)) if v is not None else 'N/A' for v in vals],
        textposition='outside',
        hovertemplate='%{y}: %{x}<extra></extra>',
    ))

    if composite_decile is not None:
        fig.add_shape(
            type='line',
            x0=composite_decile, x1=composite_decile,
            y0=-0.5, y1=len(labels) - 0.5,
            line=dict(color='#2c3e50', width=2, dash='dash'),
        )
        xanchor = 'left' if composite_decile <= 5.5 else 'right'
        xshift  = 5     if composite_decile <= 5.5 else -5
        fig.add_annotation(
            x=composite_decile, xref='x',
            y=1.0, yref='paper', yanchor='bottom',
            text=f'{composite_label}: {int(composite_decile)}',
            showarrow=True, arrowhead=2, arrowsize=0.8,
            arrowwidth=1.5, arrowcolor='#2c3e50', ay=-18,
            font=dict(size=11, color='#2c3e50'),
            xanchor=xanchor, xshift=xshift,
            bgcolor='rgba(255,255,255,0.9)', borderpad=3,
        )

    fig.update_layout(
        margin=dict(l=10, r=30, t=35, b=20),
        paper_bgcolor='white', plot_bgcolor='white',
        xaxis=dict(range=[0, 10], dtick=1, title='Decile'),
        yaxis=dict(autorange='reversed'),
        showlegend=False, height=300,
    )
    return fig


def _join_labels(labels):
    if len(labels) == 1: return f"'{labels[0]}'"
    if len(labels) == 2: return f"'{labels[0]}' and '{labels[1]}'"
    return ', '.join(f"'{l}'" for l in labels[:-1]) + f" and '{labels[-1]}'"


def _narrative(lsoa_name, ppfi_dec, imd_dec, diff, domain_row):
    paras = []
    ppfi_int = int(ppfi_dec) if ppfi_dec is not None else '?'
    imd_int  = int(imd_dec)  if imd_dec  is not None else '?'

    if diff > 3:
        paras.append(html.P(
            f'{lsoa_name} is significantly more deprived on IMD (decile {imd_int}) '
            f'than on PPFI (decile {ppfi_int}).'
        ))
        ppfi_vals = {col: domain_row.get(col) for col, _ in PPFI_DOMAIN_COLS
                     if domain_row.get(col) is not None}
        if ppfi_vals:
            best2  = sorted(ppfi_vals.items(), key=lambda x: -x[1])[:2]
            labels = [lbl for col, lbl in PPFI_DOMAIN_COLS if col in dict(best2)]
            if labels:
                paras.append(html.P(
                    f"Relatively better PPFI performance on '{labels[0]}'"
                    + (f" and '{labels[1]}'" if len(labels) > 1 else '')
                    + ' may be cushioning the overall PPFI score.'
                ))
        imd_vals = {col: domain_row.get(col) for col, _ in IMD_DOMAIN_COLS
                    if domain_row.get(col) is not None}
        if imd_vals:
            worst = [lbl for col, lbl in IMD_DOMAIN_COLS
                     if imd_vals.get(col) is not None and imd_vals[col] <= 3]
            if not worst:
                top2  = sorted(imd_vals.items(), key=lambda x: x[1])[:2]
                worst = [lbl for col, lbl in IMD_DOMAIN_COLS if col in dict(top2)]
            if worst:
                paras.append(html.P(
                    f'The IMD score is driven primarily by {_join_labels(worst)}'
                    ', which are distinct from food access indicators.'
                ))
        concerns = [lbl for col, lbl in PPFI_DOMAIN_COLS
                    if domain_row.get(col) is not None and domain_row.get(col) <= 3]
        if concerns:
            paras.append(html.P(
                f'However, {_join_labels(concerns)} '
                + ('still scores \u2264 3 on PPFI, indicating a remaining food affordability and access challenges.'
                   if len(concerns) == 1 else
                   'still score \u2264 3 on PPFI, indicating remaining food affordability and access challenges.')
            ))

    elif diff < -3:
        paras.append(html.P(
            f'{lsoa_name} is significantly higher priority on PPFI (decile {ppfi_int}) '
            f'than IMD would predict (decile {imd_int}).'
        ))
        ppfi_vals = {col: domain_row.get(col) for col, _ in PPFI_DOMAIN_COLS
                     if domain_row.get(col) is not None}
        if ppfi_vals:
            worst = [lbl for col, lbl in PPFI_DOMAIN_COLS
                     if ppfi_vals.get(col) is not None and ppfi_vals[col] <= 3]
            if not worst:
                top2  = sorted(ppfi_vals.items(), key=lambda x: x[1])[:2]
                worst = [lbl for col, lbl in PPFI_DOMAIN_COLS if col in dict(top2)]
            if worst:
                paras.append(html.P(
                    f'The PPFI score is particularly driven by {_join_labels(worst)}'
                    ', reflecting food access challenges not captured by the IMD.'
                ))

    elif abs(diff) <= 1:
        paras.append(html.P(
            f'{lsoa_name} shows close alignment between PPFI (decile {ppfi_int}) and '
            f'IMD (decile {imd_int}). Both indices tell a consistent story of vulnerability'
            'for this area.'
        ))

    else:
        direction = 'higher on IMD' if diff > 0 else 'higher on PPFI'
        paras.append(html.P(
            f'{lsoa_name} shows a moderate divergence: {abs(diff):.0f} decile gap, '
            f'with the area ranking {direction} than the other index.'
        ))

    paras.append(html.P(html.I(
        'Decile 1 = most deprived / highest priority. '
        'Domain scores are from PPFI V2.1 and English IMD 2025.'
    )))
    return html.Div(paras, style={
        'background': '#f4f7ff', 'border': '1px solid #ccd6f0',
        'borderLeft': '4px solid #2255aa', 'borderRadius': '6px',
        'padding': '12px 16px', 'fontSize': '13px', 'lineHeight': '1.7',
        'marginBottom': '16px', 'maxWidth': '900px',
    })


def _apply_filters(dff, lad, direction, min_gap):
    if lad and LAD_NAME_COL in dff.columns:
        # lad may be a string (single) or list (multi-select)
        lads = lad if isinstance(lad, list) else [lad]
        dff = dff[dff[LAD_NAME_COL].isin(lads)]
    if direction == 'high_imd':
        dff = dff[dff['ppfi_imd_diff'] > 1]
    elif direction == 'high_ppfi':
        dff = dff[dff['ppfi_imd_diff'] < -1]
    elif direction == 'aligned':
        dff = dff[dff['abs_diff'] <= 1]
    if min_gap and min_gap > 0:
        dff = dff[dff['abs_diff'] >= min_gap]
    return dff


#callbacks

@app.callback(
    Output('mismatch_lad_filter', 'options'),
    Input('view_selector', 'value'),
)
def populate_lad_dropdown(view):
    if view != 'mismatch':
        return []
    if LAD_NAME_COL not in df_mismatch.columns:
        return []
    return [{'label': lad, 'value': lad}
            for lad in sorted(df_mismatch[LAD_NAME_COL].dropna().unique())]


@app.callback(
    Output('mismatch_table', 'columns'),
    Output('mismatch_table', 'data'),
    Input('view_selector', 'value'),
    Input('mismatch_lad_filter', 'value'),
    Input('mismatch_direction_filter', 'value'),
    Input('mismatch_min_gap', 'value'),
)
def mismatch_table(view, lad, direction, min_gap):
    if view != 'mismatch':
        return [], []
    direction = direction or 'all'
    min_gap   = min_gap or 0
    dff = _apply_filters(df_mismatch.copy(), lad, direction, min_gap)

    cols = [
        {'name': 'LSOA code',       'id': LSOA_CODE_COL},
        {'name': 'LSOA name',        'id': LSOA_NAME_COL},
        {'name': 'Ward',             'id': WARD_NAME_COL},
        {'name': 'Local authority',  'id': LAD_NAME_COL},
        {'name': 'PPFI decile',      'id': 'pp_dec_combined',  'type': 'numeric'},
        {'name': 'IMD decile',       'id': 'imd_decile',       'type': 'numeric'},
        {'name': 'PPFI \u2013 IMD',  'id': 'ppfi_imd_diff',    'type': 'numeric'},
        {'name': '|difference|',     'id': 'abs_diff',         'type': 'numeric'},
    ]
    return cols, dff.to_dict('records')


@app.callback(
    Output('divergence_selected_lsoa', 'data'),
    Input('mismatch_table', 'selected_rows'),
    State('mismatch_table', 'data'),
)
def store_selected_lsoa(selected_rows, table_data):
    if selected_rows and table_data:
        return table_data[selected_rows[0]].get(LSOA_CODE_COL)
    return None


@app.callback(
    Output('domain_divergence_panel', 'style'),
    Output('domain_divergence_title', 'children'),
    Output('domain_divergence_narrative', 'children'),
    Output('domain_bar_ppfi', 'figure'),
    Output('domain_bar_imd', 'figure'),
    Input('divergence_selected_lsoa', 'data'),
)
def update_domain_divergence(lsoa_code):
    hide = {'display': 'none'}
    empty = go.Figure()
    empty.update_layout(paper_bgcolor='white', plot_bgcolor='white')

    if not lsoa_code:
        return hide, '', '', empty, empty

    mrow = df_mismatch[df_mismatch[LSOA_CODE_COL] == lsoa_code]
    if mrow.empty:
        return hide, f'No data for {lsoa_code}', '', empty, empty

    mrow      = mrow.iloc[0]
    lsoa_name = mrow[LSOA_NAME_COL]
    ward_name = mrow.get(WARD_NAME_COL) or ''
    lad_name  = mrow[LAD_NAME_COL]
    ppfi_dec  = mrow['pp_dec_combined']
    imd_dec   = mrow['imd_decile']
    diff      = mrow['ppfi_imd_diff']

    grow       = gdf_lsoa_full[gdf_lsoa_full['LSOA21CD'] == lsoa_code]
    domain_row = grow.iloc[0].to_dict() if not grow.empty else {}

    display_name = f'{ward_name} ({lsoa_name})' if ward_name else lsoa_name
    title = (
        f'{display_name}, {lad_name} \u2014 '
        f'PPFI decile {int(ppfi_dec)}, IMD decile {int(imd_dec)}, '
        f'difference {int(diff):+d}'
    )

    narrative = _narrative(display_name, ppfi_dec, imd_dec, diff, domain_row)

    ppfi_vals = {col: domain_row.get(col) for col, _ in PPFI_DOMAIN_COLS}
    imd_vals  = {col: domain_row.get(col) for col, _ in IMD_DOMAIN_COLS}

    fig_ppfi = _make_domain_bar(PPFI_DOMAIN_COLS, ppfi_vals, ppfi_dec, 'PPFI composite decile')
    fig_imd  = _make_domain_bar(IMD_DOMAIN_COLS,  imd_vals,  imd_dec,  'IMD composite decile')

    return {'display': 'block'}, title, narrative, fig_ppfi, fig_imd



@app.callback(
    Output("mismatch_download", "data"),
    Input("mismatch_download_btn", "n_clicks"),
    State("mismatch_lad_filter", "value"),
    State("mismatch_direction_filter", "value"),
    State("mismatch_min_gap", "value"),
    prevent_initial_call=True,
)
def download_mismatch_csv(n_clicks, lad, direction, min_gap):
    if not n_clicks:
        from dash.exceptions import PreventUpdate
        raise PreventUpdate

    direction = direction or "all"
    min_gap   = min_gap or 0
    dff = _apply_filters(df_mismatch.copy(), lad, direction, min_gap)

    # build a readable filename based on current filters
    parts = ["IMD_PPFI_Explorer_mismatch"]
    if lad:
        lads = lad if isinstance(lad, list) else [lad]
        if len(lads) == 1:
            parts.append(lads[0].replace(" ", "_"))
        else:
            parts.append(f"{len(lads)}_local_authorities")
    if direction != "all":
        parts.append(direction)
    filename = "_".join(parts) + ".csv"

    return dcc.send_data_frame(dff.to_csv, filename, index=False)
