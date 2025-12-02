#!/usr/bin/env python3
"""
sec.py - phishing redirect logger with multi-format outputs

Behavior:
- Redirects any incoming request to TARGET_URL (env var, default https://example.com)
- Logs each visit into:
  - SQLite DB (DB_FILE, default /data/logs.db)
  - CSV file (CSV_FILE, default /data/logs.csv)
  - TXT file (TXT_FILE, default /data/logs.txt)
  - SQL dump file (SQL_FILE, default /data/logs.sql) — regenerated after each insert via connection.iterdump()
- Healthcheck on /health
- Configurable via env vars: TARGET_URL, DB_FILE, CSV_FILE, TXT_FILE, SQL_FILE, LISTEN_HOST, LISTEN_PORT
- Designed to run locally or in Docker. Persist /data (or other path) as volume for logs persistence.
"""
from flask import Flask, request, redirect, abort, jsonify
import os
import sqlite3
from datetime import datetime
from urllib.parse import urljoin, urlparse, urlunparse
import csv
import threading

# Configuration (env override)
DB_FILE = os.environ.get("LOG_DB", "/data/logs.db")
CSV_FILE = os.environ.get("LOG_CSV", "/data/logs.csv")
TXT_FILE = os.environ.get("LOG_TXT", "/data/logs.txt")
SQL_FILE = os.environ.get("LOG_SQL", "/data/logs.sql")
TARGET_URL = os.environ.get("TARGET_URL", "https://example.com")
LISTEN_HOST = os.environ.get("LISTEN_HOST", "0.0.0.0")
LISTEN_PORT = int(os.environ.get("LISTEN_PORT", "8080"))

# Ensure directory exists for files
def ensure_parent_dirs(*paths):
    for p in paths:
        d = os.path.dirname(os.path.abspath(p))
        if d and not os.path.exists(d):
            os.makedirs(d, exist_ok=True)

ensure_parent_dirs(DB_FILE, CSV_FILE, TXT_FILE, SQL_FILE)

app = Flask(__name__)
_db_lock = threading.Lock()  # simple lock to reduce contention on sqlite + file writes

def init_db():
    """Initialize sqlite database and create visits table if needed."""
    with _db_lock:
        conn = sqlite3.connect(DB_FILE, timeout=10)
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS visits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    ip TEXT,
                    x_forwarded_for TEXT,
                    user_agent TEXT,
                    host TEXT,
                    path TEXT,
                    query_string TEXT,
                    target_url TEXT
                )
                """
            )
            conn.commit()
        finally:
            conn.close()


def get_client_ip():
    """Return (ip, xff) honoring X-Forwarded-For if present."""
    xff = request.headers.get("X-Forwarded-For", "")
    if xff:
        first = xff.split(",")[0].strip()
        return first, xff
    return request.remote_addr, xff


def safe_build_target(target_base, original_path, query_string):
    """Build target URL preserving path and query string."""
    parsed = urlparse(target_base)
    if not parsed.scheme:
        target_base = "https://" + target_base
        parsed = urlparse(target_base)

    combined = urljoin(target_base.rstrip("/) + /", original_path.lstrip("/"))
    if query_string:
        p = urlparse(combined)
        new = p._replace(query=query_string)
        combined = urlunparse(new)
    return combined


def append_txt(filepath, line):
    """Append a readable line to TXT log file."""
    try:
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        app.logger.exception("Failed to write TXT log")


def append_csv(filepath, fieldnames, row):
    """Append a row to CSV file, write header if file doesn't exist."""
    write_header = not os.path.exists(filepath)
    try:
        with open(filepath, "a", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if write_header:
                writer.writeheader()
            writer.writerow(row)
    except Exception:
        app.logger.exception("Failed to write CSV log")


def dump_sql(filepath):
    """Dump whole sqlite database to SQL file using iterdump()."""
    try:
        conn = sqlite3.connect(DB_FILE)
        with open(filepath, "w", encoding="utf-8") as f:
            for line in conn.iterdump():
                f.write("%s\n" % line)
    except Exception:
        app.logger.exception("Failed to write SQL dump")
    finally:
        try:
            conn.close()
        except Exception:
            pass


def log_visit(ip, xff, ua, host, path, qs, target):
    """Log visit into sqlite, txt, csv and generate sql dump."""
    timestamp = datetime.utcnow().isoformat() + "Z"
    # Insert into sqlite
    with _db_lock:
        try:
            conn = sqlite3.connect(DB_FILE, timeout=10)
            conn.execute(
                """
                INSERT INTO visits (timestamp, ip, x_forwarded_for, user_agent, host, path, query_string, target_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (timestamp, ip, xff, ua, host, path, qs, target),
            )
            conn.commit()
        except Exception:
            app.logger.exception("Failed to insert into sqlite")
        finally:
            try:
                conn.close()
            except Exception:
                pass

        # Prepare common row dict
        row = {
            "timestamp": timestamp,
            "ip": ip,
            "x_forwarded_for": xff,
            "user_agent": ua,
            "host": host,
            "path": path,
            "query_string": qs,
            "target_url": target,
        }

        # TXT: human readable
        txt_line = "{} | ip={} xff={} host={} path={} qs={} ua={} target={}".format(
            timestamp, ip, xff or "-", host, path, qs or "-", ua or "-", target
        )
        append_txt(TXT_FILE, txt_line)

        # CSV
        fieldnames = ["timestamp", "ip", "x_forwarded_for", "user_agent", "host", "path", "query_string", "target_url"]
        append_csv(CSV_FILE, fieldnames, row)

        # SQL dump (regenerate)
        dump_sql(SQL_FILE)


@app.route("/health", methods=["GET"])

def health():
    return jsonify({"status": "ok"}), 200


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def catch_all(path):
    if not TARGET_URL:
        abort(500, "TARGET_URL not configured")

    query_string = request.query_string.decode("utf-8") if request.query_string else ""
    target = safe_build_target(TARGET_URL, path, query_string)
    ip, xff = get_client_ip()
    ua = request.headers.get("User-Agent", "")
    host = request.host

    try:
        log_visit(ip, xff, ua, host, "/" + path, query_string, target)
    except Exception:
        app.logger.exception("Logging failed")

    return redirect(target, code=302)


if __name__ == "__main__":
    init_db()
    # Run dev server; in Docker we recommend gunicorn (see Dockerfile)
    app.run(host=LISTEN_HOST, port=LISTEN_PORT)