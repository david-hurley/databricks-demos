<img src=https://raw.githubusercontent.com/databricks-industry-solutions/.github/main/profile/solacc_logo.png width="600px">

# Databricks Apps Development and Deployment Accelerator

# Overview

### Problem
Deploying custom enterprise data and AI applications can be burdensome. It often requires a person or team that is focused on application deployment, authentication, permissions, networking, and more (i.e. DevOps). 

The problem is this slows time to value for data and AI teams and introduces processes that require specialized knowledge. 

### Problem Scenario
Imagine this - you are on Azure and have built a custom Python or Node.js application. Your application is simple, it is designed to give users within the orginization access to data (i.e. CRUD operations). This application runs great locally but now you need to deploy the app so that users can interact. 

In Azure, you would most likely use Azure WebApps. In this case, to deploy the application, you would need to follow roughly these steps:

1. Containerize the application code and dependencies
2. Register, version, and potentially orchestrate the container
3. Deploy the container to Azure WebApp - setup networking on app, authentication for users, permissions for users to access data outside app memory and permissions for app to write state
4. Automate deployment with GitHub Action workflows - configure GitHub runner with permissions to container registry and Azure WebApp

Note - replace Azure WebApps with any plethora of app hosting services and the steps are similar or the same. 

### Root Cause
The primary driver of deployment challenges is the application layer does not "live" next to the data layer. 

### Databricks Apps Solution

# End-to-End Databricks App Demo - Streamlit
The application development and deployment cycle can be broken into 3 stages. 
1. Develop and run the app locally
2. Deploy the app to a Databricks Dev workspace
3. Enable GitHub Actions to deploy the app to a Databricks Prod workspace

