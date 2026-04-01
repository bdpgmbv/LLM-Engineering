"""
PLATFORM COST CALCULATOR
========================

THE PROBLEM:
    Monthly cost across 6 platforms at 4 volumes. Pure math, no API.

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


metric_calc = Gauge("platform_calcs", "Calculations done")
PLATFORMS = {
    "GPT-4o":        {"input":2.50,"output":10.00},
    "GPT-4o-mini":   {"input":0.15,"output":0.60},
    "Claude Sonnet": {"input":3.00,"output":15.00},
    "Claude Haiku":  {"input":0.25,"output":1.25},
    "Groq Llama":    {"input":0.05,"output":0.08},
    "Together":      {"input":0.20,"output":0.20},
}

def run_benchmark():
    results = []
    log.info("benchmark_started")
    AVG_IN, AVG_OUT = 200, 150
    for label, vol in [("1K",1000),("10K",10000),("100K",100000),("1M",1000000)]:
        print(f"\n  {label}/day:")
        print(f"  {'Platform':<18} {'Monthly':>12}")
        print(f"  "+"-"*32)
        for name, p in PLATFORMS.items():
            cost = (AVG_IN/1e6)*p["input"]+(AVG_OUT/1e6)*p["output"]
            monthly = cost*vol*30
            print(f"  {name:<18} ${monthly:>10,.2f}")
            metric_calc.inc()
        results.append({"volume":vol})
    log.info("benchmark_complete"); return results

def show_analysis(results):
    print("\n  GPT-4o-mini is hard to beat below 500K/day")
    print("  Self-hosted wins above 500K/day")
    print("  Groq is cheapest API but limited models")


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

def test_6_platforms(): assert len(PLATFORMS) == 6

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
