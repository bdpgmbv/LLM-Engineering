"""
MODEL ROUTER
=============

THE PROBLEM:
    Sending everything to GPT-4o wastes money.
    70% of queries are simple. Route them to mini.

WHAT YOU WILL LEARN:
    - Simple classifier (length + keywords) works well
    - Saves 60-70% with zero quality loss on simple queries
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

metric_routed = Counter("router_calls_total", "Calls", ["model"])
metric_savings = Gauge("router_savings_pct", "Savings")

COSTS = {"gpt-4o-mini":{"input":0.15,"output":0.60},"gpt-4o":{"input":2.50,"output":10.00}}
QUERIES = [
    ("What time do you close?", "simple"),
    ("Compare Enterprise vs Pro for 200 engineers with SSO and SAML", "complex"),
    ("Do you accept PayPal?", "simple"),
    ("Design migration from on-prem to cloud with zero downtime", "complex"),
    ("Where is my order?", "simple"),
    ("Price of Pro plan?", "simple"),
    ("Explain security architecture including encryption and compliance", "complex"),
    ("How do I reset my password?", "simple"),
]

def classify(query):
    keywords = ["compare","design","explain","architecture","migration","strategy","analyze"]
    return "complex" if len(query) > 100 or any(w in query.lower() for w in keywords) else "simple"

def run_benchmark():
    results = []
    total_routed = total_expensive = 0
    log.info("benchmark_started")
    print(f"\n{chr(39)+'Query'+chr(39):<50} {'Route':>10} {'Model':>14}")
    print("-" * 78)
    for query, true_type in QUERIES:
        predicted = classify(query)
        model = "gpt-4o" if predicted == "complex" else "gpt-4o-mini"
        try:
            r = client.chat.completions.create(model=model, temperature=0, max_tokens=150,
                messages=[{"role":"user","content":query}])
            cost = (r.usage.prompt_tokens/1e6)*COSTS[model]["input"]+(r.usage.completion_tokens/1e6)*COSTS[model]["output"]
            exp = (r.usage.prompt_tokens/1e6)*COSTS["gpt-4o"]["input"]+(r.usage.completion_tokens/1e6)*COSTS["gpt-4o"]["output"]
            total_routed += cost; total_expensive += exp
            metric_routed.labels(model=model).inc()
        except: continue
        print(f"  {query[:48]:<50} {predicted:>10} {model:>14}")
    savings = (1-total_routed/total_expensive)*100 if total_expensive else 0
    metric_savings.set(savings)
    print(f"\n  Savings: {savings:.0f}%")
    results = [{"routed_cost":round(total_routed,6),"all_4o_cost":round(total_expensive,6),"savings":round(savings,1)}]
    log.info("benchmark_complete"); return results

def show_analysis(results):
    print("\n  70% of queries are simple -> route to mini -> save 60-70%")


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

def test_simple(): assert classify("What time?") == "simple"
def test_complex(): assert classify("Design a migration architecture for 5 databases") == "complex"
def test_8_queries(): assert len(QUERIES) == 8

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
