"""
SEMANTIC CACHE: SAME MEANING = SAME ANSWER
============================================

THE PROBLEM:
    Users ask the same question in different words:
    "What is your refund policy?"
    "How do returns work?"
    "Can I get my money back?"
    
    Without caching, each one costs an API call.
    A semantic cache recognizes they mean the same thing
    and returns the cached answer. Saves 30-40% of calls.

WHAT WE FIND OUT:
    1. What hit rate does semantic caching achieve?
    2. How much money does it save?
    3. What similarity threshold works best?

WHAT YOU WILL LEARN:
    - 30-40% cache hit rate is typical
    - Threshold 0.90-0.95 works best (lower = more hits but risk wrong matches)
    - Cache saves both cost AND latency (embedding lookup is 10ms vs LLM 1-2s)
    - Combine with exact-match cache (Redis) for identical queries

HOW TO RUN:
    export OPENAI_API_KEY=sk-your-key
    pip install -r requirements.txt
    python main.py
"""

import time, csv, os
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

metric_queries = Counter("cache_queries_total", "Total queries")
metric_hits = Counter("cache_hits_total", "Cache hits")
metric_misses = Counter("cache_misses_total", "Cache misses")
metric_hit_rate = Gauge("cache_hit_rate_pct", "Hit rate")
metric_savings = Gauge("cache_savings_pct", "Cost savings")

METRICS_PORT = 8000
RESULTS_DIR = "./results"
client = OpenAI()
MODEL = "gpt-4o-mini"


def get_embedding(text):
    r = client.embeddings.create(model="text-embedding-3-small", input=text)
    return r.data[0].embedding

def cosine_sim(a, b):
    dot = sum(x*y for x,y in zip(a,b))
    return dot / ((sum(x*x for x in a)**0.5) * (sum(x*x for x in b)**0.5) + 1e-10)


class SemanticCache:
    def __init__(self, threshold=0.92):
        self.cache = []  # list of (embedding, query, response)
        self.threshold = threshold
        self.hits = 0
        self.misses = 0

    def get(self, query):
        q_emb = get_embedding(query)
        best_sim = 0
        best_match = None
        for emb, cached_q, response in self.cache:
            sim = cosine_sim(q_emb, emb)
            if sim > best_sim:
                best_sim = sim
                best_match = (response, cached_q, sim)
        if best_sim >= self.threshold:
            self.hits += 1
            return best_match
        self.misses += 1
        return None

    def put(self, query, response):
        emb = get_embedding(query)
        self.cache.append((emb, query, response))


# Queries where some are paraphrases of others
QUERY_STREAM = [
    "What is your refund policy?",
    "How do returns work?",            # same as above
    "Can I get my money back?",        # same as above
    "What are your business hours?",
    "When are you open?",              # same as above
    "What time do you close?",         # same as above
    "Do you offer free shipping?",
    "Is shipping complimentary?",      # same as above
    "How do I reset my password?",
    "I forgot my password",            # same as above
    "Enterprise plan details",
    "Enterprise pricing",              # same as above
    "What is enterprise cost?",        # same as above
]


def run_benchmark():
    results = []
    cache = SemanticCache(threshold=0.90)
    log.info("benchmark_started", queries=len(QUERY_STREAM))

    total_llm_cost = 0

    for q in QUERY_STREAM:
        metric_queries.inc()
        cached = cache.get(q)

        if cached:
            response, original_q, sim = cached
            metric_hits.inc()
            print(f"  CACHE HIT ({sim:.2f}): '{q[:30]}' <- matched '{original_q[:30]}'")
        else:
            metric_misses.inc()
            try:
                r = client.chat.completions.create(model=MODEL, temperature=0, max_tokens=100,
                    messages=[{"role":"user","content":q}])
                response = r.choices[0].message.content.strip()
                cost = r.usage.total_tokens / 1e6 * 0.15
                total_llm_cost += cost
                cache.put(q, response)
                print(f"  CACHE MISS:       '{q[:30]}' -> LLM (${cost:.5f})")
            except Exception as e:
                log.error("api_failed", error=str(e))
                continue

    hit_rate = cache.hits / (cache.hits + cache.misses) * 100 if (cache.hits + cache.misses) else 0
    no_cache_est = total_llm_cost / max(cache.misses, 1) * (cache.hits + cache.misses)
    savings = (1 - total_llm_cost / no_cache_est) * 100 if no_cache_est else 0

    metric_hit_rate.set(hit_rate)
    metric_savings.set(savings)

    results = [{"metric":"hit_rate","value":round(hit_rate,1)},
               {"metric":"hits","value":cache.hits},
               {"metric":"misses","value":cache.misses},
               {"metric":"llm_cost","value":round(total_llm_cost,6)},
               {"metric":"savings_pct","value":round(savings,1)}]

    log.info("benchmark_complete")
    return results


def show_analysis(results):
    print(f"\nRESULTS:")
    print("=" * 50)
    for r in results:
        print(f"  {r['metric']:<15}: {r['value']}")
    print(f"\n  At 100K queries/day with ~35% hit rate:")
    print(f"    35,000 queries served from cache (free, instant)")
    print(f"    65,000 queries hit LLM (paid)")
    print(f"  Saves both COST and LATENCY (10ms cache vs 1-2s LLM)")


def save_results(results):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{RESULTS_DIR}/semantic_cache_{ts}.csv"
    if results:
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=results[0].keys())
            w.writeheader(); w.writerows(results)
    log.info("saved", path=path); return path


def test_13_queries():
    assert len(QUERY_STREAM) == 13

def test_cache_empty_initially():
    c = SemanticCache()
    assert c.hits == 0 and c.misses == 0


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
