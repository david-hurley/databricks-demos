# Electricity Load ML Forecast Quick Start

### Steps
##### 1. Create Synthetic Datasets
For the purpose of this demo, we are leveraging electricity load forecast data for Panama City. We want to use this data and create fake tags to emmulate multiple sensors. Under `artifacts` download the `csv` and place in a Unity Catalog managed Volume. Update the Volume path in the first notebook and run the notebook. This will create a new "Bronze" table with 9 fake sensors and varying electricity loads along with weather data. 

NOTE: You do not have to run this notebook if you have existing data. In that case, modify the notebook in Step 2 for the existing data. 

##### 2. Transform Data For ML
This steps shows how to take Unity Catalog Bronze tables with different timestamps and combine the data, add new features, and remove duplicates. The result is a "Silver" table that can be used in ML Forecasting. 