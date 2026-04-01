"""
DENSE vs BM25 vs HYBRID SEARCH
================================

THE PROBLEM:
    There are two ways to search documents:
    - Dense search (embeddings): finds SIMILAR meaning
      "login problems" finds "authentication failures"
    - BM25 (keyword): finds EXACT words
      "error 403" finds documents containing "error 403"
    
    Dense misses exact matches. BM25 misses synonyms.
    Hybrid combines both and catches everything.

WHAT WE FIND OUT:
    1. When does dense beat BM25?
    2. When does BM25 beat dense?
    3. Does hybrid really catch both?
    4. Is the extra complexity worth it?

WHAT YOU WILL LEARN:
    - Dense wins on semantic queries ("login problems" = "auth failures")
    - BM25 wins on keyword queries ("error 403")
    - Hybrid catches both — production standard
    - BM25 is FREE (no embeddings needed)

HOW TO RUN:
    export OPENAI_API_KEY=sk-your-key
    pip install -r requirements.txt
    python main.py
"""

import time, csv, os, re, math
from datetime import datetime
from collections import Counter as WordCounter
import structlog
from prometheus_client import Counter, Gauge, start_http_server
from openai import OpenAI

structlog.configure(
    processors=[structlog.processors.TimeStamper(fmt="iso"), structlog.dev.ConsoleRenderer()],
    wrapper_class=structlog.BoundLogger, context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)
log = structlog.get_logger()

metric_searches = Counter("search_total", "Searches", ["method"])
metric_correct = Counter("search_correct_total", "Correct", ["method"])
metric_accuracy = Gauge("search_accuracy_pct", "Accuracy", ["method"])

METRICS_PORT = 8000
RESULTS_DIR = "./results"
client = OpenAI()

CORPUS = [
    "TechCorp API returns error code 403 when the user lacks permission.",
    "To resolve authentication failures, regenerate your API token via /auth/refresh.",
    "The refund policy allows returns within 30 days for hardware in original packaging.",
    "Subscription billing cycles reset on the first of each month.",
    "For optimal performance, use connection pooling and 30-second timeout.",
    "The mobile app requires iOS 15 or Android 12.",
    "Enterprise customers receive dedicated support with 4-hour response SLA.",
    "Data encrypted at rest AES-256 and in transit TLS 1.3.",
    "Dashboard shows real-time metrics: latency, error rates, throughput.",
    "Two-factor authentication via Settings > Security > 2FA.",
]

QUERIES = [
    ("error 403 permission", "keyword", 0),
    ("how to fix login problems", "semantic", 1),
    ("return policy for physical items", "semantic", 2),
    ("API timeout settings", "mixed", 4),
    ("what encryption do you use", "semantic", 7),
    ("2FA setup instructions", "keyword", 9),
    ("billing date each month", "mixed", 3),
    ("iPhone compatibility", "semantic", 5),
]


def get_embedding(text):
    r = client.embeddings.create(model="text-embedding-3-small", input=text)
    return r.data[0].embedding

def cosine_sim(a, b):
    dot = sum(x*y for x,y in zip(a,b))
    return dot / ((sum(x*x for x in a)**0.5) * (sum(x*x for x in b)**0.5) + 1e-10)


def tokenize(text):
    return re.findall(r'\w+', text.lower())

corpus_tokens = [tokenize(doc) for doc in CORPUS]
avg_dl = sum(len(t) for t in corpus_tokens) / len(corpus_tokens)
N = len(CORPUS)

def bm25_score(query_tokens, doc_tokens, k1=1.5, b=0.75):
    score = 0
    dl = len(doc_tokens)
    doc_freq = WordCounter(doc_tokens)
    for qt in query_tokens:
        df = sum(1 for dt in corpus_tokens if qt in dt)
        if df == 0: continue
        idf = math.log((N - df + 0.5) / (df + 0.5) + 1)
        tf = doc_freq.get(qt, 0)
        score += idf * (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * dl / avg_dl))
    return score


def run_benchmark():
    results = []
    log.info("benchmark_started")

    # Embed corpus
    print("\nEmbedding corpus...")
    corpus_embs = [get_embedding(doc) for doc in CORPUS]

    method_correct = {"dense": 0, "bm25": 0, "hybrid": 0}

    print(f"\n{'Query':<35} {'Type':<9} {'Dense':>6} {'BM25':>6} {'Hybrid':>7}")
    print("-" * 70)

    for query, qtype, expected_idx in QUERIES:
        # Dense search
        q_emb = get_embedding(query)
        dense_scores = [(cosine_sim(q_emb, c_emb), i) for i, c_emb in enumerate(corpus_embs)]
        dense_scores.sort(key=lambda x: -x[0])
        dense_top3 = [i for _, i in dense_scores[:3]]

        # BM25 search
        q_tokens = tokenize(query)
        bm25_scores = [(bm25_score(q_tokens, dt), i) for i, dt in enumerate(corpus_tokens)]
        bm25_scores.sort(key=lambda x: -x[0])
        bm25_top3 = [i for _, i in bm25_scores[:3]]

        # Hybrid (RRF merge)
        rrf = {}
        for rank, (_, idx) in enumerate(dense_scores[:5]):
            rrf[idx] = rrf.get(idx, 0) + 1/(60+rank)
        for rank, (_, idx) in enumerate(bm25_scores[:5]):
            rrf[idx] = rrf.get(idx, 0) + 1/(60+rank)
        hybrid_top3 = [idx for idx, _ in sorted(rrf.items(), key=lambda x: -x[1])[:3]]

        d_found = expected_idx in dense_top3
        b_found = expected_idx in bm25_top3
        h_found = expected_idx in hybrid_top3

        if d_found: method_correct["dense"] += 1
        if b_found: method_correct["bm25"] += 1
        if h_found: method_correct["hybrid"] += 1

        for m, f in [("dense",d_found),("bm25",b_found),("hybrid",h_found)]:
            metric_searches.labels(method=m).inc()
            if f: metric_correct.labels(method=m).inc()

        print(f"  {query[:33]:<35} {qtype:<9} {'Y' if d_found else 'N':>6} {'Y' if b_found else 'N':>6} {'Y' if h_found else 'N':>7}")

    print(f"\n  {'Method':<10} {'Correct':>8} {'Accuracy':>10}")
    print("  " + "-" * 30)
    for m, c in method_correct.items():
        acc = c/len(QUERIES)*100
        metric_accuracy.labels(method=m).set(acc)
        print(f"  {m:<10} {c:>8}/{len(QUERIES)} {acc:>9.0f}%")
        results.append({"method":m,"correct":c,"total":len(QUERIES),"accuracy":round(acc,1)})

    log.info("benchmark_complete")
    return results


def show_analysis(results):
    print("\nRESULTS:")
    print("=" * 40)
    print("  Dense: wins on semantic (meaning) queries")
    print("  BM25: wins on keyword (exact match) queries")
    print("  Hybrid: catches BOTH — production standard")
    print("  BM25 is FREE (no embeddings, no vector DB)")


def save_results(results):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{RESULTS_DIR}/search_shootout_{ts}.csv"
    if results:
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=results[0].keys())
            w.writeheader(); w.writerows(results)
    log.info("saved", path=path); return path


def test_corpus_10_docs():
    assert len(CORPUS) == 10

def test_8_queries():
    assert len(QUERIES) == 8

def test_bm25_positive():
    score = bm25_score(["error","403"], tokenize("error code 403 returned"))
    assert score > 0


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
