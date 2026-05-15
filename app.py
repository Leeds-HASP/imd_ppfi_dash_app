# app.py
import os
from dash import Dash, html
import dash
from layouts.main_layout import layout

# Tile archive URL — set via env var on Azure (Blob Storage), defaults to a
# local tile server for `python3 index.py` development.
PMTILES_URL = os.environ.get("PMTILES_URL", "http://localhost:8080/england.pmtiles")

app = Dash(
    __name__,
    suppress_callback_exceptions=True,
    index_string=f'''<!DOCTYPE html>
<html lang="en">
    <head>
        {{%metas%}}
        <title>{{%title%}}</title>
        {{%favicon%}}
        {{%css%}}
        <script>window.PMTILES_URL = "{PMTILES_URL}";</script>
    </head>
    <body>
        {{%app_entry%}}
        <footer>
            {{%config%}}
            {{%scripts%}}
            {{%renderer%}}
        </footer>
    </body>
</html>''',
)
app.title = "PPFI-IMD Mismatch Explorer"

# register callbacks
import callbacks.navigation_callbacks
import callbacks.pmtiles_callbacks
import callbacks.pmtiles_clientside
import callbacks.mismatch_callbacks
import callbacks.compare_domain_callbacks

# set layout on import
app.layout = layout
server = app.server
