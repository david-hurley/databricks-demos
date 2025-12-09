# Alberta Water Well Spatial Explorer

An interactive web application for subsurface data related to drilled water wells in Alberta. Packaged with Databricks Asset Bundles for quick deployment.

## Overview

This application demonstrates how to build a low-latency Databricks App for quering spatial data with freeform polygons. Draw a polygon on the map and view the scatter plot of material composition vs depth for water bearing material. 

**Uses**
- Databricks App
- Databricks Lakebase (Postgres)
- PostGIS

<img width="1698" height="777" alt="image" src="https://github.com/user-attachments/assets/197429a1-02c7-40ed-8e6a-88f49c1d8e08" />

<img width="1698" height="819" alt="image" src="https://github.com/user-attachments/assets/9c231e31-6dab-4b77-ade1-1756d76aa6b9" />

## Getting Started

**Prerequisites**
- **Databricks Workspace**
- **Databricks CLI**, setup and authenticated to workspace
- **Python**, ideally 3.11+
- **uv**, used for package and Python management (`pip install uv`)

#### Data Setup
1. Clone this repository to your Databricks workspace
2. Open `001-setup.ipynb` and update `catalog` and `schema` to match your own
3. Run the notebook - it will take a few minutes and create many tables, for this demo we will leverage the `alberta_wdrill_combined_location_lithology` and `alberta_wdrill_wells` tables
4. Naviate to your catalog and schema in the workspace and confirm the tables are created

#### Deploy the Databricks Resources and Run the App Locally and in Databricks
1. Clone this repository to your local machine
2. Open a terminal, navigate to the `databricks-demos/water-well-spatial-explorer-app` directory
3. Confirm your DEFAULT auth profile is setup, run `databricks auth profiles`, it should show valid and the host should match your workspace
4. Run `uv sync`- this will create a virtual environment and install required packages and Python version
5. Run `source .venv/bin/activate`
6. Open `app/app.yaml` - update `LAKEBASE_SCHEMA` to the same schema you used in Data Setup
7. Open `databricks.yml` update catalog and schema variables to the same you used in Data Setup
8. In the terminal run `databricks bundle validate` - it should pass, then run `databricks bundle deploy`, this will take a few minutes and will create a Databricks App, Lakebase Instance, and synced Delta tables.
9. Rename `.env-example` rto `.env`, in your Databricks workspace under compute -> Lakebase Postgres, open the newly created Lakebase Instance (you can find the instance name in `resources/database.yml`), use the Connection Details table to populate the `.env`. Match `LAKEBASE_SCHEMA` to what is in `app/app.yaml`
10. Open your workspace, go to your Lakebase Instance, open a query editor. In the editor enter the below. You will need to copy your App ID, found in the app overview page. The below gives the necessary permissions for the app to the Lakebase Postgres schema and tables.

``` 
CREATE EXTENSION IF NOT EXISTS postgis SCHEMA public;
  
GRANT USAGE ON SCHEMA david_hurley TO "app-id";

GRANT SELECT ON TABLE alberta_wdrill_wells_postgres TO "app-id";

GRANT SELECT ON TABLE alberta_wdrill_combined_location_lithology_postgres TO "app-id";
```
11. Run the app locally: Navigate to `app/` and run `python app.py` - this will start a local Plotly Dash App, try it out
12. Run the App in Databricks: `databricks bundle run alberta-water-well-explorer`, go to the workspace and open the app, try it out

