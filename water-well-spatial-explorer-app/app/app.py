import dash
from dash import html, dcc
import dash_leaflet as dl
from dash.dependencies import Input, Output
import plotly.express as px
from utils import get_water_well_locations, get_water_well_locations_in_polygon
from layout import create_layout

MESSAGE_STYLE = {
    'textAlign': 'center',
    'padding': '40px',
    'backgroundColor': '#F9F7F4',
    'borderRadius': '15px',
    'border': '1px solid #EEEDE9'
}

df_wells = get_water_well_locations()
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


def show_message(message):
    """Helper to show centered messages"""
    return html.Div(message, style=MESSAGE_STYLE)


@app.callback(
    Output("polygon_output", "children"),
    Input("edit_control", "geojson")
)
def handle_polygon(poly_json):
    if not poly_json:
        return show_message("Draw a polygon on the map to query wells")
    
    try:
        features = poly_json.get('features', [])
        if not features or features[-1].get('geometry', {}).get('type') != 'Polygon':
            return show_message("Please draw a valid polygon")
        
        coords = features[-1]['geometry']['coordinates'][0]
        if len(coords) < 3:
            return show_message("Polygon must have at least 3 points")
                
        result_df = get_water_well_locations_in_polygon(coords)
        plot_df = result_df[["Material_Category", "Depth_Of_Material", "Water_Bearing"]].dropna(
            subset=["Material_Category", "Depth_Of_Material"]
        )
        
        fig = px.scatter(
            plot_df,
            x="Material_Category",
            y="Depth_Of_Material",
            color="Water_Bearing",
            color_discrete_map={True: '#0B2026', False: '#FF3621', 'TRUE': '#0B2026', 'FALSE': '#FF3621'},
            title="Material vs Depth Analysis",
            labels={"Material_Category": "Material", "Depth_Of_Material": "Depth (m)", "Water_Bearing": "Water Bearing"},
            opacity=0.7
        )
        
        fig.update_layout(
            height=600,
            font=dict(family="DM Sans, sans-serif"),
            plot_bgcolor='#F9F7F4',
            paper_bgcolor='#F9F7F4'
        )
        
        return dcc.Graph(figure=fig, config={'displaylogo': False})
        
    except Exception as e:
        print(f"Error querying polygon: {e}")
        return show_message(f"⚠️ Error: {str(e)}")

if __name__ == "__main__":
    app.run()

