import uuid
import pandas as pd
import psycopg
from psycopg_pool import ConnectionPool
from dotenv import load_dotenv
from databricks.sdk import WorkspaceClient
import os
import time

# for local development
load_dotenv(dotenv_path="../.env") 

workspace_client = WorkspaceClient()
postgres_password = None
last_password_refresh = 0
connection_pool = None

def refresh_oauth_token():
    """Refresh OAuth token if expired."""
    global postgres_password, last_password_refresh
    if postgres_password is None or time.time() - last_password_refresh > 900:
        try:
            # In-app authentication
            postgres_password = workspace_client.config.oauth_token().access_token
        except:
            # Fallback to local authentication
            postgres_password = workspace_client.database.generate_database_credential(
                request_id=str(uuid.uuid4()),
                instance_names=[os.getenv("INSTANCE_NAME")]
            ).token
        last_password_refresh = time.time()
    return True

def get_connection_pool():
    """Get or create the connection pool."""
    global connection_pool
    if connection_pool is None:
        refresh_oauth_token()
        conn_string = (
            f"dbname={os.getenv('PGDATABASE')} "
            f"user={os.getenv('PGUSER')} "
            f"password={postgres_password} "
            f"host={os.getenv('PGHOST')} "
            f"port={os.getenv('PGPORT')} "
            f"sslmode={os.getenv('PGSSLMODE', 'require')} "
            f"application_name={os.getenv('PGAPPNAME')}"
        )
        connection_pool = ConnectionPool(conn_string, min_size=2, max_size=10)
    return connection_pool

def get_connection():
    """Get a connection from the pool."""
    global connection_pool
    
    if postgres_password is None or time.time() - last_password_refresh > 900:
        if connection_pool:
            connection_pool.close()
            connection_pool = None
    
    return get_connection_pool().connection()

def get_water_well_locations() -> pd.DataFrame:
    """Execute SQL query or command."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"""SELECT * FROM {os.getenv('LAKEBASE_SCHEMA')}.alberta_wdrill_wells_postgres ORDER BY RANDOM() LIMIT 10000""")
            if cur.description is None:
                return pd.DataFrame()
            cols = [d.name for d in cur.description]
            rows = cur.fetchall()
    return pd.DataFrame(rows, columns=cols)

def get_water_well_locations_in_polygon(polygon_coords: list) -> pd.DataFrame:
    """Query points that fall within a polygon using PostGIS ST_Contains"""

    if polygon_coords[0] != polygon_coords[-1]:
        polygon_coords = polygon_coords + [polygon_coords[0]]
    
    coords_str = ', '.join([f"{lon} {lat}" for lon, lat in polygon_coords])
    polygon_wkt = f"POLYGON(({coords_str}))"
    
    query = f"""
    SELECT *
    FROM {os.getenv('LAKEBASE_SCHEMA')}.alberta_wdrill_combined_location_lithology_postgres
    WHERE ST_Contains(
        ST_GeomFromText('{polygon_wkt}', 4326),
        ST_SetSRID(ST_MakePoint("Longitude", "Latitude"), 4326)
    )
    """

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query)
            if cur.description is None:
                return pd.DataFrame()
            cols = [d.name for d in cur.description]
            rows = cur.fetchall()
    return pd.DataFrame(rows, columns=cols)