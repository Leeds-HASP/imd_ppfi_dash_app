import geopandas as gpd

gdf_lsoa = gpd.read_file('data/ppfi_imd_lsoa_england.geojson')
gdf_lad  = gpd.read_file('data/ppfi_imd_lad_england.geojson')

# fix CRS
gdf_lsoa = gdf_lsoa.set_crs(27700, allow_override=True).to_crs(4326)
gdf_lad  = gdf_lad.set_crs(27700, allow_override=True).to_crs(4326)

# simplify
gdf_lsoa.geometry = gdf_lsoa.geometry.simplify(tolerance=0.0005, preserve_topology=True)
gdf_lad.geometry  = gdf_lad.geometry.simplify(tolerance=0.0010, preserve_topology=True)

gdf_lsoa.to_parquet('data/pre_convert/lsoa_simplified.parquet', engine='pyarrow')
gdf_lad.to_parquet('data/pre_convert/lad_simplified.parquet', engine='pyarrow')
