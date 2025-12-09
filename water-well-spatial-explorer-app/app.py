import dash
from dash import html, dcc
import dash_leaflet as dl
from dash.dependencies import Input, Output, State
import plotly.express as px
import time
from databricks.sdk import WorkspaceClient
from config import instance_name, database, schema, well_table, lithology_table
from utils import build_pool, execute_sql, query_points_in_polygon
from layout import create_layout

connection_pool = None

w = WorkspaceClient()

user = w.current_user.me().user_name
host = w.database.get_database_instance(name=instance_name).read_write_dns

# Check if Lakebase Postgres connection pool exists, if not create one
if connection_pool is None:
    connection_pool = build_pool(instance_name, host, user, database, w)

# query 10k random wells to improve map rendering and query performance
query_wells = f"SELECT * FROM {schema}.{well_table} ORDER BY RANDOM() LIMIT 10000"
df_wells = execute_sql(connection_pool, query_wells)

df_well_coords = df_wells[['Latitude', 'Longitude']].dropna()

center_lat = df_well_coords["Latitude"].median()
center_lon = df_well_coords["Longitude"].median()

markers = [
    dl.CircleMarker(
        center=[row["Latitude"], row["Longitude"]],
        radius=3,
        color='#3498db',
        fillColor='#5dade2',
        fillOpacity=0.6,
        weight=1
    ) for _, row in df_well_coords.iterrows()
]

app = dash.Dash(__name__, external_stylesheets=[
    'https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;700&display=swap'
])

app.layout = create_layout(center_lat, center_lon, markers)


@app.callback(
    Output("modal-container", "style"),
    Input("close-modal", "n_clicks"),
    prevent_initial_call=True
)
def close_modal(n_clicks):
    return {'display': 'none'}


@app.callback(
    Output("polygon_output", "children"),
    Input("edit_control", "geojson")
)
def handle_polygon(poly_json):
    if not poly_json:
        return html.Div([
            html.Div("Draw a polygon on the map to query wells", style={
                'textAlign': 'center',
                'color': '#0B2026',
                'padding': '40px',
                'fontSize': '1.1rem',
                'fontFamily': 'DM Sans, sans-serif',
                'backgroundColor': '#F9F7F4',
                'borderRadius': '15px',
                'boxShadow': '0 2px 8px rgba(11,32,38,0.1)',
                'border': '1px solid #EEEDE9'
            })
        ])
    
    try:
        # Extract polygon coordinates from GeoJSON
        features = poly_json.get('features', [])
        if not features:
            return html.Div("No polygon drawn", style={
                'textAlign': 'center', 'color': '#0B2026', 'padding': '40px',
                'backgroundColor': '#F9F7F4', 'borderRadius': '15px',
                'boxShadow': '0 2px 8px rgba(11,32,38,0.1)',
                'fontFamily': 'DM Sans, sans-serif', 'border': '1px solid #EEEDE9'
            })
        
        # Get the last polygon (if multiple exist, use the most recent)
        feature = features[-1]
        geometry = feature.get('geometry', {})
        
        if geometry.get('type') != 'Polygon':
            return html.Div("Please draw a polygon", style={
                'textAlign': 'center', 'color': '#0B2026', 'padding': '40px',
                'backgroundColor': '#F9F7F4', 'borderRadius': '15px',
                'boxShadow': '0 2px 8px rgba(11,32,38,0.1)',
                'fontFamily': 'DM Sans, sans-serif', 'border': '1px solid #EEEDE9'
            })
        
        # Get coordinates - GeoJSON format is [[[lon, lat], [lon, lat], ...]]
        coords = geometry.get('coordinates', [[]])[0]
        
        if len(coords) < 3:
            return html.Div("Polygon must have at least 3 points", style={
                'textAlign': 'center', 'color': '#0B2026', 'padding': '40px',
                'backgroundColor': '#F9F7F4', 'borderRadius': '15px',
                'boxShadow': '0 2px 8px rgba(11,32,38,0.1)',
                'fontFamily': 'DM Sans, sans-serif', 'border': '1px solid #EEEDE9'
            })
                
        # Query database for points in polygon using PostGIS ST_Contains
        result_df = query_points_in_polygon(connection_pool, schema, lithology_table, coords)
        
        # Filter out rows with missing Material or Depth, but keep Water_Bearing
        plot_df = result_df[["Material_Category", "Depth_Of_Material", "Water_Bearing"]].dropna(subset=["Material_Category", "Depth_Of_Material"])
        
        # Create scatter plot colored by Water_Bearing
        fig = px.scatter(
            plot_df,
            x="Material_Category",
            y="Depth_Of_Material",
            color="Water_Bearing",
            color_discrete_map={True: '#0B2026', False: '#FF3621', 'TRUE': '#0B2026', 'FALSE': '#FF3621'},
            title=f"Material vs Depth Analysis",
            labels={"Material_Category": "Material", "Depth_Of_Material": "Depth (m)", "Water_Bearing": "Water Bearing"},
            opacity=0.7
        )
        
        fig.update_layout(
            height=600,
            xaxis_title="Material Type",
            yaxis_title="Depth (meters)",
            hovermode='closest',
            font=dict(family="DM Sans, sans-serif", size=12),
            title_font=dict(size=20, color='#0B2026', family='DM Sans, sans-serif', weight=700),
            plot_bgcolor='#F9F7F4',
            paper_bgcolor='#F9F7F4',
            margin=dict(l=80, r=40, t=80, b=80),
            legend=dict(
                orientation="v",
                yanchor="top",
                y=0.99,
                xanchor="right",
                x=0.99,
                bgcolor="rgba(249, 247, 244, 0.95)",
                bordercolor="#0B2026",
                borderwidth=1,
                font=dict(family="DM Sans, sans-serif")
            )
        )
        
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(11,32,38,0.1)')
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(11,32,38,0.1)')
        
        return html.Div([
            dcc.Graph(figure=fig, config={'displayModeBar': True, 'displaylogo': False})
        ], style={
            'backgroundColor': '#F9F7F4',
            'borderRadius': '15px',
            'padding': '20px',
            'boxShadow': '0 4px 12px rgba(11,32,38,0.15)',
            'border': '1px solid #EEEDE9'
        })
        
    except Exception as e:
        print(f"Error querying polygon: {str(e)}")
        import traceback
        traceback.print_exc()
        return html.Div([
            html.Div("⚠️ Error", style={
                'fontSize': '1.2rem',
                'fontWeight': '700',
                'color': '#FF3621',
                'marginBottom': '10px',
                'fontFamily': 'DM Sans, sans-serif'
            }),
            html.Div(str(e), style={
                'color': '#0B2026',
                'fontSize': '0.95rem',
                'fontFamily': 'DM Sans, sans-serif'
            })
        ], style={
            'padding': '30px',
            'backgroundColor': '#F9F7F4',
            'border': '2px solid #FF3621',
            'borderRadius': '15px',
            'boxShadow': '0 2px 8px rgba(255,54,33,0.2)'
        })

if __name__ == "__main__":
    app.run(debug=True)

