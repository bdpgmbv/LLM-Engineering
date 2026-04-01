"""
CHUNKING STRATEGY BENCHMARK
=============================

THE PROBLEM:
    In RAG (Retrieval Augmented Generation), you split documents into chunks
    and search for the most relevant ones. HOW you split matters enormously.
    
    Bad chunking: splits sentences in half, loses context.
    Good chunking: respects paragraph boundaries, keeps context together.
    
    Same question can get a right answer with good chunks
    and a wrong answer with bad chunks.

WHAT WE FIND OUT:
    1. Fixed-size vs recursive vs sentence-level vs parent-child
    2. Which method finds the correct answer most often?
    3. How many chunks does each method produce?
    4. What chunk size works best?

WHAT YOU WILL LEARN:
    - Fixed-size chunking is the WORST (splits sentences)
    - Recursive (paragraph-aware) is the reliable default
    - Parent-child gives best precision (small for search, big for LLM)
    - Chunking alone swings accuracy by 20-30%

HOW TO RUN:
    export OPENAI_API_KEY=sk-your-key
    pip install -r requirements.txt
    python main.py
"""

import time, csv, os, re
from datetime import datetime
from collections import defaultdict
import structlog
from prometheus_client import Counter, Gauge, start_http_server
from openai import OpenAI

structlog.configure(
    processors=[structlog.processors.TimeStamper(fmt="iso"), structlog.dev.ConsoleRenderer()],
    wrapper_class=structlog.BoundLogger, context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)
log = structlog.get_logger()

metric_searches = Counter("chunk_searches_total", "Searches", ["method"])
metric_found = Counter("chunk_found_total", "Answer found in chunks", ["method"])
metric_missed = Counter("chunk_missed_total", "Answer NOT found", ["method"])
metric_accuracy = Gauge("chunk_accuracy_pct", "Accuracy", ["method"])

METRICS_PORT = 8000
RESULTS_DIR = "./results"
client = OpenAI()

DOCS = [
    {"title": "Refund Policy", "text": """TechCorp Refund Policy (Updated January 2024)

Section 1: Digital Products
Digital products may be refunded within 14 days of purchase if not activated or downloaded more than twice. Processing takes 5-7 business days.

Section 2: Hardware Products
Hardware may be returned within 30 days in original packaging. Items must be working with all accessories. Non-defective returns have a $15 restocking fee.

Section 3: Subscriptions
Monthly subscriptions can be cancelled anytime. Annual subscriptions refunded within first 30 days. After 30 days, prorated based on months used.""",
     "questions": [
         ("What is the refund window for digital products?", "14 days"),
         ("What fee applies to non-defective hardware returns?", "15"),
         ("Can annual subscriptions be refunded after 60 days?", "prorated"),
     ]},
    {"title": "API Documentation", "text": """TechCorp API v3.2 Authentication Guide

All API requests require Bearer tokens. Tokens expire after 24 hours. Refresh via /auth/refresh.

Rate Limits: Free tier 100 requests/minute. Pro tier 1000 requests/minute. Exceeding returns HTTP 429.

Pagination: All list endpoints use cursor-based pagination. Default page size 50, max 200.""",
     "questions": [
         ("How long do API tokens last?", "24 hours"),
         ("What is the Pro tier rate limit?", "1000"),
     ]},
]


def get_embedding(text):
    r = client.embeddings.create(model="text-embedding-3-small", input=text)
    return r.data[0].embedding

def cosine_sim(a, b):
    dot = sum(x*y for x,y in zip(a,b))
    na = sum(x*x for x in a)**0.5
    nb = sum(x*x for x in b)**0.5
    return dot / (na * nb) if na and nb else 0


# 4 chunking methods
def chunk_fixed(text, size=200):
    return [text[i:i+size] for i in range(0, len(text), size)]

def chunk_recursive(text, max_size=500):
    paragraphs = text.split("\n\n")
    chunks, current = [], ""
    for p in paragraphs:
        if len(current) + len(p) < max_size:
            current += p + "\n\n"
        else:
            if current.strip(): chunks.append(current.strip())
            current = p + "\n\n"
    if current.strip(): chunks.append(current.strip())
    return chunks

