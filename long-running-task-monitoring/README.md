# Long Running Task Monitoring
In addition to monitoring costs it is also useful to monitor and be alerted for long-running tasks. 

The `LongRunningTasks.ipynb` creates 3 tables to store details around jobs, queries, and clusters that exceed the set time thresholds. This notebook can be scheduled to run every few hours and the tables can be paired with a SQL Alert which can be added to the pipeline.

The `Long Running Task Monitor` dashboard references the tables. 