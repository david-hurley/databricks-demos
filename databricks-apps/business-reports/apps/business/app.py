import json
import os
import re
import threading
import time
import traceback
from pathlib import Path

from databricks import sql
from databricks.sdk.core import Config
from flask import Flask, abort, jsonify, render_template, request

APP_DIR = Path(__file__).parent
ORG = os.environ.get("APP_ORG", "unknown")
STATUS_CATALOG = os.environ.get("STATUS_CATALOG", "your_catalog")
STATUS_SCHEMA = os.environ.get("STATUS_SCHEMA", "business_reports")

STATUS_TABLE = f"`{STATUS_CATALOG}`.`{STATUS_SCHEMA}`.`report_status`"
VALID_STATUSES = {"draft", "not_reviewed", "reviewed"}

# Canonical Databricks Apps pattern:
#   Config() reads host from the runtime environment automatically.
#   DATABRICKS_WAREHOUSE_ID is injected via valueFrom: sql-warehouse resource binding.
cfg = Config()
WAREHOUSE_ID = os.environ.get("DATABRICKS_WAREHOUSE_ID", "")
HTTP_PATH = f"/sql/1.0/warehouses/{WAREHOUSE_ID}"

# TTL for cached query results. Set QUERY_CACHE_TTL_SECONDS=0 in app.yaml to disable.
_CACHE_TTL = int(os.environ.get("QUERY_CACHE_TTL_SECONDS", "60"))

app = Flask(__name__)


# ---------------------------------------------------------------------------
# In-memory TTL cache
# ---------------------------------------------------------------------------

class _TTLCache:
    """Thread-safe in-memory cache with per-entry TTL."""

    def __init__(self) -> None:
        self._store: dict = {}
        self._lock = threading.Lock()

    def get(self, key: str):
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if time.monotonic() > expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value, ttl: int) -> None:
        if ttl <= 0:
            return
        with self._lock:
            self._store[key] = (value, time.monotonic() + ttl)

    def clear(self) -> int:
        with self._lock:
            count = len(self._store)
            self._store.clear()
            return count

    def clear_prefix(self, prefix: str) -> int:
        with self._lock:
            keys = [k for k in self._store if k.startswith(prefix)]
            for k in keys:
                del self._store[k]
            return len(keys)

    def stats(self) -> dict:
        with self._lock:
            now = time.monotonic()
            live = {k: v for k, (v, exp) in self._store.items() if exp > now}
            return {"entries": len(live), "keys": list(live.keys()), "ttl_seconds": _CACHE_TTL}


_cache = _TTLCache()


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


def parse_report_queries(html: str) -> dict:
    """Extract named SQL blocks from a <!--REPORT QUERIES ... --> comment in HTML."""
    m = re.search(r"<!--REPORT QUERIES\n(.*?)-->", html, re.DOTALL)
    if not m:
        return {}
    return parse_named_blocks(m.group(1))


# Static reports embedded by analysts are only ever allowed to run read-only
# SELECT / WITH (CTE) queries. Any other statement is rejected before execution.
_SELECT_ONLY_RE = re.compile(r"^\s*(?:--[^\n]*\n|\s)*(SELECT|WITH)\b", re.IGNORECASE)


def is_select_only(query: str) -> bool:
    return bool(_SELECT_ONLY_RE.match(query or ""))


def run_query_dict(slug: str, queries: dict) -> dict:
    """Run an arbitrary dict of {name: sql} using the OBO connection. Cached by slug.

    Each query is validated to be a read-only SELECT (or CTE) before execution.
    Any non-SELECT statement is logged and skipped — static analyst HTML must
    never be able to mutate Unity Catalog data.
    """
    cache_key = f"static_queries:{slug}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    results: dict = {}
    with user_conn() as conn:
        with conn.cursor() as cur:
            for name, query in queries.items():
                if not query:
                    continue
                if not is_select_only(query):
                    app.logger.warning(
                        "Rejected non-SELECT query in static report %s/%s", slug, name
                    )
                    results[name] = []
                    continue
                try:
                    cur.execute(query)
                    cols = [d[0] for d in cur.description]
                    results[name] = [dict(zip(cols, row)) for row in cur.fetchall()]
                except Exception as e:
                    app.logger.error("Static query %s/%s failed: %s", slug, name, e)
                    results[name] = []

    _cache.set(cache_key, results, _CACHE_TTL)
    return results


