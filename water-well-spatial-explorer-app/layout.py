from dash import html, dcc
import dash_leaflet as dl


def create_layout(center_lat, center_lon, markers):
    """Create and return the app layout."""
    return html.Div([
        # Welcome Modal
        html.Div([
            html.Div([
                html.Div([
                    html.H2("Alberta Water Well Explorer", style={
                        'color': '#0B2026',
                        'marginBottom': '20px',
                        'fontFamily': 'DM Sans, sans-serif',
                        'fontWeight': '700'
                    }),
                    html.P("Find water-bearing formations in Alberta with Databricks Lakebase and PostGIS", style={
                        'color': '#0B2026',
                        'marginBottom': '30px',
                        'fontSize': '1.1rem',
                        'fontFamily': 'DM Sans, sans-serif'
                    }),
                    html.Div([
                        html.H3("How to Use:", style={
                            'color': '#0B2026',
                            'marginBottom': '15px',
                            'fontSize': '1.2rem',
                            'fontFamily': 'DM Sans, sans-serif',
                            'fontWeight': '700'
                        }),
                        html.Ul([
                            html.Li("Use the polygon tool (left side of map) to draw an area of interest"),
                            html.Li("The app will query lithology data within your polygon"),
                            html.Li("View Material vs Depth scatter plot with water-bearing indicators"),
                            html.Li("Blue dots = water-bearing formations, Red dots = non-water-bearing")
                        ], style={
                            'color': '#0B2026',
                            'lineHeight': '1.8',
                            'fontFamily': 'DM Sans, sans-serif',
                            'paddingLeft': '20px'
                        })
                    ]),
                    html.Button("Get Started", id="close-modal", style={
                        'marginTop': '30px',
                        'padding': '12px 30px',
                        'backgroundColor': '#FF3621',
                        'color': '#F9F7F4',
                        'border': 'none',
                        'borderRadius': '8px',
                        'fontSize': '1rem',
                        'fontWeight': '700',
                        'fontFamily': 'DM Sans, sans-serif',
                        'cursor': 'pointer',
                        'width': '100%',
                        'transition': 'all 0.3s ease'
                    })
                ], style={
                    'backgroundColor': '#F9F7F4',
                    'padding': '40px',
                    'borderRadius': '20px',
                    'maxWidth': '600px',
                    'width': '90%',
                    'boxShadow': '0 20px 60px rgba(11,32,38,0.3)',
                    'border': '2px solid #EEEDE9'
                })
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
                'color': '#F9F7F4',
                'marginBottom': '0',
                'fontWeight': '700',
                'fontSize': '2.5rem',
                'fontFamily': 'DM Sans, sans-serif',
                'letterSpacing': '-0.5px'
            })
        ], style={
            'padding': '30px 20px 20px 20px',
            'background': '#0B2026',
            'borderRadius': '0 0 20px 20px',
            'boxShadow': '0 4px 6px rgba(0,0,0,0.1)',
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
                        draw={'polyline': False, 'polygon': True, 'rectangle': False,
                              'circle': False, 'marker': False, 'circlemarker': False},
                        edit=True,
                        position='topleft'
                    )
                ])
            ], style={
                'width': '100%',
                'height': '70vh',
                'borderRadius': '15px',
                'boxShadow': '0 8px 16px rgba(0,0,0,0.15)',
                'border': '2px solid #e0e0e0'
            }, id='map')
        ], style={
            'padding': '0 30px',
            'marginBottom': '30px'
        }),
        
        # Results container
        html.Div(id="polygon_output", style={
            'padding': '0 30px 30px 30px'
        })
    ], style={
        'fontFamily': 'DM Sans, sans-serif',
        'backgroundColor': '#EEEDE9',
        'minHeight': '100vh',
        'margin': '0',
        'padding': '0'
    })

