# callbacks/compare_domain_callbacks.py
from dash.dependencies import Input, Output
from dash import callback

from utils.figures import get_domains_for_single

@callback(
    Output('domain_selector_ppfi', 'options'),
    Output('domain_selector_ppfi', 'value'),
    Output('domain_selector_imd', 'options'),
    Output('domain_selector_imd', 'value'),
    Input('view_selector', 'value'),
    Input('geography_selector', 'value'),
    Input('domain_selector_ppfi', 'value'),
    Input('domain_selector_imd', 'value'),
)
def update_compare_domain_options(view, geo, current_ppfi, current_imd):
    if view != 'compare':
        return [], 'combined', [], 'combined'

    ppfi_domains = get_domains_for_single(geo, 'ppfi')
    imd_domains  = get_domains_for_single(geo, 'imd')

    ppfi_opts = [{'label': k.capitalize(), 'value': k} for k in ppfi_domains.keys()]
    imd_opts  = [{'label': k.capitalize(), 'value': k} for k in imd_domains.keys()]

    # keep selections if valid, else default to combined
    ppfi_val = current_ppfi if current_ppfi in ppfi_domains else ('combined' if 'combined' in ppfi_domains else next(iter(ppfi_domains.keys()), None))
    imd_val  = current_imd  if current_imd  in imd_domains  else ('combined' if 'combined' in imd_domains  else next(iter(imd_domains.keys()), None))

    return ppfi_opts, ppfi_val, imd_opts, imd_val
