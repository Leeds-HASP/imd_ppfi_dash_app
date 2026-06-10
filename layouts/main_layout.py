# layouts/main_layout.py
from dash import dcc, html, dash_table
from components.map_component import maplibre_css, single_map, compare_maps, mismatch_map

# layout constants
NAV_H = "84px"
SIDEBAR_W = "22%"          # keeps percentage width
SIDEBAR_PAD = "18px"       # matches padding
MAIN_PAD_X = "18px"        # horizontal padding for main content
MAIN_PAD_B = "18px"        # bottom padding for main content



layout = html.Div(
    className="app-shell",
    style={
        "minHeight": "100vh",
        "background": "#ffffff",  
        "boxSizing": "border-box",
    },
    children=[
        # navbar
        html.Header(
            className="navbar",
            style={
                "position": "fixed",
                "top": 0,
                "left": 0,
                "right": 0,
                "height": NAV_H,
                "zIndex": 1000,
                "background": "#ffffff",
                "boxSizing": "border-box",
            },
            children=[
                html.Div(
                    [
                        html.Div(
                            "Priority Places for Food Index & Index of Multiple Deprivation: Explorer",
                            className="brand-title",
                        ),
                        html.Div(
                            "Compare vulnerability patterns across England",
                            className="brand-subtitle",
                        ),
                    ]
                ),
                # HASP logo (right side of navbar)
                html.A(
                    html.Img(
                        src="/assets/hasp_logo.png",
                        alt="Healthy and Sustainable Places Data Service",
                        style={
                            "height": "52px",
                            "maxWidth": "160px",
                            "objectFit": "contain",
                        },
                        #fallback text shown if image not found
                        title="Healthy and Sustainable Places Data Service",
                    ),
                    href="https://hasp.ac.uk",
                    target="_blank",
                    rel="noopener noreferrer",
                    **{"aria-label": "Healthy and Sustainable Places Data Service website, opens in a new tab"},
                    style={"display": "flex", "alignItems": "center"},
                ),
            ],
        ),

        maplibre_css(),
        dcc.Store(id="selected_lad_store", data=[]),
        dcc.Store(id="hovered_feature", data=None),
        dcc.Store(id="divergence_selected_lsoa", data=None),
        dcc.Download(id="mismatch_download"),

        # sidebar
        html.Nav(
            className="sidebar",
            **{"aria-label": "Main navigation"},
            style={
                "width": SIDEBAR_W,
                "position": "fixed",
                "top": NAV_H,
                "bottom": 0,
                "left": 0,
                "padding": SIDEBAR_PAD,
                "paddingBottom": "40px",
                "overflowY": "auto",
                "zIndex": 900,
                "boxSizing": "border-box",
                "background": "#ffffff", 
            },
            children=[
                #view selector
                html.Fieldset(
                    className="sidebar-section",
                    style={"border": "1px solid rgba(36,34,111,0.15)", "borderRadius": "14px",
                           "padding": "12px", "marginBottom": "12px", "background": "#ffffff"},
                    children=[
                        html.Legend("View", style={"position": "absolute", "opacity": 0, "pointerEvents": "none", "fontSize": 0}),
                        html.Div("View", className="sidebar-label"),
                        html.Div("Select how to explore the data.", style={"fontSize": "11px", "color": "#888", "marginBottom": "6px"}),
                        dcc.RadioItems(
                            id="view_selector",
                            className="nav-radio",
                            options=[
                                {"label": " About this tool", "value": "about"},
                                {"label": " Index map", "value": "map"},
                                {"label": " PPFI vs IMD comparison", "value": "compare"},
                                {"label": " Differences table", "value": "mismatch"},
                            ],
                            value="about",
                        ),
                    ],
                ),

                #geography selector
                html.Fieldset(
                    id="geography_block",
                    className="sidebar-section",
                    style={"border": "none", "marginBottom": "12px"},
                    children=[
                        html.Legend("Geography", style={"position": "absolute", "opacity": 0, "pointerEvents": "none", "fontSize": 0}),
                        html.Div("Geography", className="sidebar-label"),
                        html.Div("Choose the level of geographic detail.", style={"fontSize": "11px", "color": "#888", "marginBottom": "6px"}),
                        dcc.RadioItems(
                            id="geography_selector",
                            className="nav-radio",
                            options=[
                                {"label": " Lower Super Output Area (LSOA)", "value": "lsoa"},
                                {"label": " Local Authority District (LAD)", "value": "lad"},
                            ],
                            value="lad",
                        ),
                    ],
                ),

                # dataset selector
                html.Fieldset(
                    id="dataset_block",
                    className="sidebar-section",
                    style={"border": "none", "marginBottom": "12px"},
                    children=[
                        html.Legend("Dataset", style={"position": "absolute", "opacity": 0, "pointerEvents": "none", "fontSize": 0}),
                        html.Div("Dataset", className="sidebar-label"),
                        html.Div("Choose which index to display on the map.",
                                 style={"fontSize": "11px", "color": "#888", "marginBottom": "6px"}),
                        dcc.RadioItems(
                            id="dataset_selector",
                            className="nav-radio",
                            options=[
                                {"label": " Priority Places for Food Index", "value": "ppfi"},
                                {"label": " Index of Multiple Deprivation", "value": "imd"},
                            ],
                            value="ppfi",
                        ),
                    ],
                ),

                # domain selector
                html.Details(
                    id="domain_block",
                    className="sidebar-section sidebar-collapsible",
                    **{"aria-label": "Domain"},
                    children=[
                        html.Summary("Domain", className="sidebar-collapsible-summary"),
                        html.Div("Select a specific subdomain or use Combined for an overall score.", style={"fontSize": "11px", "color": "#888", "marginBottom": "6px", "marginTop": "4px"}),
                        dcc.Dropdown(
                            id="domain_selector",
                            value="combined",
                            clearable=False,
                        ),
                    ],
                ),

                # lsoa filter
                html.Details(
                    id="lsoa_decile_filter_block",
                    className="sidebar-section sidebar-collapsible",
                    style={"display": "none"},
                    children=[
                        html.Summary("LSOA decile filter", className="sidebar-collapsible-summary"),
                        html.Div("Filter to show only areas in selected deciles.", style={"fontSize": "11px", "color": "#888", "marginBottom": "6px", "marginTop": "4px"}),
                        dcc.Dropdown(
                            id="lsoa_decile_filter",
                            options=[{"label": f"Decile {i}", "value": i} for i in range(1, 11)],
                            value=[],
                            multi=True,
                            clearable=True,
                            placeholder="Select one or more deciles",
                        ),
                    ],
                ),

                # LAD percentile filter
                html.Details(
                    id="lad_rank_filter_block",
                    className="sidebar-section sidebar-collapsible",
                    style={"display": "none", "paddingBottom": "8px"},
                    children=[
                        html.Summary("LAD rank percentile filter", className="sidebar-collapsible-summary"),
                        html.Div("Show only the top % of most vulnerable local authorities.", style={"fontSize": "11px", "color": "#888", "marginBottom": "6px", "marginTop": "4px"}),
                        html.Div(
                            dcc.Slider(
                                id="lad_rank_filter",
                                min=0,
                                max=100,
                                step=5,
                                value=100,
                                marks={p: f"{p}%" for p in range(0, 101, 20)},
                            ),
                            style={"paddingBottom": "20px"},
                        ),
                    ],
                ),

                # compare domains
                html.Details(
                    id="compare_domains_block",
                    className="sidebar-section sidebar-collapsible",
                    style={"display": "none"},
                    children=[
                        html.Summary("Compare domains", className="sidebar-collapsible-summary"),
                        html.Div("Choose a domain for each index independently.", style={"fontSize": "11px", "color": "#888", "marginBottom": "6px", "marginTop": "4px"}),
                        html.Div("PPFI Domain", style={"fontWeight": 700, "marginTop": "6px"}, id="label-ppfi-domain"),
                        dcc.Dropdown(id="domain_selector_ppfi", value="combined", clearable=False),
                        html.Div("IMD Domain", style={"fontWeight": 700, "marginTop": "12px"}, id="label-imd-domain"),
                        dcc.Dropdown(id="domain_selector_imd", value="combined", clearable=False),
                    ],
                ),

                # mismatch threshold filter
                html.Details(
                    id="mismatch_threshold_block",
                    className="sidebar-section sidebar-collapsible",
                    style={"display": "none"},
                    children=[
                        html.Summary("Mismatch threshold", className="sidebar-collapsible-summary"),
                        html.Div("Show only LSOAs where the absolute decile difference is at or above this value.",
                                 style={"fontSize": "11px", "color": "#888", "marginBottom": "6px", "marginTop": "4px"}),
                        html.Div(
                            dcc.Slider(
                                id="mismatch_threshold_slider",
                                min=0,
                                max=9,
                                step=0.5,
                                value=0,
                                marks={i: str(i) for i in range(10)},
                            ),
                            style={"paddingBottom": "20px"},
                        ),
                    ],
                ),
            ],
        ),

        # main
        html.Main(
            className="main",
            style={
                "marginLeft": SIDEBAR_W,
                "marginTop": NAV_H,
                "paddingLeft": MAIN_PAD_X,
                "paddingRight": MAIN_PAD_X,
                "paddingBottom": MAIN_PAD_B,

                "height": f"calc(100vh - {NAV_H})",
                "display": "flex",
                "flexDirection": "column",
                "minHeight": 0,
                "overflow": "hidden",
                "background": "#ffffff",
                "boxSizing": "border-box",
            },
            children=[

                html.Div(
                    id="map_row",
                    style={
                        "display": "none",
                        "flexDirection": "column",
                        "flex": 1,
                        "minHeight": 0,
                    },
                    children=[
                        #map type toggle
                        html.Div(
                            style={
                                "display": "flex",
                                "gap": "8px",
                                "padding": "6px 14px",
                                "borderBottom": "1px solid var(--border)",
                                "background": "#ffffff",
                                "flexShrink": 0,
                                "alignItems": "center",
                            },
                            children=[
                                html.Span("Map type:", id="map-type-label", style={"fontSize": "12px", "color": "#888", "marginRight": "4px"}),
                                dcc.RadioItems(
                                    id="map_type_selector",
                                    className="nav-radio",
                                    options=[
                                        {"label": " Single index", "value": "single"},
                                        {"label": " Difference map", "value": "mismatch_map"},
                                    ],
                                    value="single",
                                    inline=True,
                                    style={"fontSize": "13px"},
                                ),
                            ],
                        ),
                        html.Div(
                            id="map_container",
                            style={
                                "flex": 1,
                                "display": "flex",
                                "minHeight": 0,
                                "minWidth": 0,
                                "width": "100%",
                                "boxSizing": "border-box",
                            },
                            children=[single_map()],
                        ),
                        # mismatch map panel — replaces map_container in the same flex slot
                        html.Div(
                            id="mismatch_map_panel",
                            style={"display": "none", "flex": 1, "flexDirection": "column", "minHeight": 0, "width": "100%"},
                            children=[mismatch_map()],
                        ),
                        #info bar
                        html.Div(
                            id="map_info_bar",
                            style={
                                "flexShrink": 0,
                                "height": "52px",
                                "padding": "6px 14px",
                                "background": "#f6f7ff",
                                "borderTop": "1px solid var(--border)",
                                "fontSize": "13px",
                                "color": "#444",
                                "lineHeight": "1.4",
                                "overflow": "hidden",
                                "display": "flex",
                                "alignItems": "center",
                            },
                            children=[
                                html.Span(
                                    "Hover over an area to see insight.",
                                    id="map_info_bar_text",
                                    style={"color": "#aaa", "fontStyle": "italic"},
                                )
                            ],
                        ),
                    ],
                ),

                html.Div(
                    id="compare_panel",
                    className="panel-card",
                    style={
                        "display": "none",     
                        "width": "100%",
                        "maxWidth": "none",
                        "flex": 1,              
                        "minHeight": 0,
                        "boxSizing": "border-box",
                        "padding": "16px",
                    },
                    children=[
                        html.H3("Side-by-side comparison", style={"margin": 0}),
                        compare_maps(),
                        # shared info bar below both compare maps
                        html.Div(
                            id="compare_info_bar",
                            style={
                                "flexShrink": 0,
                                "height": "36px",
                                "padding": "6px 14px",
                                "background": "#f6f7ff",
                                "borderTop": "1px solid var(--border)",
                                "fontSize": "13px",
                                "color": "#444",
                                "lineHeight": "1.4",
                                "overflow": "hidden",
                                "display": "flex",
                                "alignItems": "center",
                                "marginTop": "6px",
                            },
                            children=[
                                html.Span(
                                    "Hover over an area to see the name and insight.",
                                    id="compare_info_bar_text",
                                    style={"color": "#aaa", "fontStyle": "italic"},
                                )
                            ],
                        ),
                    ],
                ),

                # mismatch
                html.Div(
                    id="mismatch_panel",
                    style={"display": "none"},
                    children=[
                        html.H3("Differences table: PPFI vs IMD"),
                        html.P(
                            "This explorer identifies neighbourhoods where the Priority Places for Food Index (PPFI) "
                            "and the Index of Multiple Deprivation (IMD) tell different stories. "
                            "A large gap between the two scores can flag areas that are relatively deprived based on IMD but "
                            "have good food access according to PPFI, or areas that appear less deprived based on IMD but face significant food "
                            "vulnerability according to PPFI.",
                            style={"lineHeight": "1.7", "marginBottom": "8px"},
                        ),
                        html.Div(
                            style={
                                "background": "#f6f7ff",
                                "border": "1px solid var(--border)",
                                "borderRadius": "8px",
                                "padding": "10px 16px",
                                "fontSize": "13px",
                                "marginBottom": "16px",
                                "lineHeight": "1.6",
                            },
                            children=[
                                html.Div([
                                    html.Strong("How to use this explorer: "),
                                    "Use the filters below to narrow by local authority, mismatch direction, or minimum "
                                    "decile gap. Select any row in the table to see a full breakdown of PPFI and IMD "
                                    "domain scores for that neighbourhood — the charts and summary appear above the table "
                                    "once a row is selected. Click column headers to sort.",
                                ]),
                                html.Div(
                                    style={"display": "flex", "gap": "16px", "alignItems": "center",
                                           "marginTop": "10px", "flexWrap": "wrap"},
                                    children=[
                                        html.Strong("Row colour key:", style={"fontSize": "12px"}),
                                        html.Span([
                                            html.Span(style={"display": "inline-block", "width": "14px", "height": "14px",
                                                             "background": "#e8f0fb", "border": "1px solid #1d3461",
                                                             "verticalAlign": "middle", "marginRight": "6px"}),
                                            html.Span("IMD more deprived (PPFI − IMD > 2 deciles)",
                                                      style={"fontSize": "12px", "verticalAlign": "middle"}),
                                        ]),
                                        html.Span([
                                            html.Span(style={"display": "inline-block", "width": "14px", "height": "14px",
                                                             "background": "#fdecea", "border": "1px solid #7b1e1e",
                                                             "verticalAlign": "middle", "marginRight": "6px"}),
                                            html.Span("PPFI more deprived (PPFI − IMD < −2 deciles)",
                                                      style={"fontSize": "12px", "verticalAlign": "middle"}),
                                        ]),
                                        html.Span([
                                            html.Strong("Bold", style={"fontSize": "12px", "marginRight": "6px"}),
                                            html.Span("Absolute gap ≥ 5 deciles",
                                                      style={"fontSize": "12px"}),
                                        ]),
                                    ],
                                ),
                            ],
                        ),
                        #domain divergence panel (shown once row selected, above table)
                        html.Div(
                            id="domain_divergence_panel",
                            style={"display": "none"},
                            children=[
                                html.H4(id="domain_divergence_title"),
                                html.Div(id="domain_divergence_narrative"),
                                html.Div(
                                    className="domain-bars-row",
                                    children=[
                                        html.Div(className="domain-bar-col", children=[
                                            html.H5("PPFI domains (decile; 1 = most deprived)"),
                                            dcc.Graph(id="domain_bar_ppfi",
                                                      style={"height": "300px"},
                                                      config={"displayModeBar": False}),
                                        ]),
                                        html.Div(className="domain-bar-col", children=[
                                            html.H5("IMD domains (decile; 1 = most deprived)"),
                                            dcc.Graph(id="domain_bar_imd",
                                                      style={"height": "300px"},
                                                      config={"displayModeBar": False}),
                                        ]),
                                    ],
                                ),
                                html.Hr(style={"borderColor": "#e0e4f0", "margin": "16px 0"}),
                            ],
                        ),
                        #filters + download row
                        html.Div(
                            style={"display": "flex", "gap": "12px", "marginBottom": "10px",
                                   "flexWrap": "wrap", "alignItems": "flex-end"},
                            children=[
                                html.Div([
                                    html.Label("Filter by Local Authority:", htmlFor="mismatch_lad_filter", style={"fontSize": "12px"}),
                                    dcc.Dropdown(
                                        id="mismatch_lad_filter", options=[], value=None,
                                        placeholder="All local authorities",
                                        style={"width": "280px"}, clearable=True,
                                        multi=True,
                                    ),
                                ]),
                                html.Div([
                                    html.Label("Direction:", htmlFor="mismatch_direction_filter", style={"fontSize": "12px"}),
                                    dcc.Dropdown(
                                        id="mismatch_direction_filter",
                                        options=[
                                            {"label": "All",                 "value": "all"},
                                            {"label": "IMD more deprived",   "value": "high_imd"},
                                            {"label": "PPFI more deprived",  "value": "high_ppfi"},
                                            {"label": "Broadly aligned",     "value": "aligned"},
                                        ],
                                        value="all", clearable=False,
                                        style={"width": "200px"},
                                    ),
                                ]),
                                html.Div([
                                    html.Label("Min. decile gap:", htmlFor="mismatch_min_gap", style={"fontSize": "12px", "display": "block", "marginBottom": "4px"}),
                                    dcc.Input(
                                        id="mismatch_min_gap", type="number",
                                        min=0, max=9, step=1, value=None,
                                        placeholder="e.g. 3",
                                        style={"width": "100px"},
                                    ),
                                ]),
                                # download button aligned to bottom of filter row
                                html.Div(
                                    html.Button(
                                        "⬇ Download CSV",
                                        id="mismatch_download_btn",
                                        style={
                                            "background": "var(--brand-navy)",
                                            "color": "#ffffff",
                                            "border": "none",
                                            "borderRadius": "8px",
                                            "padding": "7px 16px",
                                            "fontSize": "13px",
                                            "fontWeight": "600",
                                            "cursor": "pointer",
                                            "fontFamily": "Figtree, system-ui, sans-serif",
                                            "whiteSpace": "nowrap",
                                        },
                                    ),
                                    style={"marginLeft": "auto"},
                                ),
                            ],
                        ),
                        dash_table.DataTable(
                            id="mismatch_table",
                            columns=[], data=[],
                            page_size=20,
                            sort_action="native",
                            filter_action="native",
                            row_selectable="single",
                            selected_rows=[],
                            style_table={"overflowX": "auto"},
                            style_cell={"fontSize": 12, "padding": "6px"},
                            style_header={"fontWeight": "bold"},
                            style_data_conditional=[
                                {"if": {"filter_query": "{ppfi_imd_diff} > 2"},
                                 "backgroundColor": "#e8f0fb", "color": "#1d3461"},
                                {"if": {"filter_query": "{ppfi_imd_diff} < -2"},
                                 "backgroundColor": "#fdecea", "color": "#7b1e1e"},
                                {"if": {"filter_query": "{abs_diff} >= 5"},
                                 "fontWeight": "bold"},
                            ],
                        ),
                    ],
                ),

                #about
                html.Div(
                    id="about_panel",
                    style={"display": "block"},
                    children=[
                        html.H2(
                            "Priority Places for Food Index & Index of Multiple Deprivation Explorer",
                            style={"marginTop": 0, "marginBottom": "4px", "color": "#1a1a2e"},
                        ),
                        html.P(
                            "Two maps, two realities - this tool helps you see where they align and where they don't.",
                            style={"color": "#666", "fontSize": "13px", "marginBottom": "12px"},
                        ),
                        html.P(
                            "Deprivation and food vulnerability don't always affect the same places. "
                            "Two neighbourhoods can look similar on paper yet have completely different everyday realities. "
                            "This tool brings together the PPFI and IMD to make those differences easier to see.",
                            style={"lineHeight": "1.7", "marginBottom": "20px"},
                        ),

                        # index cards 
                        html.Hr(style={"borderColor": "#e0e4f0", "margin": "4px 0 16px 0"}),
                        html.H4("What Each Index Measures", style={"marginBottom": "6px", "color": "#1a1a2e"}),
                        html.Div(
                            style={"display": "flex", "gap": "12px", "marginBottom": "16px", "flexWrap": "wrap"},
                            children=[
                                html.Div(className="info-card info-card--imd", style={"flex": 1, "minWidth": "220px"}, children=[
                                    html.H5("Index of Multiple Deprivation (IMD)", style={"margin": "0 0 6px 0", "color": "#1a1a2e"}),
                                    html.P([html.Strong("Measures: "), "overall neighbourhood disadvantage."], style={"margin": "0 0 6px 0", "fontSize": "13px"}),
                                    html.P(html.Strong("Domains:"), style={"margin": "0 0 2px 0", "fontSize": "13px"}),
                                    html.Ul([
                                        html.Li("Income (22.5%)", style={"fontSize": "12px"}),
                                        html.Li("Employment (22.5%)", style={"fontSize": "12px"}),
                                        html.Li("Education (13.5%)", style={"fontSize": "12px"}),
                                        html.Li("Health (13.5%)", style={"fontSize": "12px"}),
                                        html.Li("Crime (9.3%)", style={"fontSize": "12px"}),
                                        html.Li("Barriers to Housing & Services (9.3%)", style={"fontSize": "12px"}),
                                        html.Li("Living Environment (9.3%)", style={"fontSize": "12px"}),
                                    ], style={"margin": "0 0 8px 0", "paddingLeft": "18px", "lineHeight": "1.7"}),
                                    html.A(
                                        "View full methodology and domain weightings",
                                        href="https://www.gov.uk/government/statistics/english-indices-of-deprivation-2025/english-indices-of-deprivation-2025-statistical-release",
                                        target="_blank",
                                        rel="noopener noreferrer",
                                        **{"aria-label": "IMD full methodology and domain weightings, opens in a new tab"},
                                        style={"color": "var(--brand-green)", "fontSize": "12px"},
                                    ),
                                ]),
                                html.Div(className="info-card info-card--ppfi", style={"flex": 1, "minWidth": "220px"}, children=[
                                    html.H5("Priority Places for Food Index (PPFI)", style={"margin": "0 0 6px 0", "color": "#1a1a2e"}),
                                    html.P([html.Strong("Measures: "), "access to healthy, affordable food."], style={"margin": "0 0 6px 0", "fontSize": "13px"}),
                                    html.P(html.Strong("Domains:"), style={"margin": "0 0 2px 0", "fontSize": "13px"}),
                                    html.Ul([
                                        html.Li("Proximity to supermarket retail facilities (12.5%)", style={"fontSize": "12px"}),
                                        html.Li("Accessibility to supermarket retail facilities (12.5%)", style={"fontSize": "12px"}),
                                        html.Li("Access to online deliveries (12.5%)", style={"fontSize": "12px"}),
                                        html.Li("Proximity to non-supermarket food provision (12.5%)", style={"fontSize": "12px"}),
                                        html.Li("Socio-economic barriers (16.7%)", style={"fontSize": "12px"}),
                                        html.Li("Fuel poverty (16.7%)", style={"fontSize": "12px"}),
                                        html.Li("Need for family food support (16.7%)", style={"fontSize": "12px"}),
                                    ], style={"margin": "0 0 8px 0", "paddingLeft": "18px", "lineHeight": "1.7"}),
                                    html.A(
                                        "View full methodology and domain weightings",
                                        href="https://leeds-hasp.github.io/data-docs/Priority%20Places%20for%20Food%20Index%20V2.1/2_PPFI_user_guide.html",
                                        target="_blank",
                                        rel="noopener noreferrer",
                                        **{"aria-label": "PPFI full methodology and domain weightings, opens in a new tab"},
                                        style={"color": "var(--brand-green)", "fontSize": "12px"},
                                    ),
                                ]),
                            ],
                        ),


                        # how to use
                        html.Hr(style={"borderColor": "#e0e4f0", "margin": "4px 0 16px 0"}),
                        html.H4("How to use this tool", style={"marginBottom": "10px", "color": "#1a1a2e"}),
                        html.Div(
                            className="how-to-accordion",
                            style={"marginBottom": "20px"},
                            children=[
                                html.Details(children=[
                                    html.Summary("Index map", className="accordion-summary"),
                                    html.Div(className="accordion-body", children=[
                                        html.P("Select 'Index map' from the View menu. Choose between a single index view or a differences map using the toggle at the top of the map. Choose PPFI or IMD from the Dataset selector, then a domain or 'Combined' for an overall score across all domains.", style={"fontSize": "13px", "lineHeight": "1.6", "margin": "4px 0"}),
                                        html.P("Click any Local Authority District (LAD) on the map to drill down to Lower Super Output Area (LSOA) level. Click multiple LADs to compare neighbouring areas. Click a selected LAD again to deselect it.", style={"fontSize": "13px", "lineHeight": "1.6", "margin": "4px 0"}),
                                    ]),
                                ]),
                                html.Details(children=[
                                    html.Summary("PPFI vs IMD comparison", className="accordion-summary"),
                                    html.Div(className="accordion-body", children=[
                                        html.P("View both indices side by side. Use the Compare domains panel to choose a domain for each index independently.", style={"fontSize": "13px", "lineHeight": "1.6", "margin": "4px 0"}),
                                        html.P("Both maps respond to the same geography and filter controls so you can compare patterns across the same area simultaneously.", style={"fontSize": "13px", "lineHeight": "1.6", "margin": "4px 0"}),
                                    ]),
                                ]),
                                html.Details(children=[
                                    html.Summary("Differences table", className="accordion-summary"),
                                    html.Div(className="accordion-body", children=[
                                        html.P("Ranks neighbourhoods by the gap between their PPFI and IMD scores, flagging areas where the two indices tell different stories.", style={"fontSize": "13px", "lineHeight": "1.6", "margin": "4px 0"}),
                                        html.P("Filter by local authority, direction of mismatch, or minimum decile gap. Select a row to see a domain-by-domain breakdown in the charts above the table.", style={"fontSize": "13px", "lineHeight": "1.6", "margin": "4px 0"}),
                                    ]),
                                ]),
                                html.Details(children=[
                                    html.Summary("Difference map", className="accordion-summary"),
                                    html.Div(className="accordion-body", children=[
                                        html.P("Select 'Index map' from the View menu, then choose 'Difference map' from the map type toggle.", style={"fontSize": "13px", "lineHeight": "1.6", "margin": "4px 0"}),
                                        html.P([
                                            html.Strong("Absolute difference "),
                                            "is the size of the gap between an area's PPFI decile and IMD decile, regardless of direction. A gap of 5 means the area is in decile 3 on one index and decile 8 on the other. Darker colours indicate a larger gap. Use the Mismatch threshold slider to filter to only the most divergent areas.",
                                        ], style={"fontSize": "13px", "lineHeight": "1.6", "margin": "4px 0"}),
                                        html.P("This view is useful for spotting areas where the two indices tell fundamentally different stories - for example, areas that are highly deprived overall but have relatively good food access, or vice versa.", style={"fontSize": "13px", "lineHeight": "1.6", "margin": "4px 0"}),
                                    ]),
                                ]),
                                html.Details(children=[
                                    html.Summary("Geography levels", className="accordion-summary"),
                                    html.Div(className="accordion-body", children=[
                                        html.P([html.Strong("Two levels of geography are available:",style={"fontSize": "13px", "lineHeight": "1.6", "margin": "4px 0"})]),
                                        html.P([html.Strong("LAD (Local Authority District): "), "local council area level, ranked from 1 (most vulnerable) upwards across England."], style={"fontSize": "13px", "lineHeight": "1.6", "margin": "4px 0"}),
                                        html.P([html.Strong("LSOA (Lower Super Output Area): "), "fine-grained neighbourhood view, deciles 1-10 where 1 = most vulnerable. Click a LAD on the map to drill down, or select LSOA from the Geography panel."], style={"fontSize": "13px", "lineHeight": "1.6", "margin": "4px 0"}),
                                    ]),
                                ]),
                            ],
                        ),

                        # data sources 
                        html.Hr(style={"borderColor": "#e0e4f0", "margin": "4px 0 16px 0"}),
                        html.P(
                            [
                                html.I("Data sources: PPFI V2.1 (Pontin et al. 2024) - English IMD 2025 (MHCLG) - LSOA 2021 and LAD 2024 boundaries (ONS). "),
                                "Full dataset: ",
                                html.A(
                                    "data.hasp.ac.uk/browser/dataset/5276/0",
                                    href="https://data.hasp.ac.uk/browser/dataset/5276/0",
                                    target="_blank",
                                    rel="noopener noreferrer",
                                    **{"aria-label": "PPFI-IMD dataset on HASP data portal, opens in a new tab"},
                                    style={"color": "var(--brand-green)"},
                                ),
                                ".",
                            ],
                            style={"fontSize": "12px", "color": "#888", "marginBottom": "16px"},
                        ),
                        html.H4("Suggested citation", style={"marginBottom": "8px", "color": "#1a1a2e"}),
                        html.Div(
                            style={
                                "background": "#f6f7ff",
                                "border": "1px solid var(--border)",
                                "borderRadius": "8px",
                                "padding": "12px 16px",
                                "fontSize": "13px",
                                "fontStyle": "italic",
                                "color": "#444",
                                "lineHeight": "1.6",
                            },
                            children=[
                                "Sargent, M., Wilkins, E., Jenneson, V., Johnstone, A., Morris, M.A. and Kininmonth, A.R. 2026. ",
                                html.Em("PPFI-IMD Explorer"),
                                ". Data asset provided by the Healthy & Sustainable Places Data Service (ES/Z504336/1). Available at: ",
                                html.A(
                                    "www.hasp.ac.uk",
                                    href="https://hasp.ac.uk",
                                    target="_blank",
                                    rel="noopener noreferrer",
                                    **{"aria-label": "Healthy and Sustainable Places Data Service website, opens in a new tab"},
                                    style={"color": "var(--brand-green)"},
                                ),
                                ".",
                            ],
                        ),
                        html.P(
                            "Please also cite the underlying data: Pontin, F. et al. (2024) PPFI V2.1; "
                            "MHCLG (2025) English Indices of Deprivation 2025.",
                            style={"fontSize": "12px", "color": "#888", "marginTop": "8px"},
                        ),

                        # funding statement
                        html.H4("Funding", style={"marginTop": "20px", "marginBottom": "8px", "color": "#1a1a2e"}),
                        html.P(
                            "This work was part of the FIO-Food project, funded through the "
                            "Transforming the UK Food System for Healthy People and a Healthy Environment "
                            "SPF Programme, delivered by UKRI, in partnership with the Global Food "
                            "Security Programme, BBSRC, ESRC, MRC, NERC, Defra, DHSC, OHID, Innovate UK "
                            "and FSA (FIO-Food award: BB/W018021/1).",
                            style={"fontSize": "12px", "color": "#666", "lineHeight": "1.6"},
                        ),
                    ],
                ),
            ],
        ),
    ],
)
