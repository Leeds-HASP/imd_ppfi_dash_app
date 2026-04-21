# utils/constants.py

# hasp colour palettes
PPFI_LSOA_PALETTE = [
    '#00214d',
    '#003366',
    '#004c8c',
    '#0066a1',
    '#3386b2',
    '#66a6c4',
    '#99c6d7',
    '#cce6e9',
    '#e6f1f4',
    '#ffffff',
]

IMD_LSOA_PALETTE = [
    '#002d12',
    '#00441b',
    '#006d2c',
    '#238b45',
    '#41ab5d',
    '#74c476',
    '#a1d99b',
    '#c7e9c0',
    '#edf8e9',
    '#ffffff',
]


PPFI_LAD_PALETTE = 'Blues_r'
IMD_LAD_PALETTE  = 'Greens_r'


# columns names
LSOA_ID   = 'LSOA21CD'
LSOA_NAME = 'LSOA21NM_x'   

LAD_ID    = 'LAD24CD'
LAD_NAME  = 'LAD24NM_y'    


# domain dictionaries
PPFI_DOMAINS_LSOA = {
    'combined': 'pp_dec_combined',
    'supermarket proximity': 'pp_dec_domain_supermarket_proximity',
    'supermarket accessibility': 'pp_dec_domain_supermarket_accessibility',
    'ecommerce access': 'pp_dec_domain_ecommerce_access',
    'socio-economic barriers': 'pp_dec_domain_socio_demographic',
    'non-supermarket proximity': 'pp_dec_domain_nonsupermarket_proximity',
    'need for family food support': 'pp_dec_domain_food_for_families',
    'fuel poverty': 'pp_dec_domain_fuel_poverty',
}

IMD_DOMAINS_LSOA = {
    'combined': 'imd_decile',
    'income': 'imd_income_decile',
    'employment': 'imd_employment_decile',
    'education': 'imd_education_decile',
    'health': 'imd_health_decile',
    'crime': 'imd_crime_decile',
    'barriers': 'imd_barriers_decile',
    'living environment': 'imd_living_env_decile',
}

PPFI_DOMAINS_LAD = {
    'combined': 'combined',
    'supermarket proximity': 'domain_supermarket_proximity',
    'supermarket accessibility': 'domain_supermarket_accessibility',
    'ecommerce access': 'domain_ecommerce_access',
    'socio-economic barriers': 'domain_socio_demographic',
    'non-supermarket proximity': 'domain_nonsupermarket_proximity',
    'need for family food support': 'domain_food_for_families',
    'fuel poverty': 'domain_fuel_poverty',
}

IMD_DOMAINS_LAD = {
    'combined': 'imd_rank',
    'income': 'income_rank',
    'employment': 'employment_rank',
    'education': 'education_rank',
    'health': 'health_rank',
    'crime': 'crime_rank',
    'barriers': 'barriers_rank',
    'living environment': 'living_env_rank',
}

# Human-readable domain label lists — each entry is (df_column, display_label)
PPFI_LSOA_DOMAIN_LABELS = [
    ("pp_dec_domain_supermarket_proximity",    "Proximity to supermarket retail facilities"),
    ("pp_dec_domain_supermarket_accessibility","Accessibility to supermarket retail facilities"),
    ("pp_dec_domain_ecommerce_access",         "Access to online deliveries"),
    ("pp_dec_domain_socio_demographic",        "Socio-economic barriers"),
    ("pp_dec_domain_nonsupermarket_proximity", "Proximity to non-supermarket food provision"),
    ("pp_dec_domain_food_for_families",        "Need for family food support"),
    ("pp_dec_domain_fuel_poverty",             "Fuel poverty"),
]

IMD_LSOA_DOMAIN_LABELS = [
    ("imd_income_decile",     "Income"),
    ("imd_employment_decile", "Employment"),
    ("imd_education_decile",  "Education"),
    ("imd_health_decile",     "Health"),
    ("imd_crime_decile",      "Crime"),
    ("imd_barriers_decile",   "Barriers to housing & services"),
    ("imd_living_env_decile", "Living environment"),
]