def run_named_queries(slug: str) -> dict:
    cache_key = f"queries:{slug}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

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

    _cache.set(cache_key, results, _CACHE_TTL)
    return results


def fetch_statuses(slugs: list[str]) -> dict:
    if not slugs:
        return {}

    cache_key = f"statuses:{ORG}:{','.join(sorted(slugs))}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

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
                result = {row[0]: dict(zip(cols, row)) for row in cur.fetchall()}
        _cache.set(cache_key, result, _CACHE_TTL)
        return result
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


def discover_static_reports() -> list[dict]:
    """Scan static_reports/ and return a report-card entry for each .html file.

    Extracts title, description, author, and updated_at from the HTML so cards
    on the home page show consistent metadata alongside manifest-based reports.
    """
    static_dir = APP_DIR / "static_reports"
    if not static_dir.exists():
        return []
    out = []
    for f in sorted(static_dir.glob("*.html")):
        slug = f.stem
        if not re.fullmatch(r"[a-z0-9_-]+", slug):
            continue
        html = f.read_text(errors="ignore")

        m_title = re.search(r"<title>(.*?)</title>", html, re.DOTALL | re.IGNORECASE)
        title = m_title.group(1).strip() if m_title else slug.replace("_", " ").title()

        m_desc = re.search(
            r'<meta\s[^>]*name=["\']description["\'][^>]*content=["\']([^"\']*)["\']',
            html, re.IGNORECASE
        ) or re.search(
            r'<meta\s[^>]*content=["\']([^"\']*)["\'][^>]*name=["\']description["\']',
            html, re.IGNORECASE
        )
        description = m_desc.group(1).strip() if m_desc else ""

        m_author = re.search(
            r'<meta\s[^>]*name=["\']author["\'][^>]*content=["\']([^"\']*)["\']',
            html, re.IGNORECASE
        ) or re.search(
            r'<meta\s[^>]*content=["\']([^"\']*)["\'][^>]*name=["\']author["\']',
            html, re.IGNORECASE
        )
        owner = m_author.group(1).strip() if m_author else ""

        m_tags = re.search(
            r'<meta\s[^>]*name=["\']tags["\'][^>]*content=["\']([^"\']*)["\']',
            html, re.IGNORECASE
        ) or re.search(
            r'<meta\s[^>]*content=["\']([^"\']*)["\'][^>]*name=["\']tags["\']',
            html, re.IGNORECASE
        )
        tags = [t.strip() for t in m_tags.group(1).split(",") if t.strip()] if m_tags else []

        import datetime
        updated_at = datetime.date.fromtimestamp(f.stat().st_mtime).isoformat()

        out.append({
            "slug": slug,
            "title": title,
            "description": description,
            "owner": owner,
            "updated_at": updated_at,
            "tags": tags,
            "source": "static",
        })
    return out


def all_reports() -> list[dict]:
    """Merge manifest reports + auto-discovered static reports. Manifest wins on collision."""
    manifest_reports = load_manifest().get("reports", [])
    manifest_slugs = {r["slug"] for r in manifest_reports}
    static = [r for r in discover_static_reports() if r["slug"] not in manifest_slugs]
    return manifest_reports + static


def _safe_slug(slug: str) -> str:
    if not re.fullmatch(r"[a-z0-9_-]+", slug):
        abort(400)
    return slug


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    reports = all_reports()
    # No SQL on the home page — status badges are loaded asynchronously by the
    # browser after the page renders, keeping the first load instant.
    return render_template("index.html", reports=reports, org=ORG)


