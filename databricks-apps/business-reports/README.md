# Clio Analytics — Business Reports Apps

Live, OBO-authenticated HTML reports deployed as Databricks Apps for Finance, HR, Sales, and Marketing.

## Architecture

Each business org has its own Databricks App (`reports-finance`, `reports-hr`, `reports-sales`, `reports-marketing`). All apps share the same Flask skeleton in `shared/app_skeleton/`. Reports are deployed here by Claude using the `deploy-html-report` skill.

### Apps

| App Name | Source Path | Org |
|---|---|---|
| `reports-finance`   | `databricks-apps/business-reports/apps/finance/`   | Finance |
| `reports-hr`        | `databricks-apps/business-reports/apps/hr/`        | HR |
| `reports-sales`     | `databricks-apps/business-reports/apps/sales/`     | Sales |
| `reports-marketing` | `databricks-apps/business-reports/apps/marketing/` | Marketing |

### Per-org layout

```
apps/<org>/
├── app.py            # Flask app (copy of shared/app_skeleton/app.py)
├── app.yaml          # Databricks Apps manifest
├── requirements.txt
├── reports.json      # Report manifest (id, slug, title, owner, dates)
├── templates/
│   ├── _base.html        # Shared layout (copy of shared skeleton)
│   ├── index.html        # Table of contents
│   └── reports/
│       └── <slug>.html   # One Jinja2 template per report
├── queries/
│   └── <slug>.sql        # Named SQL blocks for each report
└── static/
```

### How data gets live

Every `GET /reports/<slug>` runs the named SQL blocks in `queries/<slug>.sql` using the user's OBO token (`X-Forwarded-Access-Token`) against the shared SQL warehouse. Results are injected into the Jinja template as `{{ data.<query_name> }}`.

### Report status

Stored in `classic_stable_been2c_catalog.business_reports.report_status` (Delta table, OBO writes). Statuses: `draft`, `not_reviewed`, `reviewed`. Lazily seeded on first page view; editable via the status control on each report page.

## Deploying a new report

Use Claude with the `deploy-html-report` skill:

> "Deploy this report to the Finance app"

Claude will parameterize the HTML, write the SQL queries, update `reports.json`, commit, push, and run `databricks --profile fevm-classic-stable-been2c apps deploy reports-<org>`.

## Infrastructure

- **Workspace**: `fevm-classic-stable-been2c.cloud.databricks.com`
- **Warehouse**: `Serverless Starter Warehouse` (`0709f445a3d3d88a`)
- **Status table**: `classic_stable_been2c_catalog.business_reports.report_status`
- **Profile**: `fevm-classic-stable-been2c`
