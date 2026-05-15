import json
import os
import re
from pathlib import Path

from databricks import sql as dbsql
from databricks.sdk.core import Config
from flask import Flask, abort, jsonify, render_template, request

APP_DIR = Path(__file__).parent
ORG = os.environ.get("APP_ORG", "unknown")
STATUS_CATALOG = os.environ.get("STATUS_CATALOG", "classic_stable_been2c_catalog")
STATUS_SCHEMA = os.environ.get("STATUS_SCHEMA", "business_reports")
STATUS_TABLE = f"`{STATUS_CATALOG}`.`{STATUS_SCHEMA}`.`report_status`"

VALID_STATUSES = {"draft", "not_reviewed", "reviewed"}

# Databricks Apps injects these two vars automatically when a warehouse resource
# is configured — use them directly, no https:// stripping needed.
HOSTNAME  = os.environ.get("DATABRICKS_SERVER_HOSTNAME", "")
HTTP_PATH = os.environ.get("DATABRICKS_HTTP_PATH", "")

# Ambient Config for app SP credentials (status table reads/writes)
_SP_CFG = Config()

app = Flask(__name__)


# ---------------------------------------------------------------------------
# Connection helpers
# ---------------------------------------------------------------------------

def _obo_token() -> str:
    """User OBO token injected by Databricks Apps, with env fallback for local dev."""
    return (
        request.headers.get("X-Forwarded-Access-Token")
        or os.environ.get("DATABRICKS_TOKEN", "")
    )


def _obo_conn(token: str):
    """SQL connection using the user's OBO token (user-level read authorization)."""
    return dbsql.connect(
        server_hostname=HOSTNAME,
        http_path=HTTP_PATH,
        access_token=token,
    )


def _sp_conn():
    """SQL connection using the app SP (for status table reads/writes)."""
    return dbsql.connect(
        server_hostname=HOSTNAME,
        http_path=HTTP_PATH,
        credentials_provider=lambda: _SP_CFG.authenticate,
    )


# ---------------------------------------------------------------------------
# SQL helpers
# ---------------------------------------------------------------------------

def parse_named_blocks(sql_text: str) -> dict:
    """Split a SQL file into {name: query} on '-- name: <id>' markers."""
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
    """Execute every named query in queries/<slug>.sql with the user's OBO token."""
    query_file = APP_DIR / "queries" / f"{slug}.sql"
    if not query_file.exists():
        return {}

    blocks = parse_named_blocks(query_file.read_text())
    results: dict = {}

    with _obo_conn(token) as conn:
        with conn.cursor() as cur:
            for name, query in blocks.items():
                if not query:
                    continue
                try:
                    cur.execute(query)
                    cols = [d[0] for d in cur.description]
                    results[name] = [dict(zip(cols, row)) for row in cur.fetchall()]
                except Exception as e:
                    app.logger.error("Query %s/%s failed: %s", slug, name, e)
                    results[name] = []

    return results


def _sp_exec(statement: str) -> list:
    """Run a SQL statement using the app SP (for status table operations)."""
    with _sp_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(statement)
            if cur.description:
                cols = [d[0] for d in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
    return []


def load_manifest() -> dict:
    manifest_path = APP_DIR / "reports.json"
    if not manifest_path.exists():
        return {"reports": []}
    return json.loads(manifest_path.read_text())


def _safe_slug(slug: str) -> str:
    if not re.fullmatch(r"[a-z0-9_-]+", slug):
        abort(400)
    return slug


# ---------------------------------------------------------------------------
# Status helpers  (use app SP so status writes always succeed)
# ---------------------------------------------------------------------------

def fetch_statuses() -> dict:
    try:
        rows = _sp_exec(
            f"SELECT slug, status, updated_at, updated_by "
            f"FROM {STATUS_TABLE} WHERE app_org = '{ORG}'"
        )
        return {
            r["slug"]: {
                "status": r["status"],
                "updated_at": str(r.get("updated_at", "")),
                "updated_by": r.get("updated_by", "") or "",
            }
            for r in rows
        }
    except Exception as e:
        app.logger.warning("fetch_statuses failed: %s", e)
        return {}


def lazy_seed_statuses(slugs: list) -> None:
    """INSERT 'draft' rows for any slug not yet in the status table. Best-effort."""
    for slug in slugs:
        try:
            _sp_exec(
                f"""MERGE INTO {STATUS_TABLE} AS t
                USING (SELECT '{ORG}' AS app_org, '{slug}' AS slug) AS s
                ON t.app_org = s.app_org AND t.slug = s.slug
                WHEN NOT MATCHED THEN
                  INSERT (app_org, slug, status, updated_at, updated_by)
                  VALUES ('{ORG}', '{slug}', 'draft',
                          current_timestamp(), current_user())"""
            )
        except Exception as e:
            app.logger.warning("lazy_seed_statuses(%s) failed: %s", slug, e)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    manifest = load_manifest()
    reports = manifest.get("reports", [])
    statuses = fetch_statuses()

    missing = [r["slug"] for r in reports if r["slug"] not in statuses]
    if missing:
        lazy_seed_statuses(missing)
        statuses = fetch_statuses()

    return render_template("index.html", reports=reports, statuses=statuses, org=ORG)


@app.route("/reports/<slug>")
def report(slug: str):
    slug = _safe_slug(slug)
    manifest = load_manifest()
    known_slugs = {r["slug"] for r in manifest.get("reports", [])}
    if slug not in known_slugs:
        abort(404)

    token = _obo_token()
    data = run_named_queries(slug, token)

    statuses = fetch_statuses()
    if slug not in statuses:
        lazy_seed_statuses([slug])
        statuses = fetch_statuses()

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
    token = _obo_token()
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

    try:
        _sp_exec(
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
