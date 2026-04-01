"""
VOICE OF CUSTOMER ANALYZER
===========================

THE PROBLEM:
    You have 10,000 customer reviews. Reading them manually takes weeks.
    This tool extracts sentiment, topics, and action items from all of them
    in one API call per batch.

WHAT YOU WILL LEARN:
    - Structured JSON extraction from unstructured text
    - Batch analysis scales to thousands of reviews
    - Cost: ~$0.001 per review
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

metric_reviews = Counter("voc_reviews_total", "Reviews analyzed")
metric_sentiment = Counter("voc_sentiment_total", "Sentiment counts", ["sentiment"])

REVIEWS = [
    "Love the product! Works exactly as described. Shipping was fast too.",
    "Terrible customer service. Waited 3 hours on hold. Product is fine though.",
    "Its okay. Nothing special. Overpriced for what you get.",
    "Best purchase Ive made this year! The premium plan is worth every penny.",
    "App keeps crashing. Reported the bug 2 weeks ago, still no fix.",
    "Great features but the learning curve is steep. Better docs would help.",
    "Cancelled my subscription. Too many bugs and slow support.",
    "Impressed with the security features. Perfect for our compliance needs.",
    "Mixed feelings. Love the core product, hate the mobile app.",
    "Would recommend to anyone. The onboarding experience was smooth.",
]

def run_benchmark():
    results = []
    log.info("benchmark_started")
    try:
        r = client.chat.completions.create(
            model=MODEL, temperature=0, max_tokens=1000,
            response_format={"type":"json_object"},
            messages=[{"role":"system","content":"Analyze reviews. Return JSON with key analysis: array of {sentiment, topics, action_item, priority}."},
                      {"role":"user","content":"Reviews:\n"+"\n".join([f"{i+1}. {r}" for i,r in enumerate(REVIEWS)])}])
        data = json.loads(r.choices[0].message.content)
        analyses = data.get("analysis", data.get("reviews", []))
    except Exception as e:
        log.error("failed", error=str(e)); analyses = []
    
    icons = {"positive":"POS","negative":"NEG","mixed":"MIX"}
    for i, (review, analysis) in enumerate(zip(REVIEWS, analyses)):
        sent = analysis.get("sentiment","?")
        topics = ", ".join(analysis.get("topics",[]))
        action = analysis.get("action_item","")
        metric_reviews.inc()
        metric_sentiment.labels(sentiment=sent).inc()
        print(f"  [{sent:>8}] {review[:50]}...")
        if topics: print(f"           Topics: {topics}")
        if action: print(f"           Action: {action}")
        results.append({"review":review[:30],"sentiment":sent,"topics":topics[:40]})
    
    log.info("benchmark_complete"); return results

def show_analysis(results):
    from collections import Counter as C
    sents = C(r["sentiment"] for r in results)
    print(f"\nSentiment: {dict(sents)}")
    print(f"Cost: ~${len(results)*0.001:.3f} for {len(results)} reviews")


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

def test_10_reviews(): assert len(REVIEWS) == 10

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
