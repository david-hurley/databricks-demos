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


def get_delta_connection(http_path, cfg):
    """Get or create cached Delta connection."""
    return sql.connect(
        server_hostname=cfg.host,
        http_path=http_path,
        credentials_provider=lambda: cfg.authenticate,
    )


def read_delta_table(delta_conn, table_name: str) -> pd.DataFrame:
    """Read data from Delta table."""
    with delta_conn.cursor() as cursor:
        cursor.execute(f"SELECT * FROM {table_name}")
        return cursor.fetchall_arrow().to_pandas()


def write_delta_table(delta_conn, table_name: str, name: str, email: str):
    """Write data to Delta table."""
    with delta_conn.cursor() as cursor:
        cursor.execute(f"INSERT INTO {table_name} (name	, email) VALUES ('{name}', '{email}')")

