import streamlit as st
from databricks import sql
from databricks.sdk.core import Config

cfg = Config()

def run_query_with_connection(connection_type, get_connection_func, http_path, table_name, *args):
    """Execute query with the specified connection type and display results."""    
    try:
        conn = get_connection_func(http_path, *args)
        df = execute_query(table_name, conn)
        st.success(f"Query executed successfully with {connection_type}!")
        st.dataframe(df)
    except Exception as e:
        st.error(f"Failed to run query with {connection_type}: {e}")

def execute_query(table_name, conn):
    """Execute query with the specified connection type and display results."""    
    with conn.cursor() as cursor:
        query = f"SELECT * FROM {table_name} LIMIT 10"
        cursor.execute(query)
        return cursor.fetchall_arrow().to_pandas()

def get_user_access_token():
    """Get the user access token from the request headers."""
    user_access_token = st.context.headers.get('x-forwarded-access-token')
    return user_access_token

def get_connection_sp(http_path):
    """Get a connection to the SQL warehouse using a service principal."""
    return sql.connect(
        server_hostname=cfg.host,
        http_path=http_path,
        credentials_provider=lambda: cfg.authenticate,
    )

def get_connection_obo(http_path, user_access_token):
    """Get a connection to the SQL warehouse using a user identity."""
    print("this is the user access token", user_access_token)
    return sql.connect(
        server_hostname=cfg.host,
        http_path=http_path,
        access_token=user_access_token,
    )