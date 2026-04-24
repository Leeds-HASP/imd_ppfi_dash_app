# utils/data_loader.py

import json
import os
import hashlib
import pandas as pd
import geopandas as gpd


# cache directory, sits alongside the data folder
_CACHE_DIR = 'data/cache'
_PRE_CONVERT_DIR = 'data/pre_convert'  # during dev, read from here to avoid repeated geometry work

def _source_hash():
    paths = ['data/ppfi_imd_lsoa_england.geojson', 'data/ppfi_imd_lad_england.geojson']
    sig = ''.join(f"{p}:{os.path.getmtime(p)}" for p in paths if os.path.exists(p))
    return hashlib.md5(sig.encode()).hexdigest()[:10]


def _cache_paths(h):
    return {
        'lsoa_geo': os.path.join(_CACHE_DIR, f'lsoa_simplified_{h}.parquet'),
        'lad_geo':  os.path.join(_CACHE_DIR, f'lad_simplified_{h}.parquet'),
    }

def _pre_convert_paths():
    return {
        'lsoa_geo': os.path.join(_PRE_CONVERT_DIR, f'lsoa_simplified.geojson'),
        'lad_geo':  os.path.join(_PRE_CONVERT_DIR, f'lad_simplified.geojson'),
    }


def load_all_data():
    os.makedirs(_CACHE_DIR, exist_ok=True)
    h = _source_hash()
    # paths = _cache_paths(h)
    paths = _pre_convert_paths()  # during dev, read from pre-convert to avoid repeated geometry work

    # load or build simplified GeoJSON
    if os.path.exists(paths['lsoa_geo']) and os.path.exists(paths['lad_geo']):
        print('[data_loader] Loading cached simplified GeoJSON...')
        gdf_lsoa = gpd.read_file(paths['lsoa_geo'])
        gdf_lad  = gpd.read_file(paths['lad_geo'])
    else:
        print('[data_loader] Building simplified GeoJSON (first run — will be cached)...')

        gdf_lsoa = gpd.read_file('data/ppfi_imd_lsoa_england.geojson')
        gdf_lad  = gpd.read_file('data/ppfi_imd_lad_england.geojson')

        # fix CRS
        gdf_lsoa = gdf_lsoa.set_crs(27700, allow_override=True).to_crs(4326)
        gdf_lad  = gdf_lad.set_crs(27700, allow_override=True).to_crs(4326)

        # simplify
        gdf_lsoa.geometry = gdf_lsoa.geometry.simplify(tolerance=0.0001, preserve_topology=True)
        gdf_lad.geometry  = gdf_lad.geometry.simplify(tolerance=0.0003, preserve_topology=True)

        # evict old cache files so the folder doesn't grow indefinitely
        for f in os.listdir(_CACHE_DIR):
            if f.startswith('lsoa_simplified_') or f.startswith('lad_simplified_'):
                os.remove(os.path.join(_CACHE_DIR, f))

        #save.
        gdf_lsoa.to_file(paths['lsoa_geo'], driver='GeoJSON')
        gdf_lad.to_file(paths['lad_geo'],  driver='GeoJSON')
        print('[data_loader] Cache written.')

    # rest of prep (fast. no geometry work)
    df_mismatch = pd.read_csv('data/imd_ppfi_mismatch.csv')

    gdf_lsoa = gdf_lsoa.copy()
    df_mismatch = df_mismatch.copy()

    # normalise keys
    gdf_lsoa['LSOA21CD'] = gdf_lsoa['LSOA21CD'].astype(str).str.strip().str.upper()
    df_mismatch['lsoa21cd'] = df_mismatch['lsoa21cd'].astype(str).str.strip().str.upper()
    df_mismatch['lad24cd']  = df_mismatch['lad24cd'].astype(str).str.strip().str.upper()

    # normalise LSOA name
    if 'LSOA21NM_x' in gdf_lsoa.columns:
        gdf_lsoa['LSOA21NM'] = gdf_lsoa['LSOA21NM_x']

    # merge lad_cd onto gdf_lsoa
    lsoa_to_lad = (
        df_mismatch[['lsoa21cd', 'lad24cd']]
        .dropna(subset=['lsoa21cd', 'lad24cd'])
        .drop_duplicates('lsoa21cd')
        .rename(columns={'lsoa21cd': 'LSOA21CD', 'lad24cd': 'lad_cd'})
    )
    gdf_lsoa = gdf_lsoa.merge(lsoa_to_lad, on='LSOA21CD', how='left')

    # numeric coercion
    for col in gdf_lsoa.columns:
        if col.startswith(('pp_', 'imd_')):
            gdf_lsoa[col] = pd.to_numeric(gdf_lsoa[col], errors='coerce')

    for col in gdf_lad.columns:
        if col.startswith(('combined', 'domain_', 'imd_', 'income_', 'employment_',
                           'education_', 'health_', 'crime_', 'barriers_', 'living_')):
            gdf_lad[col] = pd.to_numeric(gdf_lad[col], errors='coerce')

    # id columns for plotly
    gdf_lsoa['id'] = gdf_lsoa['LSOA21CD'].astype(str)
    gdf_lad['id']  = gdf_lad['LAD24CD'].astype(str).str.strip().str.upper()

    # convert to dict (fast read from cached file, so this is the main cost remaining)
    geojson_lsoa = json.loads(gdf_lsoa.to_json(drop_id=True))
    geojson_lad  = json.loads(gdf_lad.to_json(drop_id=True))

    assert set(gdf_lsoa['id']) == {f['properties']['id'] for f in geojson_lsoa['features']}
    assert set(gdf_lad['id'])  == {f['properties']['id'] for f in geojson_lad['features']}

    # mismatch prep. rebuild scores from latest GeoJSON data
    fresh_scores = gdf_lsoa[['LSOA21CD', 'pp_dec_combined', 'imd_decile']].copy()
    fresh_scores = fresh_scores.rename(columns={'LSOA21CD': 'lsoa21cd'})
    drop_cols = [c for c in ['pp_dec_combined', 'imd_decile', 'ppfi_imd_diff', 'abs_diff']
                 if c in df_mismatch.columns]
    df_mismatch = df_mismatch.drop(columns=drop_cols)
    df_mismatch = df_mismatch.merge(fresh_scores, on='lsoa21cd', how='left')
    df_mismatch['ppfi_imd_diff'] = df_mismatch['pp_dec_combined'] - df_mismatch['imd_decile']
    df_mismatch['abs_diff'] = df_mismatch['ppfi_imd_diff'].abs()
    df_mismatch.sort_values('abs_diff', ascending=False, inplace=True)

    # join ward names
    try:
        ward_lookup = pd.read_csv('data/lsoa21_ward_lookup.csv')
        ward_col = next((c for c in ward_lookup.columns if 'LSOA' in c.upper()), None)
        name_col = next((c for c in ward_lookup.columns if 'WD' in c.upper() and 'NM' in c.upper()), None)
        if ward_col and name_col:
            ward_lookup = (
                ward_lookup[[ward_col, name_col]]
                .rename(columns={ward_col: '_lsoa_key', name_col: 'ward_name'})
            )
            ward_lookup['_lsoa_key'] = ward_lookup['_lsoa_key'].astype(str).str.strip().str.upper()
            ward_lookup = ward_lookup.drop_duplicates('_lsoa_key')
            df_mismatch = df_mismatch.merge(
                ward_lookup, left_on='lsoa21cd', right_on='_lsoa_key', how='left'
            ).drop(columns=['_lsoa_key'])
    except FileNotFoundError:
        df_mismatch['ward_name'] = ''

    return gdf_lsoa, geojson_lsoa, gdf_lad, geojson_lad, df_mismatch