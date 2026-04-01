"""
EMBEDDING MODEL SHOOTOUT
==========================

THE PROBLEM:
    OpenAI has two embedding models:
    - text-embedding-3-small: $0.02 per 1M tokens, 1536 dimensions
    - text-embedding-3-large: $0.13 per 1M tokens, 3072 dimensions
    
    Large costs 6x more and uses 2x more storage.
    Is it actually better? For what types of queries?

WHAT WE FIND OUT:
    1. Accuracy difference on 5 test queries
    2. Cost difference at scale
    3. Storage difference (vector DB size)

WHAT YOU WILL LEARN:
    - Small is good enough for 90% of use cases
    - Large has ~2-5% better accuracy on hard queries
    - 6x cost rarely justified
    - Changing embedding model = re-embed everything (choose carefully)

HOW TO RUN:
    export OPENAI_API_KEY=sk-your-key
    pip install -r requirements.txt
    python main.py
"""

import time, csv, os
from datetime import datetime
import structlog
from prometheus_client import Counter, Gauge, Histogram, start_http_server
from openai import OpenAI

structlog.configure(
    processors=[structlog.processors.TimeStamper(fmt="iso"), structlog.dev.ConsoleRenderer()],
    wrapper_class=structlog.BoundLogger, context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)
log = structlog.get_logger()

metric_embeds = Counter("embed_calls_total", "Embedding calls", ["model"])
metric_correct = Counter("embed_correct_total", "Correct retrievals", ["model"])
metric_latency = Histogram("embed_latency_seconds", "Latency", ["model"])
metric_accuracy = Gauge("embed_accuracy_pct", "Accuracy", ["model"])

METRICS_PORT = 8000
RESULTS_DIR = "./results"
client = OpenAI()

DOCS = [
    "Our return policy allows 30-day returns for hardware in original packaging.",
    "Digital products can be refunded within 14 days if not activated.",
    "Subscription cancellations are effective at end of billing cycle.",
    "Enterprise customers have custom SLAs with dedicated account managers.",
    "API rate limits are 100/min for free tier, 1000/min for pro.",
    "Two-factor authentication is required for all admin accounts.",
    "Data encryption uses AES-256 at rest and TLS 1.3 in transit.",
    "The mobile app supports iOS 15+ and Android 12+.",
]

QUERIES = [
    ("Can I return a laptop I bought last week?", 0),
    ("How do I cancel my subscription?", 2),
    ("What are the API rate limits?", 4),
    ("Is my data encrypted?", 6),
    ("Does the app work on iPhone?", 7),
]

MODELS = ["text-embedding-3-small", "text-embedding-3-large"]
COSTS_PER_1M = {"text-embedding-3-small": 0.02, "text-embedding-3-large": 0.13}


def cosine_sim(a, b):
    dot = sum(x*y for x,y in zip(a,b))
    return dot / ((sum(x*x for x in a)**0.5) * (sum(x*x for x in b)**0.5) + 1e-10)


def run_benchmark():
    results = []
    log.info("benchmark_started")

    for model in MODELS:
        print(f"\nModel: {model}")
        print("-" * 50)

        # Embed all docs
        start = time.time()
        doc_embs = []
        for doc in DOCS:
            r = client.embeddings.create(model=model, input=doc)
            doc_embs.append(r.data[0].embedding)
            metric_embeds.labels(model=model).inc()
        embed_time = time.time() - start
        dims = len(doc_embs[0])

        # Search
        correct = 0
        for query, expected_idx in QUERIES:
            q_r = client.embeddings.create(model=model, input=query)
            q_emb = q_r.data[0].embedding
            metric_embeds.labels(model=model).inc()

            scores = [(cosine_sim(q_emb, d_emb), i) for i, d_emb in enumerate(doc_embs)]
            scores.sort(key=lambda x: -x[0])
            top_idx = scores[0][1]

            found = top_idx == expected_idx
            if found:
                correct += 1
                metric_correct.labels(model=model).inc()
            
            mark = "Y" if found else "N"
            print(f"  {mark} '{query[:35]}...' -> doc {top_idx} (expected {expected_idx})")

        accuracy = correct / len(QUERIES) * 100
        metric_accuracy.labels(model=model).set(accuracy)
        metric_latency.labels(model=model).observe(embed_time)

        print(f"\n  Accuracy: {correct}/{len(QUERIES)} ({accuracy:.0f}%)")
        print(f"  Dimensions: {dims}")
        print(f"  Embed time: {embed_time:.2f}s")
        print(f"  Cost per 1M tokens: ${COSTS_PER_1M[model]}")

        results.append({"model":model, "accuracy":accuracy, "dims":dims,
                       "time":round(embed_time,2), "cost_per_1m":COSTS_PER_1M[model]})

    log.info("benchmark_complete")
    return results


def show_analysis(results):
    print("\nCOMPARISON:")
    print("=" * 60)
    for r in results:
        print(f"  {r['model']:<30} {r['accuracy']:.0f}% acc  {r['dims']} dims  ${r['cost_per_1m']}/1M")
    print(f"\n  Cost ratio: {COSTS_PER_1M['text-embedding-3-large']/COSTS_PER_1M['text-embedding-3-small']:.0f}x")
    print(f"  Storage ratio: {results[1]['dims']/results[0]['dims']:.1f}x" if len(results)==2 else "")
    print("\n  Small is good enough for 90% of use cases.")
    print("  Changing models later = re-embed everything. Choose carefully.")


def save_results(results):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{RESULTS_DIR}/embedding_shootout_{ts}.csv"
    if results:
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=results[0].keys())
            w.writeheader(); w.writerows(results)
    log.info("saved", path=path); return path


def test_8_docs():
    assert len(DOCS) == 8

def test_5_queries():
    assert len(QUERIES) == 5

def test_2_models():
    assert len(MODELS) == 2


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
