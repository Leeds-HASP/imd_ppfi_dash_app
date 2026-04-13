# app.py
from dash import Dash, html
import dash
from layouts.main_layout import layout

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
        </footer>
    </body>
</html>''',
)

# register callbacks
import callbacks.navigation_callbacks
import callbacks.map_callbacks
import callbacks.mismatch_callbacks
import callbacks.compare_domain_callbacks
import callbacks.mismatch_map_callbacks

# set layout on import
app.layout = layout
server = app.server
sfd