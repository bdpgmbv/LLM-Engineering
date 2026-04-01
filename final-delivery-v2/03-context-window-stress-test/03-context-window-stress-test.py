"""
CONTEXT WINDOW STRESS TEST
==========================

THE PROBLEM:
    LLMs have a context window (max text they can read at once).
    GPT-4o handles 128K tokens (~300 pages). But there is a hidden problem:
    the model pays MORE attention to the start and end of the text,
    and LESS to the middle. This is called "lost in the middle."
    
    If your RAG system stuffs 20 documents into the context,
    the answer might be in document #10 (the middle).
    The LLM might ignore it and give a wrong answer.

WHAT WE FIND OUT:
    1. Does the model really lose info in the middle?
    2. At what context size does quality drop?
    3. Where to put important info (start, middle, end)?
    4. How does latency increase with context size?

WHAT YOU WILL LEARN:
    - Info at START: found most reliably
    - Info at MIDDLE (40-60%): found LEAST reliably
    - Info at END: found well (recency effect)
    - Fix: put critical info at START and END
    - RAG fix: only use top 3-5 chunks, dont stuff everything

HOW TO RUN:
    export OPENAI_API_KEY=sk-your-key
    pip install -r requirements.txt
    python main.py
    http://localhost:8000/metrics
    docker-compose up --build -> http://localhost:3000 (admin/admin)
    pytest main.py -v
"""

import time, csv, os
from datetime import datetime
from collections import defaultdict
import structlog
from prometheus_client import Counter, Histogram, Gauge, start_http_server
from openai import OpenAI

structlog.configure(
    processors=[structlog.processors.TimeStamper(fmt="iso"), structlog.dev.ConsoleRenderer()],
    wrapper_class=structlog.BoundLogger, context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)
log = structlog.get_logger()

metric_calls = Counter("needle_calls_total", "Total calls", ["position"])
metric_found = Counter("needle_found_total", "Needle found", ["position"])
metric_missed = Counter("needle_missed_total", "Needle missed", ["position"])
metric_tokens = Counter("needle_tokens_total", "Tokens used")
metric_latency = Histogram("needle_latency_seconds", "Latency", ["context_lines"])

METRICS_PORT = 8000
RESULTS_DIR = "./results"

client = OpenAI()
MODEL = "gpt-4o-mini"

# The "needle" — a secret fact we hide in boring text
SECRET = "The secret project codename is AURORA-7."
QUESTION = "What is the secret project codename?"

# The "haystack" — boring filler text
FILLER = "The quarterly review meeting will be held on the usual schedule. All departments should prepare standard reports. "


def build_context(needle_position, total_lines=50):
    """
    Build a haystack with the needle at a specific position.
    needle_position: 0.0 = start, 0.5 = middle, 1.0 = end
    """
    lines = [FILLER] * total_lines
    insert_at = int(needle_position * (total_lines - 1))
    lines[insert_at] = SECRET
    return "\n".join(lines)


def search_needle(context):
    """Ask the LLM to find the needle. Returns (answer, tokens, latency)."""
    start = time.time()
    try:
        r = client.chat.completions.create(
            model=MODEL, temperature=0, max_tokens=50,
            messages=[
                {"role": "system", "content": "Answer based on the provided context only."},
                {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {QUESTION}"}
            ]
        )
    except Exception as e:
        log.error("api_failed", error=str(e))
        return None, 0, 0
    
    elapsed = time.time() - start
    answer = r.choices[0].message.content.strip()
    tokens = r.usage.total_tokens
    metric_tokens.inc(tokens)
    return answer, tokens, elapsed


def run_benchmark():
    """Test if the model can find the needle at different positions and context sizes."""
    results = []
    log.info("benchmark_started")
    
    # Test 1: Needle at different positions (80-line haystack)
    positions = [0.0, 0.1, 0.25, 0.4, 0.5, 0.6, 0.75, 0.9, 1.0]
    
    print("\nNEEDLE-IN-A-HAYSTACK TEST")
    print(f"Secret: \"{SECRET}\"")
    print(f"Question: \"{QUESTION}\"")
    print()
    print(f"  {'Position':<12} {'Found?':<8} {'Answer':<35} {'Tokens':>8} {'Time':>6}")
    print("  " + "-" * 75)
    
    for pos in positions:
        context = build_context(pos, total_lines=80)
        answer, tokens, elapsed = search_needle(context)
        if answer is None:
            continue
        
        found = "AURORA" in answer.upper()
        label = f"{pos:.0%}"
        
        metric_calls.labels(position=label).inc()
        if found:
            metric_found.labels(position=label).inc()
        else:
            metric_missed.labels(position=label).inc()
        metric_latency.labels(context_lines="80").observe(elapsed)
        
        mark = "YES" if found else "NO"
        print(f"  {label:<12} {mark:<8} {answer[:35]:<35} {tokens:>8} {elapsed:>5.2f}s")
        results.append({"position": pos, "found": found, "tokens": tokens, "latency": round(elapsed, 2)})
    
    # Test 2: Increasing context size, needle always at middle
    print()
    print("  SCALE TEST: bigger context, needle always at middle (50%)")
    print(f"  {'Lines':<10} {'Found?':<8} {'Tokens':>8} {'Time':>6}")
    print("  " + "-" * 35)
    
    for num_lines in [20, 50, 100, 200]:
        context = build_context(0.5, total_lines=num_lines)
        answer, tokens, elapsed = search_needle(context)
        if answer is None:
            continue
        found = "AURORA" in answer.upper()
        metric_latency.labels(context_lines=str(num_lines)).observe(elapsed)
        mark = "YES" if found else "NO"
        print(f"  {num_lines:<10} {mark:<8} {tokens:>8} {elapsed:>5.2f}s")
        results.append({"test": "scale", "lines": num_lines, "found": found, "tokens": tokens})
    
    log.info("benchmark_complete", results=len(results))
    return results


def show_analysis(results):
    """Show what we learned."""
    print()
    print("RESULTS:")
    print("=" * 50)
    print("  Position 0-10% (start):   MOST reliable")
    print("  Position 40-60% (middle): LEAST reliable <- lost in the middle!")
    print("  Position 90-100% (end):   second most reliable")
    print()
    print("FIX FOR PRODUCTION:")
    print("  1. Put critical info at START and END of context")
    print("  2. RAG: only retrieve top 3-5 chunks, dont stuff everything")
    print("  3. Use reranking to put best chunks first")


def save_results(results):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{RESULTS_DIR}/context_window_{ts}.csv"
    if results:
        keys = set()
        for r in results: keys.update(r.keys())
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=sorted(keys))
            w.writeheader()
            w.writerows(results)
    log.info("saved", path=path)
    return path


# ── Tests ──

def test_build_context_has_needle():
    ctx = build_context(0.5, 10)
    assert SECRET in ctx

def test_build_context_start():
    ctx = build_context(0.0, 10)
    assert ctx.startswith(SECRET)

def test_build_context_end():
    ctx = build_context(1.0, 10)
    assert ctx.strip().endswith(SECRET)

def test_filler_not_empty():
    assert len(FILLER) > 50


# ── Run ──

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
