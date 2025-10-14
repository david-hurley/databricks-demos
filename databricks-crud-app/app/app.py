import time
import dash
from dash import html, Input, Output, State
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
from utils import build_pool, execute_sql, get_delta_connection, read_delta_table, write_delta_table
from config import instance_name, database, schema, table, delta_http_path, delta_table_name
from app_layout import create_layout  

connection_pool = None
delta_conn = None

w = WorkspaceClient()
cfg = Config()

user = w.current_user.me().user_name
host = w.database.get_database_instance(name=instance_name).read_write_dns

# Check if Lakebase Postgres connection pool exists, if not create one
if connection_pool is None:
    connection_pool = build_pool(instance_name, host, user, database, w)
    print("Connection pool created")

# Initialize Delta table connection exists, if not create one
if delta_conn is None:
    delta_conn = get_delta_connection(delta_http_path, cfg)
    print("Delta connection created")

# Initialize Dash app
app = dash.Dash(__name__)

# App layout
app.layout = create_layout()

@app.callback(
    Output('write-status', 'children'),
    Input('write-button', 'n_clicks'),
    State('name-input', 'value'),
    State('email-input', 'value'),
    prevent_initial_call=True
)
def write_user(n_clicks, name, email):
    """Write a name and email to the database."""
    if name and name.strip() and email and email.strip():
        start_time = time.time()
        execute_sql(connection_pool, f"INSERT INTO {schema}.{table} (name, email) VALUES (%s, %s)", (name.strip(), email.strip()))
        elapsed_time = time.time() - start_time
        return html.Div([
            html.P(f"Roundtrip Time: {elapsed_time * 1000:.2f} ms"),
        ])
    return ""

@app.callback(
    Output('data-display', 'children'),
    Input('refresh-button', 'n_clicks'),
    prevent_initial_call=False
)
def update_data(n_clicks):
    """Fetch and display data from the database."""
    start_time = time.time()
    df = execute_sql(connection_pool, f"SELECT * FROM {schema}.{table}")
    elapsed_time = time.time() - start_time
    
    table_header = html.Tr([html.Th(col, style={'padding': '10px', 'borderBottom': '2px solid #ddd'}) 
                            for col in df.columns])
    
    table_rows = []
    for _, row in df.iterrows():
        table_rows.append(
            html.Tr([html.Td(str(val), style={'padding': '10px', 'borderBottom': '1px solid #eee'}) 
                    for val in row])
        )
    
    return html.Div([
        html.H3("Query Results"),
        html.P(f"Roundtrip Time: {elapsed_time * 1000:.2f} ms"),
        html.Table(
            [table_header] + table_rows,
            style={
                'width': '100%',
                'borderCollapse': 'collapse',
                'backgroundColor': 'white',
                'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'
            }
        )
    ])

# Delta callbacks
@app.callback(
    Output('delta-write-status', 'children'),
    Input('delta-write-button', 'n_clicks'),
    State('delta-name-input', 'value'),
    State('delta-email-input', 'value'),
    prevent_initial_call=True
)
def write_delta_user(n_clicks, name, email):
    """Write a name and email to Delta table."""
    if name and name.strip() and email and email.strip():
        start_time = time.time()
        write_delta_table(delta_conn, delta_table_name, name.strip(), email.strip())
        elapsed_time = time.time() - start_time
        return html.Div([
            html.P(f"Roundtrip Time: {elapsed_time * 1000:.2f} ms"),
        ])
    return ""

@app.callback(
    Output('delta-data-display', 'children'),
    Input('delta-read-button', 'n_clicks'),
    prevent_initial_call=False
)
def read_delta_data(n_clicks):
    """Read and display data from Delta table."""
    start_time = time.time()
    df = read_delta_table(delta_conn, delta_table_name)
    elapsed_time = time.time() - start_time
    
    table_header = html.Tr([html.Th(col, style={'padding': '10px', 'borderBottom': '2px solid #ddd'}) 
                            for col in df.columns])
    
    table_rows = []
    for _, row in df.iterrows():
        table_rows.append(
            html.Tr([html.Td(str(val), style={'padding': '10px', 'borderBottom': '1px solid #eee'}) 
                    for val in row])
        )
    
    return html.Div([
        html.H3("Delta Query Results"),
        html.P(f"Roundtrip Time: {elapsed_time * 1000:.2f} ms"),
        html.Table(
            [table_header] + table_rows,
            style={
                'width': '100%',
                'borderCollapse': 'collapse',
                'backgroundColor': 'white',
                'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'
            }
        )
    ])
        
if __name__ == '__main__':
    app.run()
