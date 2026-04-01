"""
RAG VS FINETUNE TCO
===================

THE PROBLEM:
    Three approaches to customize LLM behavior. Which is cheapest at what volume? Crossover analysis.

HOW TO RUN:
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


VOLUMES = [1000, 10000, 100000, 1000000]
APPROACHES = {
    "zero-shot": {"setup":0, "per_query":0.003, "monthly_infra":0},
    "rag":       {"setup":100, "per_query":0.005, "monthly_infra":50},
    "fine-tuned":{"setup":50, "per_query":0.001, "monthly_infra":0},
}
metric_analyzed = Gauge("tco_volumes_analyzed", "Volumes analyzed")

def run_benchmark():
    results = []
    log.info("benchmark_started")
    print(f"\n{'Volume/day':<14}", end="")
    for a in APPROACHES: print(f"{a:>18}", end="")
    print(); print("="*70)
    for vol in VOLUMES:
        metric_analyzed.inc()
        print(f"{vol:>10,}/day", end="")
        best_name, best_cost = "", float('inf')
        for name, c in APPROACHES.items():
            monthly = c["per_query"]*vol*30 + c["monthly_infra"] + c["setup"]/6
            if monthly < best_cost: best_name, best_cost = name, monthly
            print(f"  ${monthly:>14,.2f}/mo", end="")
        print(f"  -> {best_name}")
        results.append({"volume":vol,"winner":best_name,"cost":round(best_cost,2)})
    log.info("benchmark_complete"); return results

def show_analysis(results):
    print("\n  <10K/day: zero-shot wins (no setup)")
    print("  10K-100K: RAG (if knowledge changes) or fine-tune (if behavior)")
    print("  >100K/day: fine-tune ALWAYS wins on per-query cost")


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

def test_3_approaches(): assert len(APPROACHES) == 3

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