@app.route("/api/statuses")
def api_statuses():
    """Return status rows for all reports in this org. Called async by the home page."""
    reports = all_reports()
    slugs = [r["slug"] for r in reports]
    return jsonify(fetch_statuses(slugs))


@app.route("/reports/<slug>")
def report(slug: str):
    slug = _safe_slug(slug)

    # Static HTML reports uploaded directly by analysts are wrapped in the full
    # app shell (_static_wrapper.html extends _base.html) so they get the topbar,
    # sidebar, and footer. Live data is passed via live_data (injected as
    # window.__REPORT_DATA__ inside the wrapper's {% block head %}).
    static_path = APP_DIR / "static_reports" / f"{slug}.html"
    if static_path.exists():
        html = static_path.read_text()

        # Extract title for the browser tab and topbar.
        m_title = re.search(r"<title>(.*?)</title>", html, re.DOTALL | re.IGNORECASE)
        title = m_title.group(1).strip() if m_title else slug.replace("_", " ").title()

        # Extract body content — drop the standalone <head>/<style> since _base.html
        # already provides the same CSS. Chart.js is loaded by _base.html too.
        m_body = re.search(r"<body[^>]*>(.*?)</body>", html, re.DOTALL | re.IGNORECASE)
        body_html = m_body.group(1) if m_body else html

        # Run embedded SQL with OBO only if there are named queries.
        queries = parse_report_queries(html)
        live_data = run_query_dict(slug, queries) if queries else {}

        m_tags = re.search(
            r'<meta\s[^>]*name=["\']tags["\'][^>]*content=["\']([^"\']*)["\']',
            html, re.IGNORECASE
        ) or re.search(
            r'<meta\s[^>]*content=["\']([^"\']*)["\'][^>]*name=["\']tags["\']',
            html, re.IGNORECASE
        )
        tags = [t.strip() for t in m_tags.group(1).split(",") if t.strip()] if m_tags else []

        statuses = fetch_statuses([slug])
        status = statuses.get(slug, {"status": "draft", "updated_at": "", "updated_by": ""})

        return render_template(
            "_static_wrapper.html",
            title=title,
            body_html=body_html,
            live_data=live_data,
            active_slug=slug,
            all_reports=all_reports(),
            tags=tags,
            status=status,
            org=ORG,
        )

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


@app.route("/api/cache/clear", methods=["POST"])
def clear_cache():
    count = _cache.clear()
    return jsonify({"cleared": count, "ok": True})


@app.route("/api/status/<slug>", methods=["POST"])
def set_status(slug: str):
    slug = _safe_slug(slug)
    known_slugs = {r["slug"] for r in all_reports()}
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

    # Invalidate all cached status entries for this org so the next
    # home page load and report load pick up the new value immediately.
    _cache.clear_prefix(f"statuses:{ORG}:")

    return jsonify({"slug": slug, "status": new_status, "ok": True})


def _decode_jwt_claims(token: str) -> dict:
    """Decode JWT claims (payload only, no verification) for diagnostics."""
    try:
        import base64
        parts = token.split(".")
        if len(parts) != 3:
            return {"error": "not a JWT"}
        padded = parts[1] + "=" * (4 - len(parts[1]) % 4)
        payload = base64.urlsafe_b64decode(padded)
        return json.loads(payload)
    except Exception as e:
        return {"error": str(e)}


@app.route("/debug/obo")
def debug_obo():
    token = user_token()
    claims = _decode_jwt_claims(token) if token else {}
    diag = {
        "host": cfg.host,
        "http_path": HTTP_PATH,
        "warehouse_id": WAREHOUSE_ID,
        "header_present": bool(token),
        "header_len": len(token),
        "user_api_scopes_env": os.environ.get("DATABRICKS_USER_API_SCOPES"),
        "token_scope": claims.get("scope"),
        "token_sub": claims.get("sub"),
        "token_client_id": claims.get("client_id"),
        "token_aud": claims.get("aud"),
        "cache": _cache.stats(),
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
