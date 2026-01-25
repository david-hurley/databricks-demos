import os
from databricks import sql
import pandas as pd


def get_databricks_sql_connection(databricks_config):
    """
    Establish connection to Databricks SQL warehouse.
    
    Returns:
        Connection object if successful, None if connection fails
    """
    try:
        warehouse_id = os.getenv("SQL_WAREHOUSE_ID")
        return sql.connect(
            server_hostname=databricks_config.host.replace("https://", ""),
            http_path=f"/sql/1.0/warehouses/{warehouse_id}",
            credentials_provider=lambda: databricks_config.authenticate,
        )
    except Exception:
        return None

def read_ai_parse_results_table(sql_conn, catalog, schema, table):
    """
    Read parsed document results from Databricks table.
    
    Returns:
        DataFrame with table data, or empty DataFrame if query fails
    """
    if sql_conn is None:
        return pd.DataFrame()
    
    try:
        with sql_conn.cursor() as cursor:
            cursor.execute(f"SELECT * FROM {catalog}.{schema}.{table}")
            return cursor.fetchall_arrow().to_pandas()
    except Exception:
        return pd.DataFrame()
