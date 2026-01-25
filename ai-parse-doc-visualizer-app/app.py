import json
import os
from dash import Dash, html, Input, Output, State, callback_context, dcc
import dash_bootstrap_components as dbc
from databricks.sdk import WorkspaceClient
import pandas as pd
from databricks.sdk.core import Config
from document_renderer import DocumentRenderer
from dotenv import load_dotenv
from app_layout import create_layout
from databricks_utils import get_databricks_sql_connection, read_ai_parse_results_table

# Load environment variables
load_dotenv()

# Initialize Databricks clients
workspace_client = WorkspaceClient()
databricks_config = Config()
sql_connection = get_databricks_sql_connection(databricks_config)
renderer = DocumentRenderer(workspace_client=workspace_client)

# Load initial data
df = read_ai_parse_results_table(
    sql_connection, 
    os.getenv("CATALOG"), 
    os.getenv("SCHEMA"), 
    os.getenv("TABLE")
)

# Initialize Dash app
app = Dash(__name__, external_stylesheets=[
    dbc.themes.BOOTSTRAP,
    "https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&display=swap"
])

# Style constants
FONT_STYLE = {"fontFamily": "DM Sans", "borderColor": "#0B2026"}
ALERT_STYLE = {**FONT_STYLE, "fontSize": "16px", "textAlign": "center"}

def get_error_alert(sql_conn, dataframe, catalog, schema, table):
    """Generate error alert if connection failed or no data found."""
    if sql_conn is None:
        return dbc.Alert(
            "⚠️ Unable to establish SQL connection. Please check your SQL_WAREHOUSE_ID and credentials.", 
            color="warning", style=ALERT_STYLE
        )
    if dataframe.empty:
        return dbc.Alert(
            f"⚠️ No data found in table {catalog}.{schema}.{table}. The table may not exist.", 
            color="warning", style=ALERT_STYLE
        )
    return html.Div()

def prepare_grid_data(dataframe, search_value=None):
    """Convert dataframe to grid format with optional search filter."""
    if dataframe.empty:
        return []
    
    grid_data = []
    for idx, row in dataframe.iterrows():
        # Clean file path
        path = row.get('path', '') if pd.notna(row.get('path')) else ''
        display_path = path.replace('dbfs:/', '')
        filename = display_path.split('/')[-1] if display_path else ''
        
        # Apply search filter
        if search_value:
            search_lower = search_value.lower()
            if search_lower not in filename.lower() and search_lower not in display_path.lower():
                continue
        
        grid_data.append({"id": idx, "name": filename, "path": display_path})
    
    return grid_data

# Set initial layout
error_alert = get_error_alert(
    sql_connection, df, 
    os.getenv('CATALOG'), os.getenv('SCHEMA'), os.getenv('TABLE')
)
error_message = error_alert.children if isinstance(error_alert, dbc.Alert) else None
app.layout = create_layout(prepare_grid_data(df), error_message)

@app.callback(
    Output("instructions-modal", "is_open"),
    Input("open-instructions", "n_clicks"),
    Input("close-instructions", "n_clicks"),
    State("instructions-modal", "is_open"),
    prevent_initial_call=True
)
def toggle_instructions_modal(open_clicks, close_clicks, is_open):
    """Toggle instructions modal."""
    return not is_open

@app.callback(
    Output("files-grid", "rowData"),
    Output("error-message-container", "children"),
    Input("refresh-btn", "n_clicks"),
    Input("grid-search-input", "value"),
    State("catalog-input", "value"),
    State("schema-input", "value"),
    State("table-input", "value")
)
def update_grid_data(n_clicks, search_value, catalog, schema, table):
    """Refresh grid data on button click or search change."""
    global df
    
    # Reload data if refresh button clicked
    if callback_context.triggered and callback_context.triggered[0]['prop_id'].split('.')[0] == 'refresh-btn':
        df = read_ai_parse_results_table(sql_connection, catalog, schema, table)
    
    return (
        prepare_grid_data(df, search_value), 
        get_error_alert(sql_connection, df, catalog, schema, table)
    )

