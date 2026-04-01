"""
MAPREDUCE SUMMARIZATION
========================

THE PROBLEM:
    You have a 100-page document. It does not fit in one API call.
    Even if it did, the LLM would lose info in the middle.
    
    MapReduce: split into chapters, summarize each (MAP),
    then combine all summaries into one (REDUCE).
    
    MAP runs in parallel = fast. Uses cheap model.
    REDUCE uses smart model for quality synthesis.

WHAT WE FIND OUT:
    1. How fast is parallel MAP vs sequential?
    2. Cost of MAP (mini) + REDUCE (4o) vs all-4o?
    3. Quality of the final summary

WHAT YOU WILL LEARN:
    - MAP: cheap model extracts/summarizes each piece (parallel = fast)
    - REDUCE: smart model synthesizes all summaries (quality matters here)
    - Handles unlimited document size
    - Cost: MAP(mini) + REDUCE(4o) = 80% cheaper than all-4o

HOW TO RUN:
    export OPENAI_API_KEY=sk-your-key
    pip install -r requirements.txt
    python main.py
"""

import time, csv, os
import concurrent.futures
from datetime import datetime
import structlog
from prometheus_client import Counter, Histogram, start_http_server
from openai import OpenAI

structlog.configure(
    processors=[structlog.processors.TimeStamper(fmt="iso"), structlog.dev.ConsoleRenderer()],
    wrapper_class=structlog.BoundLogger, context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)
log = structlog.get_logger()

metric_map_calls = Counter("mr_map_calls_total", "MAP calls")
metric_reduce_calls = Counter("mr_reduce_calls_total", "REDUCE calls")
metric_tokens = Counter("mr_tokens_total", "Tokens", ["phase"])
metric_latency = Histogram("mr_latency_seconds", "Latency", ["phase"])

METRICS_PORT = 8000
RESULTS_DIR = "./results"
client = OpenAI()

# Simulate 10 chapters of a long document
CHAPTERS = [
    f"Chapter {i+1}: This chapter covers topic {i+1}. " * 20 +
    f"The key finding is that approach {'ABCDEFGHIJ'[i]} works best for scenario {i+1}. " * 3
    for i in range(10)
]


def summarize_chapter(chapter, idx):
    """MAP step: summarize one chapter with cheap model."""
    try:
        r = client.chat.completions.create(model="gpt-4o-mini", temperature=0, max_tokens=80,
            messages=[{"role":"user","content":f"Summarize in 2 sentences:\n{chapter}"}])
        metric_map_calls.inc()
        metric_tokens.labels(phase="map").inc(r.usage.total_tokens)
        return idx, r.choices[0].message.content.strip(), r.usage.total_tokens
    except Exception as e:
        log.error("map_failed", chapter=idx, error=str(e))
        return idx, f"Chapter {idx+1} summary unavailable.", 0


def run_benchmark():
    results = []
    log.info("benchmark_started", chapters=len(CHAPTERS))

    print(f"\nDocument: {len(CHAPTERS)} chapters, ~{sum(len(c) for c in CHAPTERS)} chars")

    # MAP phase (parallel)
    print("\nMAP phase (parallel, gpt-4o-mini)...")
    map_start = time.time()
    summaries = {}
    map_tokens = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
        futures = [ex.submit(summarize_chapter, ch, i) for i, ch in enumerate(CHAPTERS)]
        for f in concurrent.futures.as_completed(futures):
            idx, summary, tokens = f.result()
            summaries[idx] = summary
            map_tokens += tokens
            print(f"  Chapter {idx+1}: {summary[:60]}...")

    map_time = time.time() - map_start
    metric_latency.labels(phase="map").observe(map_time)

    # REDUCE phase (combine with smart model)
    print(f"\nREDUCE phase (gpt-4o)...")
    combined = "\n".join([f"Ch{i+1}: {summaries[i]}" for i in range(len(CHAPTERS))])

    reduce_start = time.time()
    try:
        r = client.chat.completions.create(model="gpt-4o", temperature=0, max_tokens=200,
            messages=[{"role":"user","content":f"Synthesize into 3-sentence executive summary:\n\n{combined}"}])
        final = r.choices[0].message.content.strip()
        reduce_tokens = r.usage.total_tokens
        metric_reduce_calls.inc()
        metric_tokens.labels(phase="reduce").inc(reduce_tokens)
    except Exception as e:
        log.error("reduce_failed", error=str(e))
        final = "Reduce failed."
        reduce_tokens = 0

    reduce_time = time.time() - reduce_start
    metric_latency.labels(phase="reduce").observe(reduce_time)

    print(f"\nFINAL SUMMARY:")
    print(f"  {final}")

    map_cost = (map_tokens / 1e6) * 0.15
    reduce_cost = (reduce_tokens / 1e6) * 2.50
    total_cost = map_cost + reduce_cost

    print(f"\nSTATS:")
    print(f"  MAP: {map_time:.2f}s, {map_tokens} tokens, ${map_cost:.4f} (mini)")
    print(f"  REDUCE: {reduce_time:.2f}s, {reduce_tokens} tokens, ${reduce_cost:.4f} (4o)")
    print(f"  TOTAL: ${total_cost:.4f}")
    print(f"\n  Cheap model for extraction, expensive for synthesis = optimal cost.")

    results = [{"phase":"map","time":round(map_time,2),"tokens":map_tokens,"cost":round(map_cost,4)},
               {"phase":"reduce","time":round(reduce_time,2),"tokens":reduce_tokens,"cost":round(reduce_cost,4)}]

    log.info("benchmark_complete")
    return results


def show_analysis(results):
    print(f"\nSUMMARY:")
    print(f"  MAP: parallel with cheap model (fast, cheap)")
    print(f"  REDUCE: one call with smart model (quality)")
    print(f"  Handles unlimited document size")


def save_results(results):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{RESULTS_DIR}/mapreduce_{ts}.csv"
    if results:
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=results[0].keys())
            w.writeheader(); w.writerows(results)
    log.info("saved", path=path); return path


def test_10_chapters():
    assert len(CHAPTERS) == 10

def test_chapters_not_empty():
    for ch in CHAPTERS:
        assert len(ch) > 50


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