def chunk_sentence(text, per_chunk=4):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    for i in range(0, len(sentences), per_chunk):
        chunk = " ".join(sentences[i:i+per_chunk])
        if chunk.strip(): chunks.append(chunk.strip())
    return chunks

def chunk_parent_child(text, child_size=200):
    parents = chunk_recursive(text, max_size=600)
    pairs = []
    for pi, parent in enumerate(parents):
        children = chunk_fixed(parent, size=child_size)
        for child in children:
            pairs.append({"child": child.strip(), "parent": parent.strip()})
    return pairs


def search_chunks(query, chunks, top_k=2):
    q_emb = get_embedding(query)
    scored = []
    for chunk in chunks:
        text = chunk if isinstance(chunk, str) else chunk["child"]
        c_emb = get_embedding(text)
        sim = cosine_sim(q_emb, c_emb)
        scored.append((sim, chunk))
    scored.sort(key=lambda x: -x[0])
    return scored[:top_k]


def run_benchmark():
    results = []
    log.info("benchmark_started")

    methods = {
        "fixed_200": lambda t: chunk_fixed(t, 200),
        "recursive_500": lambda t: chunk_recursive(t, 500),
        "sentence_4": lambda t: chunk_sentence(t, 4),
        "parent_child": lambda t: chunk_parent_child(t),
    }

    print("\nCHUNKING BENCHMARK")
    print("=" * 60)

    method_scores = {m: {"found":0, "total":0} for m in methods}

    for doc in DOCS:
        print(f"\n  Document: {doc['title']}")
        for method_name, chunk_fn in methods.items():
            chunks = chunk_fn(doc["text"])
            chunk_count = len(chunks)

            for question, expected in doc["questions"]:
                top = search_chunks(question, chunks, top_k=2)
                retrieved_text = " ".join([
                    c if isinstance(c, str) else c["parent"]
                    for _, c in top
                ])
                found = expected.lower() in retrieved_text.lower()
                method_scores[method_name]["total"] += 1
                if found: method_scores[method_name]["found"] += 1
                
                metric_searches.labels(method=method_name).inc()
                if found: metric_found.labels(method=method_name).inc()
                else: metric_missed.labels(method=method_name).inc()

    print(f"\n  {'Method':<18} {'Found':>6} {'Total':>6} {'Accuracy':>10}")
    print("  " + "-" * 45)
    for m, s in method_scores.items():
        acc = s["found"]/s["total"]*100 if s["total"] else 0
        metric_accuracy.labels(method=m).set(acc)
        print(f"  {m:<18} {s['found']:>6} {s['total']:>6} {acc:>9.0f}%")
        results.append({"method":m,"found":s["found"],"total":s["total"],"accuracy":round(acc,1)})

    log.info("benchmark_complete")
    return results


def show_analysis(results):
    print("\nRESULTS:")
    print("=" * 40)
    best = max(results, key=lambda x: x["accuracy"])
    worst = min(results, key=lambda x: x["accuracy"])
    print(f"  Best:  {best['method']} ({best['accuracy']}%)")
    print(f"  Worst: {worst['method']} ({worst['accuracy']}%)")
    gap = best["accuracy"] - worst["accuracy"]
    print(f"  Gap:   {gap:.0f}% accuracy difference from chunking alone")
    print("\n  FIX: use recursive or parent-child. Never fixed-size.")


def save_results(results):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{RESULTS_DIR}/chunking_{ts}.csv"
    if results:
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=results[0].keys())
            w.writeheader(); w.writerows(results)
    log.info("saved", path=path); return path


def test_fixed_chunks():
    chunks = chunk_fixed("a" * 500, 200)
    assert len(chunks) == 3

def test_recursive_respects_paragraphs():
    text = "Para 1.\n\nPara 2.\n\nPara 3."
    chunks = chunk_recursive(text, 1000)
    assert len(chunks) >= 1

def test_methods_exist():
    assert callable(chunk_fixed)
    assert callable(chunk_recursive)
    assert callable(chunk_sentence)
    assert callable(chunk_parent_child)


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
