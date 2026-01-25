from dash import html, dcc
import dash_bootstrap_components as dbc
import dash_ag_grid as dag
import os

# Style constants
FONT = {"fontFamily": "DM Sans"}
BORDER = {**FONT, "borderColor": "#0B2026", "color": "#0B2026"}
CARD = {"border": "1px solid #ddd", "borderRadius": "8px", "padding": "15px", "backgroundColor": "#fff"}

def create_header():
    """Create app header with logo, title, and instructions button."""
    return dbc.Row([
        dbc.Col([
            html.Div([
                html.Div([
                    html.Img(src="/assets/databricks-symbol-color.svg", 
                            style={"height": "40px", "marginRight": "15px", "verticalAlign": "middle"}),
                    html.H2("ai_parse_document() Visualizer App", 
                           style={**FONT, "fontWeight": "700", "margin": "0", "display": "inline-block", "verticalAlign": "middle"}),
                ], style={"display": "flex", "alignItems": "center", "justifyContent": "center"}),
                dbc.Button("❓ Instructions", id="open-instructions", size="sm", outline=True, 
                          style={**BORDER, "position": "absolute", "right": "0", "top": "50%", "transform": "translateY(-50%)"}),
            ], style={"position": "relative", "marginBottom": "1rem"}),
        ], width=12),
    ])

def create_instructions_modal():
    """Create instructions modal with setup link."""
    return dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("📖 Getting Started", style={**FONT, "fontWeight": "700"})),
        dbc.ModalBody([
            html.P([
                html.Span("Refer to the README in ", style={**FONT, "fontSize": "16px"}),
                html.A("https://github.com/david-hurley/databricks-demos/tree/main/ai-parse-doc-visualizer-app", 
                       href="https://github.com/david-hurley/databricks-demos/tree/main/ai-parse-doc-visualizer-app",
                       target="_blank",
                       style={**FONT, "fontSize": "16px", "color": "#0B2026", "textDecoration": "underline"}),
                html.Span(" for getting started", style={**FONT, "fontSize": "16px"}),
            ], style={"textAlign": "center", "marginTop": "20px", "marginBottom": "20px"}),
        ], style=FONT),
        dbc.ModalFooter(dbc.Button("Close", id="close-instructions", className="ms-auto", size="sm", style=FONT)),
    ], id="instructions-modal", is_open=True, centered=True, size="lg")

def create_left_panel(grid_data):
    """Create left panel with catalog/schema/table inputs and file grid."""
    return dbc.Col([
        # Catalog/Schema/Table inputs
        html.Div([
            dbc.Input(id=f"{name}-input", placeholder=name.title(), value=os.getenv(name.upper()), 
                     size="sm", style={**BORDER, "flex": "1"})
            for name in ["catalog", "schema", "table"]
        ], style={**CARD, "display": "flex", "gap": "10px", "marginBottom": "15px"}),
        
        # Search bar + file grid
        html.Div([
            # Search and refresh
            html.Div([
                dbc.Input(id="grid-search-input", placeholder="Search by filename or path...", 
                         size="sm", style={**BORDER, "width": "60%"}),
                dbc.Button("↻ Refresh", id="refresh-btn", size="sm", outline=True, 
                          style={**BORDER, "marginLeft": "10px", "whiteSpace": "nowrap", "flex": "1"}),
            ], style={"display": "flex", "marginBottom": "10px", "alignItems": "center"}),
            
            # File grid
            dcc.Loading(id="loading-grid-container", type="default", children=html.Div([
                dag.AgGrid(
                    id="files-grid",
                    rowData=grid_data,
                    columnDefs=[
                        {"field": "name", "headerName": "Filename", "checkboxSelection": True, "flex": 1},
                        {"field": "path", "headerName": "Volume Path", "flex": 2, 
                         "tooltipField": "path", "wrapText": True, "autoHeight": True}
                    ],
                    dashGridOptions={"rowSelection": "single"},
                    defaultColDef={"resizable": True},
                    style={"height": "100%", **FONT}
                ),
            ], style={"height": "calc(100vh - 350px)", "overflow": "auto"})),
        ], style={**CARD, "height": "calc(100vh - 260px)", "marginBottom": "15px"}),
    ], width=5)

def create_right_panel():
    """Create right panel with document viewer and page navigation."""
    return dbc.Col([
        html.Div([
            # Document viewer
            dcc.Loading(id="loading-document-display", type="default", children=html.Div(
                id="document-display",
                style={"height": "calc(100vh - 280px)", "overflowX": "auto", 
                       "overflowY": "auto", "scrollBehavior": "smooth"}
            )),
            
            # Page navigation
            html.Div([
                dbc.Button("← Previous", id="prev-page-btn", size="sm", outline=True, 
                          disabled=True, style={**BORDER}),
                dbc.Button("Next →", id="next-page-btn", size="sm", outline=True, 
                          disabled=True, className="ms-2", style={**BORDER}),
                html.Div([
                    dcc.Dropdown(id="page-dropdown", options=[], value=1, clearable=False, 
                                optionHeight=35, style={"width": "120px", **FONT}),
                ], style={"display": "inline-block", "marginLeft": "10px", "verticalAlign": "middle"}),
                html.Span(id="page-info", className="ms-3", 
                         style={**FONT, "color": "#0B2026", "verticalAlign": "middle"})
            ], className="mt-2"),
        ], style={**CARD, "height": "calc(100vh - 180px)", "maxWidth": "900px", 
                  "marginLeft": "auto", "marginRight": "auto"}),
    ], width=7)

def create_layout(grid_data, error_message=None):
    """Create main application layout."""
    return html.Div(
        style={"backgroundColor": "#EEEDE9", "minHeight": "100vh", "color": "#0B2026", "padding": "2vh 3vw"}, 
        children=[
            dbc.Container([
                create_header(),
                
                # Error/warning container
                html.Div(id="error-message-container", children=[
                    dbc.Alert(error_message, color="warning", 
                             style={**FONT, "fontSize": "16px", "textAlign": "center"}) if error_message else html.Div()
                ]),
                
                # Page state store
                dcc.Store(id="page-store", data={"current_page": 1, "total_pages": 1}),
                
                create_instructions_modal(),
                
                # Main 2-column layout
                dbc.Row([
                    create_left_panel(grid_data),
                    create_right_panel(),
                ]),
            ], fluid=True, style=FONT)
        ]
    )
