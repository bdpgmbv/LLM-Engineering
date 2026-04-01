"""
CHUNKING FAILURES
=================

THE PROBLEM:
    Same question fails with bad chunks, works with good chunks. Proves chunking is #1 quality lever.

HOW TO RUN:
    pip install -r requirements.txt
    python main.py
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


metric_tested = Counter("chunk_fail_tested", "Methods tested")
DOC = """Section 3: Refund Processing

After approval, standard refunds take 5-7 business days for credit cards.

Bank transfers may take 10-14 business days. International transfers add 3-5 business days on top."""

QUESTION = "How long do international bank transfer refunds take?"

def chunk_fixed(text, size=150):
    return [text[i:i+size] for i in range(0, len(text), size)]

def chunk_paragraph(text):
    return [p.strip() for p in text.split("\n\n") if p.strip()]

def run_benchmark():
    results = []
    log.info("benchmark_started")
    bad = chunk_fixed(DOC)
    good = chunk_paragraph(DOC)
    
    print("\n  BAD (fixed 150-char):")
    for i, c in enumerate(bad):
        has = "10-14" in c or "3-5" in c
        print(f"    Chunk {i}: {'HAS ANSWER' if has else '          '} {c[:50]}...")
    
    print("\n  GOOD (paragraph-aware):")
    for i, c in enumerate(good):
        has = "10-14" in c or "3-5" in c
        print(f"    Chunk {i}: {'HAS ANSWER' if has else '          '} {c[:50]}...")
    
    metric_tested.inc(2)
    # Check if answer spans chunks in bad method
    answer_in_one_bad = any("10-14" in c and "3-5" in c for c in bad)
    answer_in_one_good = any("10-14" in c and "3-5" in c for c in good)
    print(f"\n  Bad chunks: full answer in one chunk? {answer_in_one_bad}")
    print(f"  Good chunks: full answer in one chunk? {answer_in_one_good}")
    results = [{"method":"fixed","answer_intact":answer_in_one_bad},{"method":"paragraph","answer_intact":answer_in_one_good}]
    log.info("benchmark_complete"); return results

def show_analysis(results):
    print("\n  Fixed-size splits answers across chunks = WRONG answers")
    print("  Paragraph-aware keeps answers together = CORRECT answers")
    print("  Chunking is #1 quality lever. Fix BEFORE tuning prompts.")


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

def test_doc_exists(): assert len(DOC) > 100

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
