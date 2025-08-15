from databricks import sql
from databricks.sdk.core import Config
import streamlit as st

class DatabricksQueryClient:
    """
    DatabricksQueryClient is a class that provides a connection to a Databricks SQL warehouse.
    It supports both app level auth and user level auth.
    """
    def __init__(self, http_path: str, auth_mode: str = "sp", user_access_token: str = None):
        self.cfg = Config()
        self.http_path = http_path
        self.auth_mode = auth_mode
        self.user_access_token = user_access_token
        self.conn = self._create_connection()

    def _create_connection(self):
        """
        Create a connection to a Databricks SQL warehouse using the provided http path and auth mode.
        """
        if self.auth_mode == "sp":
            return sql.connect(
                server_hostname=self.cfg.host,
                http_path=self.http_path,
                credentials_provider=lambda: self.cfg.authenticate,
            )
        elif self.auth_mode == "obo":
            return sql.connect(
                server_hostname=self.cfg.host,
                http_path=self.http_path,
                access_token=self.user_access_token,
            )
        else:
            raise ValueError("Invalid auth mode")

    def execute_query(self, table_name: str):
        """
        Execute a query against the Databricks SQL warehouse.
        """
        with self.conn.cursor() as cursor:
            query = f"SELECT * FROM {table_name}"
            try:
                cursor.execute(query)
                return cursor.fetchall_arrow().to_pandas()
            except Exception as e:
                st.error(f"Failed to run query: {e}")
