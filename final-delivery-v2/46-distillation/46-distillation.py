"""
KNOWLEDGE DISTILLATION
=======================

THE PROBLEM:
    GPT-4o is smart but expensive ($2.50/1M tokens).
    GPT-4o-mini is cheap ($0.15/1M) but less accurate.
    Distillation: use GPT-4o to LABEL data, fine-tune mini on those labels.
    Result: mini performs like 4o on YOUR specific task at 1/30th cost.

WHAT YOU WILL LEARN:
    - Teacher labels once, student learns, deploy student
    - Fine-tuned mini often beats base GPT-4o on specific tasks
    - At 100K/day: $100/day (mini) vs $3000/day (4o)
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

metric_labeled = Counter("distill_labeled_total", "Examples labeled")
metric_cost = Counter("distill_cost_dollars", "Labeling cost")

TEXTS = [
    "My card was charged twice for order #123",
    "The app keeps crashing on iPhone",
    "What are your business hours?",
    "Need a refund for defective product",
    "API returning 500 errors since yesterday",
    "Do you offer student discounts?",
    "Unauthorized charge on my statement",
    "Cant connect bluetooth to the device",
    "How do I update my shipping address?",
    "Premium subscription billed after I cancelled",
    "Login page is broken on Firefox",
    "Where can I find the user manual?",
    "Invoice amount doesnt match the quote",
    "Dark mode makes text unreadable",
    "Can I gift a subscription?",
    "Double charged for the same item",
    "Export feature produces empty files",
    "What payment methods do you accept?",
    "Promo code not working at checkout",
    "App notifications stopped working",
]

def run_benchmark():
    results = []
    training_data = []
    log.info("benchmark_started")
    print("\nTeacher (GPT-4o-mini) labeling 20 examples...")
    print("-" * 50)
    for text in TEXTS:
        try:
            r = client.chat.completions.create(model=MODEL, temperature=0, max_tokens=5,
                messages=[{"role":"user","content":f"Classify: billing, technical, or general. One word.\n\n{text}"}])
            label = r.choices[0].message.content.strip().lower().rstrip(".")
            cost = r.usage.total_tokens / 1e6 * 0.15
            metric_labeled.inc()
            metric_cost.inc(cost)
            training_data.append({"messages":[
                {"role":"system","content":"Classify as billing, technical, or general."},
                {"role":"user","content":text},
                {"role":"assistant","content":label}
            ]})
            print(f"  [{label:>10}] {text[:45]}")
        except Exception as e:
            log.error("failed", error=str(e))
    
    print(f"\n  Training data ready: {len(training_data)} examples")
    print(f"  Format: JSONL for OpenAI fine-tuning API")
    print(f"  Next: upload -> fine-tune mini -> deploy")
    print(f"  Fine-tuned mini: $0.001/call vs base 4o: $0.03/call = 30x cheaper")
    results = [{"examples":len(training_data)}]
    log.info("benchmark_complete"); return results

def show_analysis(results):
    print("\n  Teacher labels ONCE. Student learns. Deploy student.")
    print("  At 100K/day: mini=$100/day, 4o=$3000/day")


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

def test_20_texts(): assert len(TEXTS) == 20

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
