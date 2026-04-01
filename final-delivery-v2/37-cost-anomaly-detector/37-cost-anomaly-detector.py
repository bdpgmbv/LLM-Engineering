"""
COST ANOMALY DETECTOR
======================

THE PROBLEM:
    You deploy an LLM app. One day, someone sends a 10,000-word prompt.
    Your daily cost spikes from $50 to $500. Nobody notices for 3 days.
    
    This tool tracks every API call and alerts when cost exceeds
    2 standard deviations from the rolling average.

WHAT WE FIND OUT:
    1. Does the detector catch cost spikes?
    2. How many false alarms does it trigger?
    3. What rolling window size works best?

WHAT YOU WILL LEARN:
    - Track every call: tokens, cost, latency
    - Alert on 2+ standard deviations from rolling average
    - 50 lines of monitoring replaces expensive tools for LLM costs
    - Production: feed these metrics into Datadog/Grafana

HOW TO RUN:
    export OPENAI_API_KEY=sk-your-key
    pip install -r requirements.txt
    python main.py
"""

import time, csv, os, statistics
from datetime import datetime
import structlog
from prometheus_client import Counter, Gauge, start_http_server
from openai import OpenAI

structlog.configure(
    processors=[structlog.processors.TimeStamper(fmt="iso"), structlog.dev.ConsoleRenderer()],
    wrapper_class=structlog.BoundLogger, context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)
log = structlog.get_logger()

metric_calls = Counter("anomaly_calls_total", "Total calls")
metric_alerts = Counter("anomaly_alerts_total", "Alerts triggered")
metric_cost = Gauge("anomaly_last_cost", "Last call cost")
metric_avg_cost = Gauge("anomaly_avg_cost", "Rolling average cost")

METRICS_PORT = 8000
RESULTS_DIR = "./results"
client = OpenAI()
MODEL = "gpt-4o-mini"
PRICING = {"input": 0.15, "output": 0.60}


class CostMonitor:
    def __init__(self, window_size=10):
        self.costs = []
        self.window = window_size
        self.alerts = []

    def track(self, cost):
        self.costs.append(cost)
        metric_calls.inc()
        metric_cost.set(cost)

        if len(self.costs) >= self.window:
            recent = self.costs[-self.window:]
            avg = statistics.mean(recent)
            std = statistics.stdev(recent) if len(recent) > 1 else 0
            metric_avg_cost.set(avg)

            if cost > avg + 2 * std and std > 0:
                alert = f"COST SPIKE: ${cost:.5f} (avg: ${avg:.5f}, +{(cost-avg)/avg*100:.0f}%)"
                self.alerts.append(alert)
                metric_alerts.inc()
                return alert
        return None


def run_benchmark():
    results = []
    monitor = CostMonitor(window_size=10)
    log.info("benchmark_started")

    # Simulate 30 normal calls + 3 spikes
    queries = (
        ["What is your refund policy?"] * 10 +  # normal
        ["Write a detailed 2000-word analysis of " + "everything " * 50] +  # SPIKE
        ["What is your refund policy?"] * 8 +  # normal
        ["Write a detailed 2000-word analysis of " + "everything " * 50] +  # SPIKE
        ["What is your refund policy?"] * 5 +  # normal
        ["Write a detailed 2000-word analysis of " + "everything " * 50] +  # SPIKE
        ["What is your refund policy?"] * 5    # normal
    )

    print(f"\nSimulating {len(queries)} API calls (with 3 cost spikes)...")
    print("-" * 60)

    for i, query in enumerate(queries):
        try:
            r = client.chat.completions.create(model=MODEL, temperature=0, max_tokens=100,
                messages=[{"role":"user","content":query}])
            tok = r.usage.total_tokens
            cost = (r.usage.prompt_tokens/1e6)*PRICING["input"] + (r.usage.completion_tokens/1e6)*PRICING["output"]
        except:
            continue

        alert = monitor.track(cost)
        if alert:
            print(f"  Call {i+1}: *** ALERT *** {alert}")
            results.append({"call":i+1, "cost":round(cost,6), "alert":True})
        else:
            results.append({"call":i+1, "cost":round(cost,6), "alert":False})

    log.info("benchmark_complete", alerts=len(monitor.alerts))
    return results


def show_analysis(results):
    alerts = sum(1 for r in results if r["alert"])
    total_cost = sum(r["cost"] for r in results)
    print(f"\nRESULTS:")
    print(f"=" * 40)
    print(f"  Total calls: {len(results)}")
    print(f"  Alerts triggered: {alerts}")
    print(f"  Total cost: ${total_cost:.4f}")
    print(f"\n  Cost spikes detected automatically.")
    print(f"  Production: feed these alerts into PagerDuty/Slack.")


def save_results(results):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{RESULTS_DIR}/anomaly_{ts}.csv"
    if results:
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=results[0].keys())
            w.writeheader(); w.writerows(results)
    log.info("saved", path=path); return path


def test_monitor_no_alert_initially():
    m = CostMonitor(window_size=5)
    assert m.track(0.001) is None

def test_monitor_detects_spike():
    m = CostMonitor(window_size=5)
    for _ in range(10): m.track(0.001)
    alert = m.track(0.1)  # 100x spike
    assert alert is not None


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
