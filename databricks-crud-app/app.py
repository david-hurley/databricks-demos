import uuid
import time
import pandas as pd
import dash
from dash import html, dcc, Input, Output, State
from databricks.sdk import WorkspaceClient
from databricks.sdk.core import Config
from databricks import sql
import psycopg
from psycopg_pool import ConnectionPool

instance_name = "david-demo-instance"
database = "databricks_postgres"
schema = "public"
table = "users"
connection_pool = None

delta_http_path = "/sql/1.0/warehouses/383cc3b75ffe2072"  # Update with your warehouse path
delta_table_name = "users.david_hurley.users"  # Update with your table name
delta_conn = None

w = WorkspaceClient()
cfg = Config()

user = w.current_user.me().user_name
host = w.database.get_database_instance(name=instance_name).read_write_dns

class RotatingTokenConnection(psycopg.Connection):
    """psycopg3 Connection that injects a fresh OAuth token as the password."""
    
    @classmethod
    def connect(cls, conninfo: str = "", **kwargs):
        kwargs["password"] = w.database.generate_database_credential(
            request_id=str(uuid.uuid4()),
            instance_names=[kwargs.pop("_instance_name")]
        ).token
        kwargs.setdefault("sslmode", "require")
        return super().connect(conninfo, **kwargs)

def build_pool(instance_name: str, host: str, user: str, database: str) -> ConnectionPool:
    """Build a connection pool with rotating tokens."""
    return ConnectionPool(
        conninfo=f"host={host} dbname={database} user={user}",
        connection_class=RotatingTokenConnection,
        kwargs={"_instance_name": instance_name},
        min_size=1,
        max_size=5,
        open=True,
    )

def execute_sql(sql: str, params: tuple = None) -> pd.DataFrame:
    """Execute SQL query or command. Returns DataFrame for SELECT, empty DataFrame otherwise."""
    with connection_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params) if params else cur.execute(sql)
            if cur.description:
                cols = [d.name for d in cur.description]
                rows = cur.fetchall()
                return pd.DataFrame(rows, columns=cols)
            conn.commit() 
            return pd.DataFrame()

def get_delta_connection(http_path):
    """Get or create cached Delta connection."""
    return sql.connect(
        server_hostname=cfg.host,
        http_path=http_path,
        credentials_provider=lambda: cfg.authenticate,
    )

def read_delta_table(table_name: str) -> pd.DataFrame:
    """Read data from Delta table."""
    with delta_conn.cursor() as cursor:
        cursor.execute(f"SELECT * FROM {table_name}")
        return cursor.fetchall_arrow().to_pandas()

def write_delta_table(table_name: str, name: str, email: str):
    """Write data to Delta table."""
    with delta_conn.cursor() as cursor:
        cursor.execute(f"INSERT INTO {table_name} (name	, email) VALUES ('{name}', '{email}')")

# Check if pool exists, if not create connection
if connection_pool is None:
    connection_pool = build_pool(instance_name, host, user, database)
    print("Connection pool created")

# Initialize Delta connection on load
if delta_conn is None:
    delta_conn = get_delta_connection(delta_http_path)
    print("Delta connection created")

# Initialize Dash app
app = dash.Dash(__name__)

# App layout
app.layout = html.Div([
    html.H1("Simple Dash App", style={'textAlign': 'center', 'marginBottom': '30px'}),
    
    # PostgreSQL Section
    html.Div([
        html.H2("PostgreSQL", style={'marginBottom': '20px'}),
        html.Div([
            dcc.Input(
                id='name-input',
                type='text',
                placeholder='Enter name...',
                style={
                    'padding': '10px',
                    'marginRight': '10px',
                }
            ),
            dcc.Input(
                id='email-input',
                type='email',
                placeholder='Enter email...',
                style={
                    'padding': '10px',
                    'marginRight': '10px',
                }
            ),
            html.Button(
                'Write To Postgres',
                id='write-button',
                n_clicks=0,
                style={
                    'padding': '10px 20px',
                }
            ),
        ]),
        html.Div(id='write-status'),
        html.Div([
            html.Button(
                'Read From Postgres',
                id='refresh-button',
                n_clicks=0,
                style={
                    'padding': '10px 20px',
                    'marginBottom': '20px',
                    'marginTop': '20px'
                }
            ),
        ]),
        html.Div(id='data-display')
    ], style={'marginBottom': '50px', 'paddingBottom': '30px', 'borderBottom': '2px solid #ddd'}),
    
    # Delta Lake Section
    html.Div([
        html.H2("Delta Lake", style={'marginBottom': '20px'}),
        html.Div([
            dcc.Input(
                id='delta-name-input',
                type='text',
                placeholder='Enter name...',
                style={
                    'padding': '10px',
                    'marginRight': '10px',
                }
            ),
            dcc.Input(
                id='delta-email-input',
                type='email',
                placeholder='Enter email...',
                style={
                    'padding': '10px',
                    'marginRight': '10px',
                }
            ),
            html.Button(
                'Write to Delta',
                id='delta-write-button',
                n_clicks=0,
                style={
                    'padding': '10px 20px',
                }
            ),
        ]),
        html.Div(id='delta-write-status'),
        html.Div([
            html.Button(
                'Read From Delta',
                id='delta-read-button',
                n_clicks=0,
                style={
                    'padding': '10px 20px',
                    'marginBottom': '20px',
                    'marginTop': '20px'
                }
            ),
        ]),
        html.Div(id='delta-data-display')
    ])
])

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
        execute_sql(f"INSERT INTO {schema}.{table} (name, email) VALUES (%s, %s)", (name.strip(), email.strip()))
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
    df = execute_sql(f"SELECT * FROM {schema}.{table}")
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
        write_delta_table(delta_table_name, name.strip(), email.strip())
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
    df = read_delta_table(delta_table_name)
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
