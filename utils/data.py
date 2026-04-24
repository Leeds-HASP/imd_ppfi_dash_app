
from utils.data_loader import load_all_data

# load base data
gdf_lsoa, geojson_lsoa, gdf_lad, geojson_lad, df_mismatch = load_all_data()

# preserve full, unfiltered datasets
gdf_lsoa_full = gdf_lsoa
gdf_lad_full = gdf_lad
