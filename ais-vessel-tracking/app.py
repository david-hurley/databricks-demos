"""H3 Vessel Activity Visualization - Clean & Simple"""
import os
import time
import uuid
import pandas as pd
import numpy as np
import h3
import psycopg
from psycopg_pool import ConnectionPool
from databricks.sdk import WorkspaceClient
import dash
from dash import html, dcc, Input, Output, State
import dash_leaflet as dl

# ============================================================================
# CONFIG
# ============================================================================
SCHEMA = "david_hurley"
TABLE = "ais_records_curated_pg"
RESOLUTION = 7
LIMIT = 5000

COLORS = ['#FFE082', '#FFB74D', '#FF9800', '#F57C00', '#E65100', '#D84315', '#BF360C']
BREAKS = np.array([1, 17, 33, 50, 67, 83, 100])

# ============================================================================
# DATABASE CONNECTION
# ============================================================================
workspace_client = WorkspaceClient()
postgres_password = None
last_password_refresh = 0
connection_pool = None

def refresh_oauth_token():
    """Refresh OAuth token if expired."""
    global postgres_password, last_password_refresh
    if postgres_password is None or time.time() - last_password_refresh > 900:
        try:
            # In-app authentication
            postgres_password = workspace_client.config.oauth_token().access_token
        except:
            # Fallback to local authentication
            postgres_password = workspace_client.database.generate_database_credential(
                request_id=str(uuid.uuid4()),
                instance_names=[os.getenv("INSTANCE_NAME", "yyc-data-meet")]
            ).token
        last_password_refresh = time.time()
    return True

def get_connection_pool():
    """Get or create the connection pool."""
    global connection_pool
    if connection_pool is None:
        refresh_oauth_token()
        
        # Get current user
        try:
            user = workspace_client.current_user.me().user_name
        except:
            user = os.getenv("PGUSER", "david.hurley@databricks.com")
        
        conn_string = (
            f"dbname={os.getenv('PGDATABASE', 'users')} "
            f"user={user} "
            f"password={postgres_password} "
            f"host={os.getenv('PGHOST', 'instance-6924fe4e-f240-46f0-876d-69ff7f6e5c84.database.azuredatabricks.net')} "
            f"port={os.getenv('PGPORT', '5432')} "
            f"sslmode={os.getenv('PGSSLMODE', 'require')} "
        )
        connection_pool = ConnectionPool(conn_string, min_size=2, max_size=10)
        print(f"Connection pool created for user: {user}")
    return connection_pool

def get_connection():
    """Get a connection from the pool."""
    global connection_pool
    
    if postgres_password is None or time.time() - last_password_refresh > 900:
        if connection_pool:
            connection_pool.close()
            connection_pool = None
    
    return get_connection_pool().connection()

