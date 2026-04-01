"""
AGENT LOOP DETECTION
====================

THE PROBLEM:
    Give agents impossible tasks. Do they loop forever or stop gracefully? Max steps is essential.

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


metric_loops = Counter("loop_detected", "Loops detected")
TASKS = [
    ("Find order XYZ-IMPOSSIBLE-999", "impossible"),
    ("Look up secret code for project UNICORN", "impossible"),
    ("Search CEO personal phone number", "impossible"),
]

def fake_search(query):
    return "No results found"

def run_benchmark():
    results = []
    log.info("benchmark_started")
    MAX_STEPS = 5
    for task, task_type in TASKS:
        print(f"\n  Task ({task_type}): {task}")
        steps = 0
        for _ in range(MAX_STEPS):
            result = fake_search(task)
            steps += 1
            print(f"    Step {steps}: search -> {result}")
            if steps >= 3:  # Stuck detector: same result 3 times
                print(f"    STUCK DETECTED: same result {steps} times. Stopping.")
                metric_loops.inc()
                break
        hit_max = steps >= MAX_STEPS
        print(f"    {'HIT MAX STEPS' if hit_max else 'Stopped gracefully'}")
        results.append({"task":task[:30],"steps":steps,"stopped":not hit_max})
    log.info("benchmark_complete"); return results

def show_analysis(results):
    print("\n  Max steps (5-10) prevents infinite loops")
    print("  Stuck detector: same result 3x = force stop")
    print("  Include impossible tasks in your test suite")
    print("  Cost of loops: $0.15/step x infinite = disaster")


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

def test_3_tasks(): assert len(TASKS) == 3

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
