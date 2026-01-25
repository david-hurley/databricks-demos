# AI Parse Document Visualizer App

A Databricks application for visualizing and exploring documents processed with the `ai_parse_document()` function. This app provides an interactive interface to view parsed document results with bounding boxes, element details, and multi-page navigation. Supported document types are PDF, JPG, PNG, DOC, DOCX, PPT, and PPTX, see the [docs](https://docs.databricks.com/aws/en/sql/language-manual/functions/ai_parse_document) for details.

<img width="1612" height="755" alt="image" src="https://github.com/user-attachments/assets/80572dd1-d0fd-49fa-8531-c36ca6047d9b" />

## Setup Instructions

**1. Create a new volume in your Unity Catalog and add 2 empty directories named "input" and "output" - upload a few documents to "input"**


<img width="906" height="409" alt="image" src="https://github.com/user-attachments/assets/08f4814c-fd54-497c-8e46-a94edf63236b" />


**2. Create a new Custom App in Databricks Apps - under "Configure" and "Add Resources" give the app "CAN USE" permission on a SQL warehouse and "CAN READ" permission on the UC Volume created in Step 1**


<img width="636" height="409" alt="image" src="https://github.com/user-attachments/assets/af72dd3f-7f07-4614-964f-316087dffa79" />


**3. In your Databricks Workspace select "Create" and choose "Git Folder" - paste "https://github.com/david-hurley/databricks-demos.git" as the URL**


**4. In the new folder, navigate to "ai-parse-doc-visualizer-app" and open the "ai_parse_visualizer_app_backend.ipynb" notebook. Fill in the catalog, schema, and volume from Step 1 and add a results table name - run the notebook. This may take several minutes depending on number of files and length**


**5. In the same folder, open the "app.yaml" file and update the catalog, schema, and table value to match what you used in Step 4**


<img width="315" height="334" alt="image" src="https://github.com/user-attachments/assets/fd5421df-c324-4cb9-920d-3767d179904d" />


**6. Now open the App you created in Step 2 and select "Deploy" and point to the "ai-parse-doc-visualizer-app" folder in your workspace**


**7. After Step 4 has completed - copy the App Id from the App overview page. Open the newly created results table in your schema and select "Permissions". Grant the App Id "SELECT" permission**


<img width="720" height="254" alt="image" src="https://github.com/user-attachments/assets/bd99d915-833b-48fb-8aed-287202fa08a0" />


**8. Refresh the App page - you should now see a list of the documents you uploaded and be able to visualize how well `ai_parse_document()` performed**