def execute_sql(sql: str) -> pd.DataFrame:
    """Execute SQL query and return DataFrame."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            if cur.description is None:
                return pd.DataFrame()
            cols = [d.name for d in cur.description]
            rows = cur.fetchall()
    return pd.DataFrame(rows, columns=cols)

# ============================================================================
# DATA QUERIES
# ============================================================================
def get_hours():
    query = f'SELECT DISTINCT hour_ts FROM "{SCHEMA}"."{TABLE}" WHERE resolution = {RESOLUTION} ORDER BY hour_ts'
    return execute_sql(query)['hour_ts'].tolist()

def get_data(hour):
    query = f"""
        SELECT h3_cell, ship_count as count
        FROM "{SCHEMA}"."{TABLE}"
        WHERE resolution = {RESOLUTION} AND hour_ts = '{hour}'
        ORDER BY count DESC LIMIT {LIMIT}
    """
    return execute_sql(query)

# ============================================================================
# UTILS
# ============================================================================
def get_color(count):
    for i in range(len(BREAKS) - 1, 0, -1):
        if count >= BREAKS[i]:
            return COLORS[min(i, len(COLORS) - 1)]
    return COLORS[0]

def format_num(n):
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    elif n >= 1_000:
        return f"{n/1_000:.0f}K"
    return str(int(n))

def gradient(c1, c2):
    return f"linear-gradient(135deg, {c1} 0%, {c2} 100%)"

def create_polygon(h3_cell, count):
    try:
        h3_hex = hex(h3_cell)[2:]
        boundary = h3.cell_to_boundary(h3_hex)
        coords = [[lat, lng] for lat, lng in boundary]
        color = get_color(count)
        
        return dl.Polygon(
            positions=coords,
            fillColor=color,
            color=color,
            weight=1,
            opacity=0.8,
            fillOpacity=0.6,
            children=dl.Tooltip(f"Ships: {int(count):,}")
        )
    except:
        return None

# ============================================================================
# UI COMPONENTS
# ============================================================================
def create_legend():
    items = []
    for i in range(len(BREAKS) - 1):
        lower, upper = int(BREAKS[i]), int(BREAKS[i+1])
        label = f"{format_num(lower)}–{format_num(upper)}" if i < len(BREAKS) - 2 else f"≥ {format_num(lower)}"
        
        items.append(
            html.Div([
                html.Div(style={
                    "background": gradient(COLORS[i], COLORS[min(i+1, len(COLORS)-1)]),
                    "width": "48px", "height": "32px", "borderRadius": "6px",
                    "boxShadow": f"0 4px 12px {COLORS[i]}40, inset 0 1px 0 rgba(255,255,255,0.2)"
                }),
                html.Span(label, style={"color": "#FFF", "fontSize": "14px", "fontWeight": "500"})
            ], style={"display": "flex", "alignItems": "center", "marginBottom": "14px"}, className="legend-item")
        )
    
    return html.Div([
        html.Div([
            html.I(className="fas fa-layer-group", style={
                "fontSize": "20px", "marginRight": "12px",
                "background": gradient("#667eea", "#764ba2"),
                "WebkitBackgroundClip": "text", "WebkitTextFillColor": "transparent"
            }),
            html.Span("Ship Density", style={
                "fontSize": "18px", "fontWeight": "700",
                "background": gradient("#FFF", "#E0E0E0"),
                "WebkitBackgroundClip": "text", "WebkitTextFillColor": "transparent"
            })
        ], style={"display": "flex", "alignItems": "center"}),
        html.Hr(style={"border": "none", "borderTop": "1px solid rgba(255,255,255,0.08)", "margin": "16px 0"}),
        html.Div(items)
    ], style={
        "position": "absolute", "top": "24px", "right": "24px", "zIndex": "1000",
        "background": gradient("rgba(20,20,25,0.98)", "rgba(30,30,35,0.98)"),
        "padding": "28px 26px", "borderRadius": "16px", "minWidth": "260px",
        "boxShadow": "0 20px 60px rgba(0,0,0,0.6), 0 0 1px rgba(255,255,255,0.15), inset 0 1px 0 rgba(255,255,255,0.05)",
        "border": "1px solid rgba(255,255,255,0.08)", "backdropFilter": "blur(20px)"
    })

# ============================================================================
# INIT
# ============================================================================
hours = get_hours()
current_idx = [0]
initial_data = get_data(hours[0])

if len(initial_data) > 0:
    try:
        h3_hex = hex(initial_data.iloc[0]['h3_cell'])[2:]
        center = h3.cell_to_boundary(h3_hex)[0]
        center_lat, center_lng = center[0], center[1]
    except:
        center_lat, center_lng = 0, 0
else:
    center_lat, center_lng = 0, 0

initial_polygons = [create_polygon(row['h3_cell'], row['count']) for _, row in initial_data.iterrows()]
initial_polygons = [p for p in initial_polygons if p is not None]

# Slider marks
marks = {
    i: {"label": str(hours[i])[:13], "style": {"fontSize": "10px", "color": "#888"}}
    for i in range(0, len(hours), max(1, len(hours) // 10))
}

# ============================================================================
# APP
# ============================================================================
app = dash.Dash(__name__, external_stylesheets=[
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
    'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap'
])

app.index_string = '''<!DOCTYPE html>
<html>
<head>{%metas%}<title>H3 Vessel Activity</title>{%favicon%}{%css%}
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }
.rc-slider-rail { background: rgba(255,255,255,0.1); height: 6px; border-radius: 3px; }
.rc-slider-track { background: linear-gradient(90deg, #667eea 0%, #764ba2 100%); height: 6px; border-radius: 3px; }
.rc-slider-handle { width: 20px; height: 20px; margin-top: -7px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border: 3px solid #fff; box-shadow: 0 4px 12px rgba(102,126,234,0.4); transition: all 0.2s ease; }
.rc-slider-handle:hover { transform: scale(1.15); box-shadow: 0 6px 20px rgba(102,126,234,0.6); }
.rc-slider-mark-text { color: #888; font-size: 12px; font-weight: 500; }
.legend-item:hover { transform: translateX(4px); }
</style>
</head>
<body>{%app_entry%}<footer>{%config%}{%scripts%}{%renderer%}</footer></body>
</html>'''

app.layout = html.Div([
    # Header
    html.Div([
        html.Div([
            html.I(className="fas fa-ship", style={
                "fontSize": "32px", "marginRight": "16px",
                "background": gradient("#4FC3F7", "#29B6F6"),
                "WebkitBackgroundClip": "text", "WebkitTextFillColor": "transparent",
                "filter": "drop-shadow(0 2px 4px rgba(79,195,247,0.3))"
            }),
            html.Div([
                html.Div("H3 Vessel Activity", style={
                    "fontSize": "32px", "fontWeight": "700", "letterSpacing": "-0.5px",
                    "background": gradient("#FFF", "#B0BEC5"),
                    "WebkitBackgroundClip": "text", "WebkitTextFillColor": "transparent"
                }),
                html.Div("Real-time Maritime Intelligence", style={
                    "fontSize": "13px", "color": "#78909C", "fontWeight": "500", "marginTop": "2px"
                })
            ])
        ], style={"display": "flex", "alignItems": "center", "maxWidth": "1600px", "margin": "0 auto", "padding": "0 40px"})
    ], style={
        "background": gradient("#0f2027", "#2c5364"),
        "padding": "32px 0",
        "boxShadow": "0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.05)",
        "borderBottom": "1px solid rgba(255,255,255,0.1)"
    }),
    
    # Play Button & Slider
    html.Div([
        html.Div([
            html.Button(
                html.I(className="fas fa-play", id="play-icon"),
                id="play-button",
                style={
                    "background": gradient("#667eea", "#764ba2"),
                    "border": "none",
                    "borderRadius": "50%",
                    "width": "48px",
                    "height": "48px",
                    "color": "#FFF",
                    "fontSize": "18px",
                    "cursor": "pointer",
                    "boxShadow": "0 4px 12px rgba(102, 126, 234, 0.4)",
                    "transition": "all 0.2s ease",
                    "marginRight": "24px"
                }
            ),
            html.Div([
                dcc.Slider(
                    id="time-slider",
                    min=0,
                    max=len(hours) - 1,
                    value=0,
                    marks=marks,
                    step=None,
                    tooltip=None
                )
            ], style={"flex": "1"})
        ], style={"display": "flex", "alignItems": "center"}),
        dcc.Interval(id="interval", interval=1000, n_intervals=0, disabled=True)
    ], style={
        "background": gradient("#1a1f2e", "#252b3b"),
        "padding": "20px 40px",
        "boxShadow": "0 4px 20px rgba(0,0,0,0.3)",
        "borderBottom": "1px solid rgba(255,255,255,0.05)",
        "maxWidth": "1600px", "margin": "0 auto"
    }),
    
    # Map
    html.Div([
        dl.Map(
            id="map", center=[center_lat, center_lng], zoom=6,
            style={"width": "100%", "height": "calc(100vh - 155px)"},
            children=[
                dl.TileLayer(url="https://cartodb-basemaps-{s}.global.ssl.fastly.net/dark_all/{z}/{x}/{y}.png"),
                dl.LayerGroup(id="hex-layer", children=initial_polygons)
            ]
        ),
        create_legend()
    ], style={"position": "relative"})
], style={"backgroundColor": "#0d0d0d", "minHeight": "100vh"})

# ============================================================================
# CALLBACKS
# ============================================================================
@app.callback(
    Output("hex-layer", "children"),
    Input("time-slider", "value")
)
def update_map(idx):
    data = get_data(hours[idx])
    polygons = [create_polygon(row['h3_cell'], row['count']) for _, row in data.iterrows()]
    return [p for p in polygons if p is not None]

@app.callback(
    [Output("interval", "disabled"), Output("play-icon", "className")],
    Input("play-button", "n_clicks"),
    State("interval", "disabled"),
    prevent_initial_call=True
)
def toggle_play(n, paused):
    return (False, "fas fa-pause") if paused else (True, "fas fa-play")

@app.callback(
    Output("time-slider", "value"),
    Input("interval", "n_intervals"),
    State("time-slider", "value"),
    prevent_initial_call=True
)
def advance(n, current):
    return (current + 1) % len(hours)

# ============================================================================
# RUN
# ============================================================================
if __name__ == "__main__":
    app.run(debug=True)
