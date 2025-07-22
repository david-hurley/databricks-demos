import streamlit as st
import os
from utils import get_user_access_token, get_connection_sp, get_connection_obo, execute_query, run_query_with_connection

sql_warehouse_id = os.getenv("SQL_WAREHOUSE_ID")
sql_warehouse_http_path = f"/sql/1.0/warehouses/{sql_warehouse_id}"

st.title("Databricks Data Explorer")

table_name = st.text_input("Table Name", placeholder="catalog.schema.table")

st.header("App Level Authentication with Service Principal")

if st.button("Show First 10 Rows - SP") and sql_warehouse_http_path and table_name:
    run_query_with_connection("Service Principal", get_connection_sp, sql_warehouse_http_path, table_name)

st.header("User Level Authentication with User Identity")

if st.button("Show First 10 Rows - OBO") and sql_warehouse_http_path and table_name:
    user_access_token = get_user_access_token()
    run_query_with_connection("User Identity (OBO)", get_connection_obo, sql_warehouse_http_path, table_name, user_access_token)

