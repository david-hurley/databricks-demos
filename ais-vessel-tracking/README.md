# H3 Vessel Activity Visualization

A professional Dash application for visualizing vessel activity using H3 hexagonal grid system, connected to Databricks Managed Postgres.

## Features

- 🗺️ **Interactive H3 Map** - Visualize vessel activity across resolution 7 H3 hexagons
- ⏱️ **Time Animation** - Navigate through 768 hours of historical data with play/pause controls
- 📊 **Linear Color Scale** - Clear visualization with 6 color buckets (max 100 vessels)
- ⚡ **Fast Queries** - Connection pooling with OAuth token rotation
- 🎨 **Professional UI** - Modern, sleek design

## Quick Start

### Local Development

```bash
# Install dependencies
uv sync

# Run the app
uv run python app.py

# Open browser to http://localhost:8050
```

### Deploy to Databricks

```bash
# Deploy and run
databricks bundle deploy -t dev --profile DEFAULT
databricks bundle run h3_vessel_activity_app -t dev --profile DEFAULT

# View logs
databricks apps logs h3-vessel-activity --profile DEFAULT
```

## Architecture

- **Frontend**: Dash + Dash Leaflet
- **Backend**: Databricks Managed Postgres (psycopg connection pool)
- **Data**: H3 Resolution 7 vessel activity (March-April 2024)
- **Authentication**: OAuth token rotation via Databricks SDK

## Configuration

The app automatically configures itself for both local and deployed environments:

- **Local**: Uses Databricks CLI authentication
- **Deployed**: Uses in-app OAuth tokens with automatic refresh

Environment variables (set in `databricks.yml` for deployment):
- `PGHOST`: Postgres host
- `PGDATABASE`: Database name
- `PGPORT`: Port (default: 5432)
- `INSTANCE_NAME`: Databricks instance name

## Database Schema

```sql
CREATE TABLE david_hurley.ais_records_curated_pg (
    resolution INTEGER,
    h3_cell BIGINT,
    hour_ts TIMESTAMP,
    ship_count BIGINT
);
```

## Tech Stack

- **Dash** - Web framework
- **Dash Leaflet** - Interactive maps
- **H3** - Hexagonal hierarchical geospatial indexing
- **psycopg** + **psycopg-pool** - PostgreSQL connection pooling
- **Pandas** - Data manipulation
- **Databricks SDK** - Authentication & API access

## Project Structure

```
h3-viz-app/
├── app.py              # Main Dash application
├── databricks.yml      # Databricks Asset Bundle config
├── requirements.txt    # Python dependencies
├── pyproject.toml      # UV project configuration
├── uv.lock             # Lock file
└── README.md           # This file
```
