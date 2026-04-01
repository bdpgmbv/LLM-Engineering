"""
STALE DATA DETECTOR
===================

THE PROBLEM:
    RAG returns outdated info if old documents are still in your index. Fix with freshness metadata filtering.

HOW TO RUN:
    export OPENAI_API_KEY=sk-your-key
    pip install -r requirements.txt
    python main.py
"""

import time, csv, os, json
from datetime import datetime
from collections import defaultdict
import structlog
from prometheus_client import Counter, Histogram, Gauge, start_http_server

structlog.configure(
    processors=[structlog.processors.TimeStamper(fmt="iso"), structlog.dev.ConsoleRenderer()],
    wrapper_class=structlog.BoundLogger, context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)
log = structlog.get_logger()
METRICS_PORT = 8000
RESULTS_DIR = "./results"
from openai import OpenAI
client = OpenAI()
MODEL = "gpt-4o-mini"


metric_stale = Counter("stale_found", "Stale docs served")
DOCS = [
    {"text":"Pro plan costs $29/month.","date":"2023-01","current":False},
    {"text":"Pro plan costs $49/month.","date":"2024-06","current":True},
    {"text":"Free trial is 7 days.","date":"2023-03","current":False},
    {"text":"Free trial is 14 days. No credit card.","date":"2024-06","current":True},
]

def run_benchmark():
    results = []
    log.info("benchmark_started")
    query = "How much does Pro plan cost?"
    print(f"\n  Query: {query}")
    # Without filter (returns closest match which may be stale)
    for doc in DOCS:
        if "pro" in doc["text"].lower() and "cost" in doc["text"].lower():
            print(f"\n  WITHOUT freshness filter:")
            print(f"    Retrieved: {doc['text']} (from {doc['date']})")
            print(f"    Current? {'YES' if doc['current'] else 'NO - STALE!'}")
            if not doc["current"]: metric_stale.inc()
            break
    # With filter
    current_docs = [d for d in DOCS if d["current"]]
    for doc in current_docs:
        if "pro" in doc["text"].lower():
            print(f"\n  WITH freshness filter:")
            print(f"    Retrieved: {doc['text']} (from {doc['date']})")
            print(f"    Current? YES")
            break
    results = [{"issue":"stale_data","fix":"freshness_metadata"}]
    log.info("benchmark_complete"); return results

def show_analysis(results):
    print("\n  FIX: filter by date/version BEFORE vector search")
    print("  Monitor stale document count as health metric")


def save_results(results):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{RESULTS_DIR}/results_{ts}.csv"
    if results:
        keys = set()
        for r in results: keys.update(r.keys())
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=sorted(keys))
            w.writeheader(); w.writerows(results)
    log.info("saved", path=path); return path

def test_has_stale(): assert any(not d["current"] for d in DOCS)

if __name__ == "__main__":
    try:
        start_http_server(METRICS_PORT)
        log.info("metrics_started", url=f"http://localhost:{METRICS_PORT}/metrics")
    except OSError:
        log.warning("port_in_use")
    results = run_benchmark()
    show_analysis(results)
    csv_path = save_results(results)
    print(f"\nDONE! CSV: {csv_path} | Metrics: http://localhost:{METRICS_PORT}/metrics")
    print("Ctrl+C to stop.")
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt: log.info("shutdown")
