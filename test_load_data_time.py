import time
t = time.time()
from utils.data import gdf_lsoa, geojson_lsoa, gdf_lad, geojson_lad, df_mismatch
print(f"Data load: {time.time() - t:.2f}s")