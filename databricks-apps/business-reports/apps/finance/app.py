import json
import os
import re
import traceback
from pathlib import Path

from databricks import sql
from databricks.sdk.core import Config
from flask import Flask, abort, jsonify, render_template, request

APP_DIR = Path(__file__).parent
ORG = os.environ.get("APP_ORG", "unknown")
STATUS_CATALOG = os.environ.get("STATUS_CATALOG", "classic_stable_been2c_catalog")
STATUS_SCHEMA = os.environ.get("STATUS_SCHEMA", "business_reports")

STATUS_TABLE = f"`{STATUS_CATALOG}`.`{STATUS_SCHEMA}`.`report_status`"
VALID_STATUSES = {"draft", "not_reviewed", "reviewed"}

# Canonical Databricks Apps pattern:
#   Config() reads host from the runtime environment automatically.
#   DATABRICKS_WAREHOUSE_ID is injected via valueFrom: sql-warehouse resource binding.
cfg = Config()
WAREHOUSE_ID = os.environ.get("DATABRICKS_WAREHOUSE_ID", "")
HTTP_PATH = f"/sql/1.0/warehouses/{WAREHOUSE_ID}"

app = Flask(__name__)


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def user_token() -> str:
    return request.headers.get("x-forwarded-access-token", "")


def user_conn():
    return sql.connect(
        server_hostname=cfg.host,
        http_path=HTTP_PATH,
        access_token=user_token(),
    )


# ---------------------------------------------------------------------------
# SQL helpers
# ---------------------------------------------------------------------------

def parse_named_blocks(sql_text: str) -> dict:
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


def run_named_queries(slug: str) -> dict:
    query_file = APP_DIR / "queries" / f"{slug}.sql"
    if not query_file.exists():
        return {}

    blocks = parse_named_blocks(query_file.read_text())
    results: dict = {}

    with user_conn() as conn:
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


def fetch_statuses(slugs: list[str]) -> dict:
    if not slugs:
        return {}
    placeholders = ", ".join("?" * len(slugs))
    query = (
        f"SELECT slug, status, updated_at, updated_by "
        f"FROM {STATUS_TABLE} "
        f"WHERE app_org = ? AND slug IN ({placeholders})"
    )
    try:
        with user_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(query, [ORG] + slugs)
                cols = [d[0] for d in cur.description]
                return {row[0]: dict(zip(cols, row)) for row in cur.fetchall()}
    except Exception as e:
        app.logger.warning("fetch_statuses failed: %s", e)
        return {}


def upsert_status(slug: str, new_status: str) -> None:
    query = f"""
        MERGE INTO {STATUS_TABLE} AS t
        USING (SELECT ? AS app_org, ? AS slug, ? AS status,
                      current_timestamp() AS updated_at,
                      current_user() AS updated_by) AS s
        ON t.app_org = s.app_org AND t.slug = s.slug
        WHEN MATCHED THEN UPDATE SET
            t.status = s.status,
            t.updated_at = s.updated_at,
            t.updated_by = s.updated_by
        WHEN NOT MATCHED THEN INSERT (app_org, slug, status, updated_at, updated_by)
            VALUES (s.app_org, s.slug, s.status, s.updated_at, s.updated_by)
    """
    with user_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(query, [ORG, slug, new_status])


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
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    manifest = load_manifest()
    reports = manifest.get("reports", [])
    slugs = [r["slug"] for r in reports]
    statuses = fetch_statuses(slugs)
    return render_template("index.html", reports=reports, statuses=statuses, org=ORG)


@app.route("/reports/<slug>")
def report(slug: str):
    slug = _safe_slug(slug)
    manifest = load_manifest()
    known_slugs = {r["slug"] for r in manifest.get("reports", [])}
    if slug not in known_slugs:
        abort(404)

    data = run_named_queries(slug)
    report_meta = next((r for r in manifest["reports"] if r["slug"] == slug), {})
    statuses = fetch_statuses([slug])
    status = statuses.get(slug, {"status": "draft", "updated_at": "", "updated_by": ""})

    return render_template(
        f"reports/{slug}.html",
        data=data,
        slug=slug,
        status=status,
        report=report_meta,
        org=ORG,
    )


@app.route("/api/query/<slug>/<name>")
def api_query(slug: str, name: str):
    slug = _safe_slug(slug)
    if not re.fullmatch(r"\w+", name):
        abort(400)
    results = run_named_queries(slug)
    if name not in results:
        abort(404)
    return jsonify(results[name])


@app.route("/api/status/<slug>", methods=["POST"])
def set_status(slug: str):
    slug = _safe_slug(slug)
    manifest = load_manifest()
    known_slugs = {r["slug"] for r in manifest.get("reports", [])}
    if slug not in known_slugs:
        abort(404)

    body = request.get_json(silent=True) or {}
    new_status = body.get("status", "")
    if new_status not in VALID_STATUSES:
        return jsonify({"error": f"status must be one of {sorted(VALID_STATUSES)}"}), 400

    try:
        upsert_status(slug, new_status)
    except Exception as e:
        app.logger.error("upsert_status failed for %s: %s", slug, e)
        return jsonify({"error": str(e)}), 500

    return jsonify({"slug": slug, "status": new_status, "ok": True})


@app.route("/debug/obo")
def debug_obo():
    token = user_token()
    diag = {
        "host": cfg.host,
        "http_path": HTTP_PATH,
        "warehouse_id": WAREHOUSE_ID,
        "header_present": bool(token),
        "header_len": len(token),
        "user_api_scopes_env": os.environ.get("DATABRICKS_USER_API_SCOPES"),
    }
    try:
        with user_conn() as c:
            with c.cursor() as cur:
                cur.execute("SELECT current_user() AS user, current_timestamp() AS ts")
                row = cur.fetchone()
                diag["query_user"] = row[0]
                diag["query_ts"] = str(row[1])
                diag["ok"] = True
    except Exception as e:
        diag["ok"] = False
        diag["error_type"] = type(e).__name__
        diag["error"] = str(e) or repr(e)
        diag["cause"] = repr(e.__cause__) if e.__cause__ else None
        diag["context"] = repr(e.__context__) if e.__context__ else None
        diag["traceback"] = traceback.format_exc()
    return jsonify(diag)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)
