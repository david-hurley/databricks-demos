# AI Parse Document Visualizer App

A Databricks application for visualizing and exploring documents processed with the `ai_parse_document()` function. This app provides an interactive interface to view parsed document results with bounding boxes, element details, and multi-page navigation.

## Features

- **Document Grid View**: Browse all parsed documents from your Unity Catalog table
- **Interactive Visualization**: View documents with highlighted bounding boxes for detected elements
- **Element Details**: Hover over bounding boxes to see detailed element information
- **Multi-Page Support**: Navigate through multi-page documents with Previous/Next buttons and page dropdown
- **Search & Filter**: Search documents by filename or path
- **Real-time Refresh**: Reload data from your table with the refresh button

## Prerequisites

- Databricks workspace with Unity Catalog enabled
- SQL Warehouse for querying parsed document results
- Unity Catalog volume for storing documents
- Documents to parse (PDF, JPG, PNG, DOC, DOCX, PPT, PPTX)

## Setup Instructions

### 1. Create a new volume in your Unity Catalog and add 2 empty directories named "input" and "output" 


Upload a few documents to the `input/` directory to get started.

### 2. Create Databricks App

1. In your Databricks workspace, create a new **Custom App**
2. Under **Configure**, add the following resources:
   - **SQL Warehouse**: Select an active SQL warehouse
   - **UC Volume**: Select the volume you created in Step 1
3. Leave the app empty for now - we'll deploy the files later

### 3. Clone Repository

1. In your Databricks workspace, select **Create** and choose **Git Folder**
2. Clone the repository: `https://github.com/david-hurley/databricks-demos.git`

### 4. Run Setup Notebook

1. Navigate to the cloned folder: `databricks-demos/ai-parse-doc-visualizer-app/`
2. Open the setup notebook: `setup/ai_parse_visualizer_app_backend.ipynb`
3. Fill in the required configuration:
   - Catalog name
   - Schema name
   - Volume name
   - Results table name
4. Run the notebook - this will:
   - Create the results table
   - Parse all documents in the input directory
   - Store results in the Unity Catalog table

**Note**: Processing time depends on the number and size of documents. A 50-page document may take more than 1 minute to process.

### 5. Grant App Permissions

1. Go to your Databricks app (created in Step 2)
2. Copy the **App ID** from the right pane
3. Navigate to your results table (the table name you specified in the setup notebook)
4. Select **Permissions**
5. Grant **SELECT** permission to the App ID

### 6. Update App Configuration

1. In the same `ai-parse-doc-visualizer-app` folder, navigate to the `app/` subfolder
2. Open `app.yaml`
3. Update the following values to match your setup from Step 1:
   - `catalog`: Your catalog name
   - `schema`: Your schema name
   - `table`: Your results table name

### 7. Deploy the App

1. Go back to your Databricks app (created in Step 2)
2. Click **Deploy**
3. Navigate to `databricks-demos/ai-parse-doc-visualizer-app/app/` folder
4. Select the `app` subfolder for deployment

### 8. Configure and Launch

1. Open your deployed app
2. Update the configuration fields:
   - **Catalog**: Your catalog name from Step 1
   - **Schema**: Your schema name from Step 1
   - **Table**: Your results table name from Step 4
3. Click **Refresh** to load your parsed documents
4. Select any document to view its visualization

## Environment Variables

Create a `.env` file in the `app/` directory for local development:

```env
CATALOG=your_catalog
SCHEMA=your_schema
TABLE=your_results_table
SQL_WAREHOUSE_ID=your_warehouse_id
```

See `.env-example` for reference.

## Application Structure

```
ai-parse-doc-visualizer-app/
├── app/
│   ├── app.py                    # Main Dash application
│   ├── app_layout.py             # UI layout components
│   ├── databricks_utils.py       # Database utilities
│   ├── document_renderer.py      # Document visualization logic
│   ├── requirements.txt          # Python dependencies
│   └── assets/                   # Static assets
├── setup/
│   └── ai_parse_visualizer_app_backend.ipynb  # Setup notebook
├── databricks.yml                # Databricks bundle config
└── README.md
```

## Usage

### Viewing Documents

1. Select a document from the grid on the left
2. The document will appear on the right with colored bounding boxes
3. Hover over any bounding box to see element details (type, content, confidence)
4. Use navigation controls to browse multi-page documents

### Searching Documents

Use the search bar to filter documents by filename or volume path.

### Refreshing Data

Click the **↻ Refresh** button to reload the latest data from your table.

## Supported Document Types

- PDF (`.pdf`)
- Images: JPG/JPEG (`.jpg`, `.jpeg`), PNG (`.png`)
- Microsoft Word (`.doc`, `.docx`)
- Microsoft PowerPoint (`.ppt`, `.pptx`)

## Technology Stack

- **Frontend**: Dash (Plotly) with Dash Bootstrap Components
- **Backend**: Databricks SQL Warehouse
- **Storage**: Unity Catalog (tables and volumes)
- **AI Function**: `ai_parse_document()` for document processing

## Demo Repository

This app is part of the Databricks Demos repository: https://github.com/david-hurley/databricks-demos

## License

See the main repository for license information.

