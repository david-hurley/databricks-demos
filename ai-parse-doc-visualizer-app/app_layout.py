from dash import html, dcc
import dash_bootstrap_components as dbc
import dash_ag_grid as dag
import os

# Shared style constants for consistent UI
FONT = {"fontFamily": "DM Sans"}
BORDER = {"borderColor": "#0B2026", "color": "#0B2026"}
CARD_STYLE = {"border": "1px solid #ddd", "borderRadius": "8px", "padding": "15px", "backgroundColor": "#fff"}

def create_layout(grid_data, error_message=None):
    """Create main application layout with 2-column design (grid + document viewer)."""
    return html.Div(style={"backgroundColor": "#EEEDE9", "minHeight": "100vh", "color": "#0B2026", "padding": "2vh 3vw"}, children=[
        dbc.Container([
            # Header with title and instructions button
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.Div([
                            html.Img(src="/assets/databricks-symbol-color.svg", 
                                    style={"height": "40px", "marginRight": "15px", "verticalAlign": "middle"}),
                            html.H2("ai_parse_document() Visualizer App", 
                                   style={**FONT, "fontWeight": "700", "margin": "0", "display": "inline-block", "verticalAlign": "middle"}),
                        ], style={"display": "flex", "alignItems": "center", "justifyContent": "center"}),
                        dbc.Button("❓ Instructions", id="open-instructions", size="sm", outline=True, 
                                  style={**FONT, **BORDER, "position": "absolute", "right": "0", "top": "50%", "transform": "translateY(-50%)"}),
                    ], style={"position": "relative", "marginBottom": "1rem"}),
                ], width=12),
            ]),
            
            # Error/warning message container (dynamic updates via callback)
            html.Div(id="error-message-container", children=[
                dbc.Alert(error_message, color="warning", 
                         style={**FONT, "fontSize": "16px", "textAlign": "center"}) if error_message else html.Div()
            ]),
            
            # Store for tracking current page state across callbacks
            dcc.Store(id="page-store", data={"current_page": 1, "total_pages": 1}),
            
            # Instructions modal
            dbc.Modal([
                dbc.ModalHeader(dbc.ModalTitle("📖 How to Use This App", style={**FONT, "fontWeight": "700"})),
                dbc.ModalBody([
                    html.H5("Getting Started", style={**FONT, "fontWeight": "600", "marginTop": "10px"}),
                    html.Ul([
                        html.Li(txt, style={"marginBottom": "8px"})
                        for txt in [
                            "Select a catalog, schema, and table from the input fields at the top",
                            "Click the 'Refresh' button to load documents from your table",
                            "Use the search bar to filter documents by filename or path"
                        ]
                    ], style=FONT),
                    html.H5("Viewing Documents", style={**FONT, "fontWeight": "600", "marginTop": "15px"}),
                    html.Ul([
                        html.Li(txt, style={"marginBottom": "8px"})
                        for txt in [
                            "Click on any document in the grid to view it",
                            "The document will appear on the right with highlighted bounding boxes",
                            "Hover over any bounding box to see element details in a tooltip",
                            "Use 'Previous' and 'Next' buttons or the page dropdown to navigate multi-page documents"
                        ]
                    ], style=FONT),
                ], style=FONT),
                dbc.ModalFooter(dbc.Button("Close", id="close-instructions", className="ms-auto", size="sm", style=FONT)),
            ], id="instructions-modal", is_open=True, centered=True, size="lg"),
            
            # Main 2-column layout
            dbc.Row([
                # Left column: Table selector + file grid
                dbc.Col([
                    # Catalog/Schema/Table input fields
                    html.Div([
                        dbc.Input(id=f"{name}-input", placeholder=name.title(), value=os.getenv(name.upper()), 
                                 size="sm", style={**FONT, **BORDER, "flex": "1"})
                        for name in ["catalog", "schema", "table"]
                    ], style={**CARD_STYLE, "display": "flex", "gap": "10px", "marginBottom": "15px"}),
                    
                    # Search bar + grid container
                    html.Div([
                        # Search and refresh controls
                        html.Div([
                            dbc.Input(id="grid-search-input", placeholder="Search by filename or path...", 
                                     size="sm", style={**FONT, **BORDER, "width": "60%"}),
                            dbc.Button("↻ Refresh", id="refresh-btn", size="sm", outline=True, 
                                      style={**FONT, **BORDER, "marginLeft": "10px", "whiteSpace": "nowrap", "flex": "1"}),
                        ], style={"display": "flex", "gap": "0", "marginBottom": "10px", "alignItems": "center"}),
                        
                        # AG Grid with file list
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
                        ], style={"height": "calc(100vh - 260px - 90px)", "overflow": "auto"})),
                    ], style={**CARD_STYLE, "height": "calc(100vh - 260px)", "marginBottom": "15px"}),
                ], width=5),
                
                # Right column: Document viewer with page navigation
                dbc.Col([
                    html.Div([
                        # Document display area
                        dcc.Loading(id="loading-document-display", type="default", children=html.Div(
                            id="document-display",
                            style={"height": "calc(100vh - 280px)", "overflowX": "auto", "overflowY": "auto", "scrollBehavior": "smooth"}
                        )),
                        
                        # Page navigation controls
                        html.Div([
                            dbc.Button("← Previous", id="prev-page-btn", size="sm", outline=True, disabled=True, style={**FONT, **BORDER}),
                            dbc.Button("Next →", id="next-page-btn", size="sm", outline=True, disabled=True, className="ms-2", style={**FONT, **BORDER}),
                            html.Div([
                                dcc.Dropdown(id="page-dropdown", options=[], value=1, clearable=False, optionHeight=35,
                                            style={"width": "120px", **FONT}),
                            ], style={"display": "inline-block", "marginLeft": "10px", "verticalAlign": "middle"}),
                            html.Span(id="page-info", className="ms-3", style={**FONT, "color": "#0B2026", "verticalAlign": "middle"})
                        ], className="mt-2"),
                    ], style={**CARD_STYLE, "height": "calc(100vh - 180px)", "maxWidth": "900px", "marginLeft": "auto", "marginRight": "auto"}),
                ], width=7),
            ]),
        ], fluid=True, style=FONT)
    ])
