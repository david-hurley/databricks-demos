from dash import html, dcc
import dash_leaflet as dl

# Color palette
COLORS = {
    'dark': '#0B2026',
    'light': '#F9F7F4',
    'border': '#EEEDE9',
    'accent': '#FF3621'
}

# Common styles
FONT = 'DM Sans, sans-serif'
TEXT_STYLE = {'fontFamily': FONT, 'color': COLORS['dark']}
TITLE_STYLE = {**TEXT_STYLE, 'fontWeight': '700'}
CARD_STYLE = {
    'backgroundColor': COLORS['light'],
    'borderRadius': '15px',
    'border': f"1px solid {COLORS['border']}"
}

def create_layout(center_lat, center_lon, markers):
    """Create and return the app layout."""
    return html.Div([
        # Welcome Modal
        html.Div([
            html.Div([
                html.Div([
                    html.H2("Alberta Water Well Explorer", style={**TITLE_STYLE, 'marginBottom': '20px'}),
                    html.P("Find water-bearing formations in Alberta with Databricks Lakebase and PostGIS", 
                           style={**TEXT_STYLE, 'marginBottom': '30px', 'fontSize': '1.1rem'}),
                    html.Div([
                        html.H3("How to Use:", style={**TITLE_STYLE, 'marginBottom': '15px', 'fontSize': '1.2rem'}),
                        html.Ul([
                            html.Li("Use the polygon tool (left side of map) to draw an area of interest"),
                            html.Li("The app will query lithology data within your polygon"),
                            html.Li("View Material vs Depth scatter plot with water-bearing indicators"),
                            html.Li("Blue dots = water-bearing formations, Red dots = non-water-bearing")
                        ], style={**TEXT_STYLE, 'lineHeight': '1.8', 'paddingLeft': '20px'})
                    ]),
                    html.Button("Get Started", id="close-modal", style={
                        'marginTop': '30px',
                        'padding': '12px 30px',
                        'backgroundColor': COLORS['accent'],
                        'color': COLORS['light'],
                        'border': 'none',
                        'borderRadius': '8px',
                        'fontSize': '1rem',
                        'fontWeight': '700',
                        'fontFamily': FONT,
                        'cursor': 'pointer',
                        'width': '100%'
                    })
                ], style={**CARD_STYLE, 'padding': '40px', 'maxWidth': '600px', 'width': '90%', 
                          'boxShadow': '0 20px 60px rgba(11,32,38,0.3)'})
            ], style={
                'position': 'fixed',
                'top': '0',
                'left': '0',
                'width': '100%',
                'height': '100%',
                'backgroundColor': 'rgba(11,32,38,0.8)',
                'display': 'flex',
                'justifyContent': 'center',
                'alignItems': 'center',
                'zIndex': '9999'
            }, id='modal')
        ], id='modal-container'),
        
        # Header
        html.Div([
            html.H1("Alberta Water Well Explorer", style={
                'textAlign': 'center',
                'color': COLORS['light'],
                'fontWeight': '700',
                'fontSize': '2.5rem',
                'fontFamily': FONT
            })
        ], style={
            'padding': '30px 20px 20px 20px',
            'background': COLORS['dark'],
            'borderRadius': '0 0 20px 20px',
            'marginBottom': '30px'
        }),
        
        # Map container
        html.Div([
            dl.Map(center=[center_lat, center_lon], zoom=6, children=[
                dl.TileLayer(),
                dl.LayerGroup(id="well-markers", children=markers),
                dl.FeatureGroup([
                    dl.EditControl(
                        id="edit_control",
                        draw={'polygon': True, 'polyline': False, 'rectangle': False,
                              'circle': False, 'marker': False, 'circlemarker': False},
                        edit=True,
                        position='topleft'
                    )
                ])
            ], style={'width': '100%', 'height': '70vh', **CARD_STYLE}, id='map')
        ], style={'padding': '0 30px', 'marginBottom': '30px'}),
        
        # Results container
        html.Div(id="polygon_output", style={'padding': '0 30px 30px 30px'})
    ], style={
        'fontFamily': FONT,
        'backgroundColor': COLORS['border'],
        'minHeight': '100vh',
        'margin': '0',
        'padding': '0'
    })

