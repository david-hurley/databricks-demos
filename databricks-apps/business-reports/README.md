# Business Reports Apps

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

Stored in `<your-catalog>.business_reports.report_status` (Delta table, OBO writes). Statuses: `draft`, `not_reviewed`, `reviewed`. Editable via the status control on each report page.

## Deploying a new report

Use Claude with the `deploy-html-report` skill:

> "Deploy this report to the Finance app"

Claude will parameterize the HTML, write the SQL queries, update `reports.json`, commit, push, and run `databricks --profile <your-workspace-profile> apps deploy reports-<org>`.

## Infrastructure

- **Workspace**: `<your-workspace>.cloud.databricks.com`
- **Warehouse**: Configure via `sql-warehouse` resource binding in app definition
- **Status table**: `<your-catalog>.business_reports.report_status`
- **Profile**: Set your Databricks CLI profile in `~/.databrickscfg`
