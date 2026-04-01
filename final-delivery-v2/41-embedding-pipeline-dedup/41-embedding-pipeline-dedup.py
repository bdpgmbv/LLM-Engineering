"""
EMBEDDING PIPELINE WITH DEDUP
===============================

THE PROBLEM:
    Your document store has duplicates. Same paragraph appears in
    3 different documents. Without dedup, you embed it 3 times
    and store 3 identical vectors. Waste of money and storage.

WHAT WE FIND OUT:
    1. How many duplicates exist in a typical doc set?
    2. How much does dedup save on embedding costs?
    3. Does metadata enable useful filtering?

WHAT YOU WILL LEARN:
    - Dedup via content hashing saves 10-30%
    - Always attach metadata (source, date, type)
    - Idempotent pipeline: run twice = same result
    - Monitor: docs processed, errors, storage growth

HOW TO RUN:
    export OPENAI_API_KEY=sk-your-key
    pip install -r requirements.txt
    python main.py
"""

import time, csv, os, hashlib
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

metric_docs = Counter("embed_docs_total", "Docs processed")
metric_dupes = Counter("embed_dupes_total", "Duplicates found")
metric_embedded = Counter("embed_embedded_total", "Docs embedded")

METRICS_PORT = 8000
RESULTS_DIR = "./results"
client = OpenAI()

DOCUMENTS = [
    {"id":"doc1","text":"TechCorp refund policy allows 30-day returns for hardware.","source":"faq","date":"2024-01"},
    {"id":"doc2","text":"Digital products can be refunded within 14 days.","source":"faq","date":"2024-01"},
    {"id":"doc3","text":"API rate limits: Free 100/min, Pro 1000/min.","source":"api-docs","date":"2024-02"},
    {"id":"doc4","text":"TechCorp refund policy allows 30-day returns for hardware.","source":"faq","date":"2024-01"},  # DUPLICATE
    {"id":"doc5","text":"Enterprise plans include custom SLAs.","source":"pricing","date":"2024-03"},
    {"id":"doc6","text":"Data encrypted AES-256 at rest, TLS 1.3 in transit.","source":"security","date":"2024-02"},
    {"id":"doc7","text":"API rate limits: Free 100/min, Pro 1000/min.","source":"api-docs","date":"2024-02"},  # DUPLICATE
    {"id":"doc8","text":"Two-factor auth available for all accounts.","source":"security","date":"2024-02"},
    {"id":"doc9","text":"Mobile app requires iOS 15+ or Android 12+.","source":"compat","date":"2024-03"},
    {"id":"doc10","text":"TechCorp refund policy allows 30-day returns for hardware.","source":"faq","date":"2024-01"},  # DUPLICATE
]


def run_benchmark():
    results = []
    log.info("benchmark_started", docs=len(DOCUMENTS))

    # Step 1: Dedup
    print("\nStep 1: Dedup via content hashing")
    print("-" * 40)
    seen = {}
    unique = []
    dupes = 0

    for doc in DOCUMENTS:
        metric_docs.inc()
        h = hashlib.md5(doc["text"].encode()).hexdigest()
        if h not in seen:
            seen[h] = doc["id"]
            unique.append(doc)
        else:
            dupes += 1
            metric_dupes.inc()
            print(f"  DEDUP: {doc['id']} is duplicate of {seen[h]}")

    savings_pct = dupes / len(DOCUMENTS) * 100
    print(f"  Removed {dupes} duplicates ({savings_pct:.0f}% savings)")
    print(f"  {len(unique)} unique documents remain")

    # Step 2: Embed with metadata
    print(f"\nStep 2: Embedding {len(unique)} unique docs...")
    embedded = []
    for doc in unique:
        try:
            r = client.embeddings.create(model="text-embedding-3-small", input=doc["text"])
            metric_embedded.inc()
            embedded.append({
                "id": doc["id"], "text": doc["text"][:40],
                "dims": len(r.data[0].embedding),
                "metadata": {"source": doc["source"], "date": doc["date"]},
            })
        except Exception as e:
            log.error("embed_failed", doc=doc["id"], error=str(e))

    print(f"  Embedded: {len(embedded)} docs")
    if embedded:
        print(f"  Dimensions: {embedded[0]['dims']}")

    results = [{"total_docs":len(DOCUMENTS),"unique":len(unique),"dupes":dupes,
               "savings_pct":round(savings_pct,1),"embedded":len(embedded)}]

    log.info("benchmark_complete")
    return results


def show_analysis(results):
    if results:
        r = results[0]
        print(f"\nRESULTS:")
        print(f"=" * 40)
        print(f"  Input: {r['total_docs']} docs")
        print(f"  Duplicates removed: {r['dupes']} ({r['savings_pct']}%)")
        print(f"  Embedded: {r['embedded']} unique docs")
        print(f"\n  Dedup saved {r['savings_pct']:.0f}% on embedding costs")
        print(f"  Metadata enables filtered search (by source, date)")


def save_results(results):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{RESULTS_DIR}/embed_pipeline_{ts}.csv"
    if results:
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=results[0].keys())
            w.writeheader(); w.writerows(results)
    log.info("saved", path=path); return path


def test_10_docs():
    assert len(DOCUMENTS) == 10

def test_has_duplicates():
    texts = [d["text"] for d in DOCUMENTS]
    assert len(texts) > len(set(texts))


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
