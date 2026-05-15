import json
import os
import re
from pathlib import Path

from databricks import sql as dbsql
from flask import Flask, abort, jsonify, render_template, request

APP_DIR = Path(__file__).parent
ORG = os.environ.get("APP_ORG", "unknown")
HOST = os.environ.get("DATABRICKS_HOST", "").rstrip("/").replace("https://", "")
WAREHOUSE_HTTP_PATH = os.environ.get("DATABRICKS_WAREHOUSE_HTTP_PATH", "")
STATUS_CATALOG = os.environ.get("STATUS_CATALOG", "classic_stable_been2c_catalog")
STATUS_SCHEMA = os.environ.get("STATUS_SCHEMA", "business_reports")
STATUS_TABLE = f"`{STATUS_CATALOG}`.`{STATUS_SCHEMA}`.`report_status`"

VALID_STATUSES = {"draft", "not_reviewed", "reviewed"}

app = Flask(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def obo_token() -> str:
    """Return the user's OBO token injected by Databricks Apps, or fallback to env."""
    return (
        request.headers.get("X-Forwarded-Access-Token")
        or os.environ.get("DATABRICKS_TOKEN", "")
    )


def get_connection(token: str):
    return dbsql.connect(
        server_hostname=HOST,
        http_path=WAREHOUSE_HTTP_PATH,
        access_token=token,
    )


def parse_named_blocks(sql_text: str) -> dict:
    """Split a SQL file into a dict of {name: query} on '-- name: <id>' markers."""
    blocks: dict = {}
    current_name: str | None = None
    current_lines: list = []

    for line in sql_text.splitlines():
        m = re.match(r"--\s*name:\s*(\w+)", line.strip())
        if m:
            if current_name is not None:
                blocks[current_name] = "\n".join(current_lines).strip()
            current_name = m.group(1)
            current_lines = []
        elif current_name is not None:
            current_lines.append(line)

    if current_name is not None:
        blocks[current_name] = "\n".join(current_lines).strip()

    return blocks


def run_named_queries(slug: str, token: str) -> dict:
    """Execute every named query for a report slug; return {name: [row_dict, ...]}."""
    query_file = APP_DIR / "queries" / f"{slug}.sql"
    if not query_file.exists():
        return {}

    blocks = parse_named_blocks(query_file.read_text())
    results: dict = {}

    with get_connection(token) as conn:
        with conn.cursor() as cur:
            for name, query in blocks.items():
                if not query:
                    continue
                cur.execute(query)
                cols = [d[0] for d in cur.description]
                results[name] = [dict(zip(cols, row)) for row in cur.fetchall()]

    return results


def load_manifest() -> dict:
    manifest_path = APP_DIR / "reports.json"
    if not manifest_path.exists():
        return {"reports": []}
    return json.loads(manifest_path.read_text())


def _safe_slug(slug: str) -> str:
    """Reject slugs that could be used for injection."""
    if not re.fullmatch(r"[a-z0-9_-]+", slug):
        abort(400)
    return slug


# ---------------------------------------------------------------------------
# Status helpers
# ---------------------------------------------------------------------------

def fetch_statuses(token: str) -> dict:
    """Return {slug: {status, updated_at, updated_by}} for this org."""
    try:
        with get_connection(token) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT slug, status, updated_at, updated_by "
                    f"FROM {STATUS_TABLE} WHERE app_org = '{ORG}'"
                )
                return {
                    row[0]: {
                        "status": row[1],
                        "updated_at": str(row[2]) if row[2] else "",
                        "updated_by": row[3] or "",
                    }
                    for row in cur.fetchall()
                }
    except Exception:
        return {}


def lazy_seed_statuses(slugs: list, token: str) -> None:
    """INSERT 'draft' rows for any slug not yet in the status table. Best-effort."""
    if not slugs:
        return
    try:
        with get_connection(token) as conn:
            with conn.cursor() as cur:
                for slug in slugs:
                    cur.execute(
                        f"""MERGE INTO {STATUS_TABLE} AS t
                        USING (SELECT '{ORG}' AS app_org, '{slug}' AS slug) AS s
                        ON t.app_org = s.app_org AND t.slug = s.slug
                        WHEN NOT MATCHED THEN
                          INSERT (app_org, slug, status, updated_at, updated_by)
                          VALUES ('{ORG}', '{slug}', 'draft',
                                  current_timestamp(), current_user())"""
                    )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    token = obo_token()
    manifest = load_manifest()
    reports = manifest.get("reports", [])
    statuses = fetch_statuses(token)

    missing = [r["slug"] for r in reports if r["slug"] not in statuses]
    if missing:
        lazy_seed_statuses(missing, token)
        statuses = fetch_statuses(token)

    return render_template("index.html", reports=reports, statuses=statuses, org=ORG)


@app.route("/reports/<slug>")
def report(slug: str):
    slug = _safe_slug(slug)
    manifest = load_manifest()
    known_slugs = {r["slug"] for r in manifest.get("reports", [])}
    if slug not in known_slugs:
        abort(404)

    token = obo_token()
    data = run_named_queries(slug, token)

    statuses = fetch_statuses(token)
    if slug not in statuses:
        lazy_seed_statuses([slug], token)
        statuses = fetch_statuses(token)

    status_info = statuses.get(slug, {"status": "draft", "updated_at": "", "updated_by": ""})

    report_meta = next((r for r in manifest["reports"] if r["slug"] == slug), {})
    return render_template(
        f"reports/{slug}.html",
        data=data,
        slug=slug,
        status=status_info,
        report=report_meta,
        org=ORG,
    )


@app.route("/api/query/<slug>/<name>")
def api_query(slug: str, name: str):
    slug = _safe_slug(slug)
    if not re.fullmatch(r"\w+", name):
        abort(400)
    token = obo_token()
    results = run_named_queries(slug, token)
    if name not in results:
        abort(404)
    return jsonify(results[name])


@app.route("/api/status/<slug>", methods=["POST"])
def set_status(slug: str):
    slug = _safe_slug(slug)
    payload = request.get_json(silent=True) or {}
    new_status = payload.get("status", "")
    if new_status not in VALID_STATUSES:
        return jsonify({"error": f"status must be one of {sorted(VALID_STATUSES)}"}), 400

    token = obo_token()
    try:
        with get_connection(token) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""MERGE INTO {STATUS_TABLE} AS t
                    USING (SELECT '{ORG}' AS app_org, '{slug}' AS slug) AS s
                    ON t.app_org = s.app_org AND t.slug = s.slug
                    WHEN MATCHED THEN
                      UPDATE SET status = '{new_status}',
                                 updated_at = current_timestamp(),
                                 updated_by = current_user()
                    WHEN NOT MATCHED THEN
                      INSERT (app_org, slug, status, updated_at, updated_by)
                      VALUES ('{ORG}', '{slug}', '{new_status}',
                              current_timestamp(), current_user())"""
                )
        return jsonify({"ok": True, "status": new_status})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)
