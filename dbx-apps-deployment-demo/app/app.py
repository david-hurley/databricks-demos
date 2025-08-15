import streamlit as st
import os
from dotenv import load_dotenv
from utils import DatabricksQueryClient

load_dotenv()

sql_warehouse_id = os.getenv("SQL_WAREHOUSE_ID")
sql_warehouse_http_path = f"/sql/1.0/warehouses/{sql_warehouse_id}"

# cache the app level auth after first load
if "client_sp" not in st.session_state:
    st.session_state.client_sp = DatabricksQueryClient(
        http_path=sql_warehouse_http_path,
        auth_mode="sp"
    )

# cache the obo auth after first load
if "client_obo" not in st.session_state:
    user_access_token = st.context.headers.get('x-forwarded-access-token')
    
    st.session_state.client_obo = DatabricksQueryClient(
        http_path=sql_warehouse_http_path,
        auth_mode="obo",
        user_access_token=user_access_token
    )

st.title("Databricks Data Explorer")

table_name = st.text_input("Table Name", placeholder="catalog.schema.table")

st.header("App Level Authentication with Service Principal")

if st.button("Show First 10 Rows - SP") and sql_warehouse_http_path and table_name:
    df = st.session_state.client_sp.execute_query(table_name)
    st.dataframe(df)

st.header("User Level Authentication with User Identity")

if st.button("Show First 10 Rows - OBO") and sql_warehouse_http_path and table_name:
    df = st.session_state.client_obo.execute_query(table_name)
    st.dataframe(df)
