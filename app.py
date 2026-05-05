# app.py
from dash import Dash, html
import dash
from layouts.main_layout import layout
from pathlib import Path

def load_cookies_html() -> str:
    try:
        return Path("cookies.html").read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    
cookies_html = load_cookies_html()

app = Dash(
    __name__,
    suppress_callback_exceptions=True,
    index_string='''<!DOCTYPE html>
<html lang="en">
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
            __COOKIES_HTML__
        </footer>
    </body>
</html>'''.replace("__COOKIES_HTML__", cookies_html)
)
app.title = "PPFI-IMD Mismatch Explorer"

# register callbacks
import callbacks.navigation_callbacks
import callbacks.map_callbacks
import callbacks.mismatch_callbacks
import callbacks.compare_domain_callbacks
import callbacks.mismatch_map_callbacks

# set layout on import
app.layout = layout
server = app.server
