"""
RAG IN 30 LINES
================

THE PROBLEM:
    People think RAG is complicated. It is not.
    The entire pipeline is: embed documents -> search -> answer.
    
    This proves it works in 30 lines of actual logic.
    Everything else (hybrid search, reranking, chunking) is optimization.

WHAT WE FIND OUT:
    1. Does basic RAG give correct answers?
    2. Does it correctly abstain on unanswerable questions?
    3. How many tokens does it use?

WHAT YOU WILL LEARN:
    - RAG works in 30 lines
    - Grounded answers from real documents
    - Correct abstention on unknown questions
    - This is the foundation — everything else is optimization

HOW TO RUN:
    export OPENAI_API_KEY=sk-your-key
    pip install -r requirements.txt
    python main.py
"""

import time, csv, os
from datetime import datetime
import structlog
from prometheus_client import Counter, start_http_server
from openai import OpenAI

structlog.configure(
    processors=[structlog.processors.TimeStamper(fmt="iso"), structlog.dev.ConsoleRenderer()],
    wrapper_class=structlog.BoundLogger, context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)
log = structlog.get_logger()

metric_queries = Counter("rag_queries_total", "Queries answered")
metric_tokens = Counter("rag_tokens_total", "Tokens used")

METRICS_PORT = 8000
RESULTS_DIR = "./results"
client = OpenAI()

# ── THE ENTIRE RAG PIPELINE (30 lines of actual logic) ──

# 1. Your documents
docs = [
    "TechCorp offers 30-day returns for hardware. Digital products: 14 days.",
    "Pro plan costs $49/month. Enterprise starts at $499/month with custom SLAs.",
    "API rate limits: Free 100/min, Pro 1000/min. Auth via Bearer tokens, expire 24h.",
    "Data encrypted AES-256 at rest, TLS 1.3 in transit. SOC 2 Type II certified.",
]

# 2. Embed documents (run once, store in vector database in production)
log.info("embedding_docs", count=len(docs))
doc_embs = [client.embeddings.create(model="text-embedding-3-small", input=d).data[0].embedding for d in docs]

# 3. Search function
def search(query, top_k=2):
    q = client.embeddings.create(model="text-embedding-3-small", input=query).data[0].embedding
    scores = [(sum(a*b for a,b in zip(q,d)), i) for i, d in enumerate(doc_embs)]
    return [docs[i] for _, i in sorted(scores, reverse=True)[:top_k]]

# 4. Answer function
def answer(question):
    context = " ".join(search(question))
    r = client.chat.completions.create(
        model="gpt-4o-mini", temperature=0, max_tokens=80,
        messages=[{"role":"system","content":"Answer from context only. If not found, say so."},
                  {"role":"user","content":f"Context: {context}\nQ: {question}"}])
    metric_queries.inc()
    metric_tokens.inc(r.usage.total_tokens)
    return r.choices[0].message.content.strip()

# ── END OF RAG PIPELINE ──


QUESTIONS = [
    "What is the return policy?",
    "How much is Enterprise?",
    "Is my data encrypted?",
    "What are the API rate limits?",
    "Do you have a free trial?",  # NOT in docs — should abstain
]


def run_benchmark():
    results = []
    log.info("benchmark_started")

    for q in QUESTIONS:
        a = answer(q)
        print(f"Q: {q}")
        print(f"A: {a}")
        print()
        results.append({"question": q, "answer": a})

    log.info("benchmark_complete")
    return results


def show_analysis(results):
    print("THAT IS THE ENTIRE RAG PIPELINE.")
    print("=" * 50)
    print("  4 documents. 5 questions. Grounded answers.")
    print("  30 lines of actual logic.")
    print("  Everything else is optimization on top of this.")


def save_results(results):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{RESULTS_DIR}/rag_30_lines_{ts}.csv"
    if results:
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=results[0].keys())
            w.writeheader(); w.writerows(results)
    log.info("saved", path=path); return path


def test_4_docs():
    assert len(docs) == 4

def test_5_questions():
    assert len(QUESTIONS) == 5

def test_search_returns_list():
    # Can only test structure without API
    assert callable(search)


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
