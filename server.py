#!/usr/bin/env python3
"""
Render Web Service Entry Point
- Serves index.html via Flask
- Runs scraper.py on startup
- Refreshes news every 1 hour via APScheduler
"""

import os
import subprocess
import sys
import threading
from flask import Flask, send_file, abort
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INDEX_HTML = os.path.join(BASE_DIR, "index.html")


# ─── Scraper Runner ───────────────────────────────────────────────────────────

def run_scraper():
    """Execute scraper.py to regenerate index.html"""
    print("[scheduler] Running scraper...", flush=True)
    result = subprocess.run(
        [sys.executable, os.path.join(BASE_DIR, "scraper.py")],
        capture_output=True,
        text=True,
        cwd=BASE_DIR,
    )
    if result.returncode == 0:
        print("[scheduler] Scraper done ✅", flush=True)
    else:
        print(f"[scheduler] Scraper error ❌\n{result.stderr}", flush=True)


# ─── Routes ──────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    if not os.path.exists(INDEX_HTML):
        abort(503, description="index.html not yet generated — please wait a moment and refresh.")
    return send_file(INDEX_HTML)


@app.route("/refresh")
def refresh():
    """Manual trigger endpoint — call /refresh to force scraper run"""
    thread = threading.Thread(target=run_scraper, daemon=True)
    thread.start()
    return {"status": "scraper started"}, 202


@app.route("/healthz")
def health():
    """Health check for Render"""
    return {"status": "ok"}, 200


# ─── Startup ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # 1) Run scraper immediately on cold start
    print("[startup] Running initial scraper...", flush=True)
    run_scraper()

    # 2) Schedule scraper every 60 minutes
    scheduler = BackgroundScheduler()
    scheduler.add_job(run_scraper, "interval", minutes=60, id="scraper")
    scheduler.start()
    print("[startup] Scheduler started — refresh every 60 min", flush=True)

    # 3) Start Flask server on PORT (Render injects $PORT)
    port = int(os.environ.get("PORT", 8000))
    print(f"[startup] Server listening on 0.0.0.0:{port}", flush=True)
    app.run(host="0.0.0.0", port=port)
