import uuid
import pandas as pd
import psycopg
from psycopg_pool import ConnectionPool
from databricks import sql

class RotatingTokenConnection(psycopg.Connection):
    """psycopg3 Connection that injects a fresh OAuth token as the password."""
    
    @classmethod
    def connect(cls, conninfo: str = "", w=None, **kwargs):
        kwargs["password"] = w.database.generate_database_credential(
            request_id=str(uuid.uuid4()),
            instance_names=[kwargs.pop("_instance_name")]
        ).token
        kwargs.setdefault("sslmode", "require")
        return super().connect(conninfo, **kwargs)


def build_pool(instance_name: str, host: str, user: str, database: str, w) -> ConnectionPool:
    """Build a connection pool with rotating tokens."""
    return ConnectionPool(
        conninfo=f"host={host} dbname={database} user={user}",
        connection_class=RotatingTokenConnection,
        kwargs={"_instance_name": instance_name, "w": w},
        min_size=1,
        max_size=5,
        open=True,
    )


def execute_sql(connection_pool, sql: str, params: tuple = None) -> pd.DataFrame:
    """Execute SQL query or command."""
    with connection_pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            if cur.description is None:
                return pd.DataFrame()
            cols = [d.name for d in cur.description]
            rows = cur.fetchall()
    return pd.DataFrame(rows, columns=cols)

def query_points_in_polygon(connection_pool, schema: str, table: str, polygon_coords: list) -> pd.DataFrame:
    """Query points that fall within a polygon using PostGIS ST_Contains"""

    if polygon_coords[0] != polygon_coords[-1]:
        polygon_coords = polygon_coords + [polygon_coords[0]]
    
    coords_str = ', '.join([f"{lon} {lat}" for lon, lat in polygon_coords])
    polygon_wkt = f"POLYGON(({coords_str}))"
    
    query = f"""
    SELECT *
    FROM {schema}.{table}
    WHERE ST_Contains(
        ST_GeomFromText('{polygon_wkt}', 4326),
        ST_SetSRID(ST_MakePoint("Longitude", "Latitude"), 4326)
    )
    """
        
    return execute_sql(connection_pool, query)