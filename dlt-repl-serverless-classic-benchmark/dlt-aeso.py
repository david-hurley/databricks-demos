"""
The 'data_sources' folder contains definitions for all data sources
used by the pipeline. Keeping them separate provides a clear overview
of the data used and allows for easy swapping of sources during development.
"""
from aeso_api import aeso
import pandas as pd
from datetime import datetime, timedelta
import pytz
from pyspark.sql.functions import col, expr, current_timestamp
import dlt

# AESO API key and instance initialization
aeso_api_key = 'b3b431c1c956490580df23f395786ba6'
aeso_instance = aeso(aeso_api_key)

@dlt.view(name = "aeso_pool_prices_snapshot")
def aeso_pool_price_snapshot():
    # Get Current Date, and Current Date + 1
    utc_time = pytz.utc.localize(datetime.utcnow())
    calgary_time = utc_time.astimezone(pytz.timezone("America/Edmonton"))

    start_date = (calgary_time - timedelta(hours=1)).strftime("%Y-%m-%d")
    end_date = (calgary_time).strftime("%Y-%m-%d")
    
    # Fetch pool price report from AESO API
    resp = aeso_instance.get_pool_price_report(
        start_date=start_date, end_date=end_date
    )
    
    # Convert response to Pandas DataFrame and then to Spark DataFrame
    pdf = pd.DataFrame(resp)
    df = spark.createDataFrame(pdf)
    
    # Add ingestion timestamp column
    return df.withColumn("ingest_timestamp", current_timestamp())

# Create a streaming table for AESO pool price bronze data
dlt.create_streaming_table("aeso_pool_prices_dlt")

# Apply changes from snapshot to the target table
dlt.apply_changes_from_snapshot(
  target = "aeso_pool_prices_dlt",
  source = "aeso_pool_prices_snapshot",
  keys = ["begin_datetime_mpt","begin_datetime_utc"],
  stored_as_scd_type = "2",
)