### Prerequisite 
- Need Python 3.9+
- Need the [Databricks CLI](https://docs.databricks.com/aws/en/dev-tools/cli/install]) on a local machine
- Need a GitHub account with Admin rights at the repository level
- Need a Databricks workspace that is Unity Catalog enabled with Databricks Apps feature switched on and access to SQL Warehouse compute

### Step 1: Develop Locally
1. Clone this repo and open the `streamlit-app-e2e-deployment` folder, `git clone https://github.com/david-hurley/databricks-demos.git`
1. Use the Databricks CLI to setup workspace authentication
    a. If you have an existing Databricks Default configuration profile, run `databricks auth profiles` to check, then skip step B. 
    b. To create a new Default or custom named configuration profile follow the [documentation](https://docs.databricks.com/aws/en/dev-tools/cli/authentication)
2. In the root of the repository run `source .venv/bin/activate` to launch a virtual environment
3. Copy the SQL Warehouse compute ID from the workspace, found next to name on SQL Warehouse details ![sql-warehouse-id](./artifacts/image.png)
4. Export the SQL Warehouse ID as an environment variable `export SQL_WAREHOUSE_ID=XXX`
5. Run the Streamlit app from repository root with `streamlit run app/app.py`

### Step 2: Test App in Databricks Dev Workspace




### Step 3: Automate App Deployment to Databricks Prd Workspace


##### Development App Environment
1. Use DABs to manage the Databricks App IaC
2. Deploy to test using DABs
`databricks bundle validate`
`databricks bundle deploy`
`databricks bundle summary` --> shows where code has been synced
`databricks bundle run streamlit_auth_demo`
`databricks bundle summary` --> now it shows the running app



## Business Problem

The UK's transition to Market-Wide Half-Hourly Settlement (MHHS) marks a significant regulatory shift aimed at modernising electricity billing and promoting a more flexible, efficient energy market. Under MHHS, all electricity consumption data will be settled on a half-hourly basis, reflecting actual usage patterns in near-real time.

For energy suppliers, this change introduces both opportunities and challenges. Accurate forecasting becomes mission-critical: suppliers must predict customer demand at granular 30-minute intervals to manage their trading positions effectively. Forecasting errors can lead to imbalanced positions—buying too much or too little power—which exposes suppliers to costly imbalance charges and volatile trading prices in wholesale markets.

In this new landscape, the ability to harness smart meter data, invest in predictive analytics, and optimise trading strategies will be essential for maintaining competitiveness and mitigating financial risk.


## Proposed Solution

This solution accelerator looks at using the Databricks Lakehouse platform to work with half-hourly smart meter data.
We run you through:
- Obtaining and processing weather data in unusual formats (`era5`, `ifs`)
- Processing geographical data to align smart meter locations to nearby features (weather, administrative boundaries)
- Pre-processing and validating data before it is ready for use
- Extracting features from the data to augment our forecasts
- Creating and evaluating forecasts with both prophet and `ai_forecast()`

## Reference Architecture
<img src="./docs/imgs/energy-sa-high-level-flow.png" width="1200">

## Key Services and Costs

We recommend you treat these notebooks as referential material.
Running the workflow and the notebook is possible, however we load around 12Gb of smart meter data and several Gb of geographical weather data. This then goes through some significant processing. While the end to end flow can take under an hour to run, there is a compute cost associated which you should be aware of. Effort has been made to minimise this cost, and multiple runs of this accelerator will default to skipping re-processing.


## Table of Contents

The notebooks are numbered for convenience. The stages in the reference architecture break down into the following notebooks:

|stage                |notebook|
|---------------------|-|
|Source & Ingest      |[01a_ingest_meter_data](./src/01a_ingest_meter_data.ipynb)|
|Source & Ingest      |[01b_ingest_historic_weather_data](./src/01b_ingest_historic_weather_data.ipynb)|
|Source & Ingest      |[01c_ingest_forecast_weather_data](./src/01c_ingest_forecast_weather_data.ipynb)|
|Data clean-up & prep |[02_interactive_exploration](./src/02_interactive_exploration.ipynb)|
|Source & Ingest      |[02_data_prep_for_feature_engineering](./src/02_data_prep_for_feature_engineering.ipynb)|
|Feature engineering  |[03_feature_engineering](./src/03_feature_engineering.ipynb)|
|Model training       |[04a_forecast_with_prophet_and_exogenous_inputs_unscaled](./src/04a_forecast_with_prophet_and_exogenous_inputs_unscaled.ipynb)|
|Model training       |[04b_forecast_with_prophet_and_exogenous_inputs_scaled](./src/04b_forecast_with_prophet_and_exogenous_inputs_scaled.ipynb)|
|Model training       |[04c_ai_forecasting_uk_energy](./src/04c_ai_forecasting_uk_energy.ipynb)|
|Evaluation           |[05_forecast_evaluation](./src/05_forecast_evaluation.ipynb)|


## Deploying the accelerator

If you want to deploy the accelerator as a job so you can follow the DAG between tasks, or even run it yourselves you can use Databricks asset bundles in the workspace to do so.

You'll need to create your own secret scope to securely store your API key for the [ECMWF Web Api](https://www.ecmwf.int/en/computing/software/ecmwf-web-api).

Then, all you need to do is navigate into the folder: `.databricks/bundle/dev/` and make a copy of the `variable-overrides-template.json` into the same folder, rename it to `variable-overrides.json` and populate it with your values. 

This will parameterise the first task in the job (The notebook [00_project_setup](./src/00_project_setup.ipynb)) with your settings, and be pulled into all subsequent notebooks via the `%run includes/common_funtions_and_imports` call.

If you want to run it manually, you need to open the notebook [00_project_setup](./src/00_project_setup.ipynb) in databricks, set the widget values appropriately and run it which will create the relevant `config.json` file for you in the project folder.

You can also reference this diagram for the bundle deployment flow:

<img src="./docs/imgs/energy-sa-deployment-flow.png" width="1200">


## Authors
<stuart.lynn@databricks.com>
<sam.lecorre@databricks.com>
<kyra.wulfert@databricks.com>

## Project support 

Please note the code in this project is provided for your exploration only, and are not formally supported by Databricks with Service Level Agreements (SLAs). They are provided AS-IS and we do not make any guarantees of any kind. Please do not submit a support ticket relating to any issues arising from the use of these projects. The source in this project is provided subject to the Databricks [License](./LICENSE.md). All included or referenced third party libraries are subject to the licenses set forth below.

Any issues discovered through the use of this project should be filed as GitHub Issues on the Repo. They will be reviewed as time permits, but there are no formal SLAs for support.

## License

&copy; 2025 Databricks, Inc. All rights reserved. The source in this notebook is provided subject to the Databricks License [https://databricks.com/db-license-source].  All included or referenced third party libraries are subject to the licenses set forth below.