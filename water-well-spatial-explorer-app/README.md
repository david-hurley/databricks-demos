# Alberta Water Well Spatial Explorer

An interactive web application for subsurface data related to drilled water wells in Alberta.

## Overview

This application demonstrates how to build a low-latency Databricks App for quering spatial data with freeform polygons. Draw a polygon on the map and view the scatter plot of material composition vs depth for water bearing material. 

- **Databricks App** - 
- **Databricks Lakebase** - Managed PostGIS-compatible database for spatial queries
- **PostGIS** - 

## Getting Started

**Prerequisites**
- **Databricks Workspace**
- **Databricks CLI**
- **Python**
- **uv**, used for package and Python management

#### Data Setup
1. Clone this repository to your Databricks workspace
2. Open `001-setup.ipynb` and update `catalog` and `schema` to match your own
3. Run the notebook - it will take a few minutes and create many tables

#### Run the App Locally
1. Clone this repository to your local machine
2. Open a terminal, navigate to the root folder
3. Confirm your DEFAULT auth profile is setup, run `databricks auth profiles`, it should show valid and the host should match your workspace
4. Run `uv sync`- this will create a virtual environment and install required packages and Python version
5. Run `source .venv/bin/activate`
6. Open `app/app.yaml` - update `LAKEBASE_SCHEMA` to the same schema you used in Data Setup
7. Open `databricks.yml` update catalog and schema variables to the same you used in Data Setup
8. In the terminal run `databricks bundle validate` - it should pass, then run `databricks bundle deploy`, this will take a few minutes and will create a Databricks App, Lakebase Instance, and synced Delta tables.
9. Rename `.env-example` rto `.env`, go to the newly created Lakebase Instance (name is in `database.yml`) in your workspace, populate `.env` with the connection details. 
10. Run `python app.py` - this will start a local Plotly Dash App, try it out

#### Deploying the Databricks App
1. In your workspace, go to your Lakebase Instance, open a query editor. In the editor enter the below - fill in your app id

``` 
CREATE EXTENSION IF NOT EXISTS postgis SCHEMA public;
  
GRANT USAGE ON SCHEMA david_hurley TO "app-id";

GRANT SELECT ON TABLE alberta_wdrill_wells_postgres TO "app-id";

GRANT SELECT ON TABLE alberta_wdrill_combined_location_lithology_postgres TO "app-id";
```

2. Start the App with `databricks bundle run alberta-water-well-explorer` - go to the workspace and open the app, try it out


