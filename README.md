# PPFI-IMD Explorer

An interactive web application for visualising and comparing the **Priority Places for Food Index (PPFI)** and the **Index of Multiple Deprivation (IMD)** across England.

Built with [Plotly Dash](https://dash.plotly.com/) and developed by the [Healthy and Sustainable Places (HASP) Data Service](https://hasp.ac.uk).

---

## Overview

The PPFI-IMD Explorer lets researchers, analysts, and policymakers interactively explore deprivation and food vulnerability patterns across England at two geographic levels:

- **LSOA** (Lower Super Output Area): fine-grained, decile-based analysis
- **LAD** (Local Authority District): broader, rank-based analysis

The app has four views:

| View | Description |
|---|---|
| **About this tool** | Background information on the data sources and methodology. |
| **Index map** | Choropleth maps of a single index (PPFI or IMD) by domain, with optional decile/rank filtering. Includes a divergence map showing where the two indices disagree. |
| **PPFI vs IMD Comparison** | Side-by-side comparison of PPFI and IMD domain scores for a selected area. |
| **Explore Differences** | Ranked table and map of LSOAs where PPFI and IMD diverge most strongly, with CSV export. |

---

## Project Structure

```
imd_ppfi_dash_app/
├── app.py                        # Dash app initialisation and callback registration
├── index.py                      # Entry point (runs the dev server)
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Container image definition
├── citation.cff                  # Citation metadata
│
├── assets/
│   ├── styles.css                # App-wide stylesheet (Figtree font, CSS variables)
│   ├── Figtree-Bold.ttf
│   ├── Figtree-Regular.ttf
│   └── hasp_logo.png
│
├── layouts/
│   └── main_layout.py            # Full Dash layout (navbar, sidebar, panels)
│
├── callbacks/
│   ├── navigation_callbacks.py   # View / geography switching logic
│   ├── map_callbacks.py          # Choropleth map rendering and filtering
│   ├── mismatch_callbacks.py     # Mismatch table, chart, and CSV download
│   ├── mismatch_map_callbacks.py # Divergence map rendering
│   └── compare_domain_callbacks.py # Domain comparison charts
│
├── utils/
│   ├── constants.py              # Colour palettes, column names, domain dictionaries
│   ├── data.py                   # Module-level data loading (calls data_loader)
│   └── data_loader.py            # GeoJSON loading, simplification, caching, and merging
│
├── data/
│   ├── ppfi_imd_lsoa_england.geojson   # LSOA-level PPFI + IMD data with geometries
│   ├── ppfi_imd_lad_england.geojson    # LAD-level PPFI + IMD data with geometries
│   ├── imd_ppfi_mismatch.csv           # Pre-computed mismatch scores
│   └── lsoa21_ward_lookup.csv          # LSOA to Ward name lookup
│
└── data_creation/
    ├── imd_ppfi_merge_final.ipynb      # Notebook: merging IMD and PPFI datasets
    ├── ppfi_upscale_final.ipynb        # Notebook: upscaling PPFI to LAD level
    └── README.md
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- GDAL, PROJ, and GEOS system libraries (required by GeoPandas/Fiona)

On Debian/Ubuntu:

```bash
sudo apt-get install gdal-bin libgdal-dev proj-bin libproj-dev libgeos-dev
```

### Installation

```bash
git clone https://github.com/mol-sarg/imd_ppfi_dash_app.git
cd imd_ppfi_dash_app
pip install -r requirements.txt
```

### Running locally

```bash
python index.py
```

The app will be available at `http://localhost:8000`.

> **Note:** On first run the app will simplify and cache the GeoJSON files in `data/cache/`. This takes a minute or two; subsequent starts load from cache and are much faster.

---

## Docker

Build and run the container locally:

```bash
docker build -t imd-ppfi-explorer .
docker run -p 8000:8000 imd-ppfi-explorer
```

The container uses Gunicorn with a single worker and four threads (`--preload` is set to reduce memory usage, which is important when running on Azure).


---

## Data

| File | Description |
|---|---|
| `ppfi_imd_lsoa_england.geojson` | LSOA 2021 boundaries with PPFI deciles (7 domains + combined) and IMD deciles (7 domains + combined) |
| `ppfi_imd_lad_england.geojson` | LAD 2024 boundaries with PPFI and IMD domain ranks |
| `imd_ppfi_mismatch.csv` | Per-LSOA mismatch scores derived from the difference between PPFI and IMD combined deciles |
| `lsoa21_ward_lookup.csv` | ONS lookup from LSOA 2021 codes to ward names |

Source geometries are originally in OSGB36 (EPSG:27700) and are reprojected to WGS84 (EPSG:4326) on first load.

The `data_creation/` notebooks document how the source datasets were merged and how PPFI scores were upscaled from LSOA to LAD level.

---

## Citation

If you use this repository, please cite it as:

```
Sargent, M., Wilkins, E., Jenneson, V., Johnstone, A., Morris, M.A. and Kininmonth, A.R. (2026). PPFI-IMD Explorer. Available from: https://github.com/mol-sarg/imd_ppfi_dash_app
```

A `citation.cff` file is included for automated citation tooling.

---

## Running locally (PMTiles maps)

All three maps (single, compare, mismatch) now render via **MapLibre GL + PMTiles** instead of Plotly. Geometry ships as vector tiles; values ship as a small JSON lookup that the JS layer paints in-place. You need to run a tile-prep step once, then two processes side by side (Dash app + tile server).

### 1. One-off: install tippecanoe

```sh
brew install tippecanoe          # macOS
# Linux: clone https://github.com/felt/tippecanoe and make install
```

### 2. Bake the tiles

```sh
python3 data_creation/prep_pmtiles.py
tippecanoe \
  -o data/pmtiles/england.pmtiles --force \
  -L lad:data/pmtiles/lad.geojson \
  -L lsoa:data/pmtiles/lsoa.geojson \
  -Z 4 -z 14 \
  --coalesce-densest-as-needed \
  --extend-zooms-if-still-dropping \
  --no-tile-compression
```

Outputs land in `data/pmtiles/`. Re-run this whenever the source GeoJSONs or domain columns change. The archive is ~80–150 MB — don't commit it.

### 3. Serve the tiles

```sh
npx serve data/pmtiles -l 8080 --cors
```

`serve` honours HTTP `Range` requests (PMTiles needs them — the client fetches tile byte-ranges out of the archive, not the whole file) and adds CORS headers so the Dash app on port 8000 can read tiles from port 8080. Leave this running in its own terminal.

### 4. Run the app

```sh
python3 index.py
```

Open <http://localhost:8000>.

No Mapbox token is required (MapLibre GL is the open fork). If you swap the tile server for `python -m http.server` you'll need to add CORS headers yourself.
