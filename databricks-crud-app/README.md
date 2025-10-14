# Databricks CRUD App

Compare Lakebase PostgreSQL and Delta

### Getting Started Locally
1. Create a authenticated profile using the Databricks CLI `databricks auth login --host <workspace-url>`
2. Confirm profiles with `databricks auth profiles`
3. Clone this repo and open `databricks-crud-app`
4. Open a terminal create a virtual environment. Easiest is to use `uv` and run `uv init` and then `uv venv venv --python 3.11`. Then run `source venv/bin/activate` and `uv pip install -r requirements.txt`
5. Open `app/config.py` update the variables
6. Run the app locally `python app/app.py` - first time it take a few seconds to build connections

### Deploy App to Dev
You can either create a app via the UI and use the UI commands or use Databricks Asset Bundles

With Asset Bundles, you can define all the resources the app needs
1. validate the bundle `databricks bundle validate`
2. deploy the code `databricks bundle deploy`
3. start and run the app `databricks bundle run <app-name>`
4. The app is now deployed BUT we need to give the app SP the correct permissions over the Delta table and Postgres roles

### Automate to Prod
With an asset bundle you can now create a GitHub Action that deploys our app when a PR is merged
1. define GitHub Action workflow