@app.callback(
    Output("document-display", "children"),
    Output("page-info", "children"),
    Output("prev-page-btn", "disabled"),
    Output("next-page-btn", "disabled"),
    Output("prev-page-btn", "style"),
    Output("next-page-btn", "style"),
    Output("page-dropdown", "options"),
    Output("page-dropdown", "value"),
    Output("page-dropdown", "style"),
    Output("page-store", "data"),
    Input("files-grid", "selectedRows"),
    Input("prev-page-btn", "n_clicks"),
    Input("next-page-btn", "n_clicks"),
    Input("page-dropdown", "value"),
    State("page-store", "data")
)
def display_document(selected_rows, prev_clicks, next_clicks, dropdown_page, page_data):
    """Display selected document with page navigation."""
    # Get current page state
    current_page = page_data.get("current_page", 1) if page_data else 1
    total_pages = page_data.get("total_pages", 1) if page_data else 1
    
    # Handle navigation triggers
    if callback_context.triggered:
        trigger_id = callback_context.triggered[0]['prop_id'].split('.')[0]
        if trigger_id == "prev-page-btn":
            current_page = max(1, current_page - 1)
        elif trigger_id == "next-page-btn":
            current_page = min(total_pages, current_page + 1)
        elif trigger_id == "page-dropdown":
            current_page = dropdown_page or 1
        elif trigger_id == "files-grid":
            current_page = 1
    
    # Style constants
    DISABLED_STYLE = {**FONT_STYLE, "color": "#EEEDE9"}
    EMPTY_RESULT = (
        html.Div([html.P(
            "← Select a document from the grid to view", 
            style={"color": "#0B2026", "opacity": "0.6", "fontStyle": "italic", 
                   "padding": "40px", "textAlign": "center", "margin": "0"}
        )]),
        "", True, True, DISABLED_STYLE, DISABLED_STYLE, [], 1,
        {"width": "120px", **FONT_STYLE, "color": "#EEEDE9"},
        {"current_page": 1, "total_pages": 1}
    )
    
    # Validate selection
    if not selected_rows:
        return EMPTY_RESULT
    
    row_id = selected_rows[0].get("id")
    if row_id is None or df.empty or row_id >= len(df):
        return EMPTY_RESULT
    
    parsed_result = df.iloc[row_id]['parsed']
    if pd.isna(parsed_result):
        return EMPTY_RESULT
    
    # Get total pages from document
    try:
        parsed_dict = json.loads(parsed_result) if isinstance(parsed_result, str) else parsed_result
        total_pages = len(parsed_dict.get("document", {}).get("pages", [])) or 1
    except:
        total_pages = 1
    
    # Clamp current page to valid range
    current_page = max(1, min(current_page, total_pages))
    
    # Render document
    rendered_html = renderer.render_document_to_html(parsed_result, page_selection=str(current_page))
    
    # Button states
    is_prev_disabled = current_page <= 1
    is_next_disabled = current_page >= total_pages
    
    return (
        html.Iframe(srcDoc=rendered_html, style={"width": "100%", "height": "100%", "border": "none"}),
        f"Page {current_page} of {total_pages}",
        is_prev_disabled,
        is_next_disabled,
        {**FONT_STYLE, "color": "#EEEDE9" if is_prev_disabled else "#0B2026"},
        {**FONT_STYLE, "color": "#EEEDE9" if is_next_disabled else "#0B2026"},
        [{"label": f"Page {i}", "value": i} for i in range(1, total_pages + 1)],
        current_page,
        {"width": "120px", **FONT_STYLE, "color": "#0B2026"},
        {"current_page": current_page, "total_pages": total_pages}
    )

if __name__ == "__main__":
    app.run()
