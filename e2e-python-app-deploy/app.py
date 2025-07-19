import streamlit as st
from databricks import sql
from databricks.sdk.core import Config


cfg = Config()  # Set the DATABRICKS_HOST environment variable when running locally


@st.cache_resource # connection is cached
def get_connection(http_path):
    return sql.connect(
        server_hostname=cfg.host,
        http_path=http_path,
        credentials_provider=lambda: cfg.authenticate,
    )

def read_table(table_name, conn):
    with conn.cursor() as cursor:
        query = f"SELECT * FROM {table_name}"
        cursor.execute(query)
        return cursor.fetchall_arrow().to_pandas()

http_path_input = st.text_input(
    "Enter your Databricks HTTP Path:", placeholder="/sql/1.0/warehouses/xxxxxx"
)

table_name = st.text_input(
    "Specify a :re[UC] table name:", placeholder="catalog.schema.table"
)

if http_path_input and table_name:
    conn = get_connection(http_path_input)
    df = read_table(table_name, conn)
    st.dataframe(df)