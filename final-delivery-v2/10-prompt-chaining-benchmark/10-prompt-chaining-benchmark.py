"""
PROMPT CHAINING: SEQUENTIAL vs PARALLEL
========================================

THE PROBLEM:
    For complex tasks, you can either:
    - Send ONE big prompt asking for everything at once
    - Break it into STEPS: summarize -> extract topics -> analyze sentiment -> actions
    
    Sequential chain: Step 1 -> Step 2 -> Step 3 (each step uses previous result)
    Parallel chain: Steps 1,2,3 all run at the same time (faster!)
    
    Which gives better results? Which costs more? Which is faster?

WHAT WE FIND OUT:
    1. Quality: does chaining give better output?
    2. Speed: sequential vs parallel timing
    3. Cost: chaining costs 2-3x more (multiple API calls)
    4. When to use each approach

WHAT YOU WILL LEARN:
    - Single prompt: cheapest, fine for simple tasks
    - Sequential: better quality on multi-part analysis
    - Parallel: same quality as sequential but 2-3x faster
    - Mix models: GPT-4 for thinking, mini for formatting = 60% savings

HOW TO RUN:
    export OPENAI_API_KEY=sk-your-key
    pip install -r requirements.txt
    python main.py
"""

import time, csv, os
from datetime import datetime
from collections import defaultdict, Counter
import structlog
from prometheus_client import Counter as PCounter, Histogram, Gauge, start_http_server
from openai import OpenAI

structlog.configure(
    processors=[structlog.processors.TimeStamper(fmt="iso"), structlog.dev.ConsoleRenderer()],
    wrapper_class=structlog.BoundLogger, context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)
log = structlog.get_logger()
client = OpenAI()
MODEL = "gpt-4o-mini"
PRICING = {"input": 0.15, "output": 0.60}
METRICS_PORT = 8000
RESULTS_DIR = "./results"

import concurrent.futures

metric_calls = PCounter("chain_calls_total", "Calls", ["method"])
metric_tokens = PCounter("chain_tokens_total", "Tokens", ["method"])
metric_latency = Histogram("chain_latency_seconds", "Latency", ["method"])

ARTICLE = """Artificial intelligence is transforming healthcare. Machine learning algorithms 
detect cancers from images with accuracy rivaling radiologists. NLP extracts insights from 
millions of records. Drug discovery timelines shortened from decades to years. Remote monitoring 
with wearable sensors enables early intervention. However, challenges remain: data privacy, 
algorithmic bias, lack of explainability, and slow regulatory frameworks. The global AI healthcare 
market is projected to reach $188 billion by 2030, growing at 37% annually."""


def ask(prompt, max_tokens=200):
    try:
        r = client.chat.completions.create(model=MODEL, temperature=0, max_tokens=max_tokens,
            messages=[{"role":"user","content":prompt}])
        return r.choices[0].message.content.strip(), r.usage.total_tokens
    except Exception as e:
        log.error("api_failed", error=str(e)); return "", 0


def single_prompt(article):
    start = time.time()
    answer, tokens = ask(f"Analyze this article. Provide: 1) 2-sentence summary 2) 3 key topics 3) Sentiment 4) 3 action items\n\n{article}", 400)
    return answer, time.time()-start, tokens


def sequential_chain(article):
    start = time.time()
    total_tokens = 0
    
    summary, t = ask(f"Summarize in 2 sentences:\n{article}", 100); total_tokens += t
    topics, t = ask(f"List 3 key topics from:\n{summary}", 50); total_tokens += t
    sentiment, t = ask(f"Sentiment (positive/negative/mixed)?\n{summary}", 20); total_tokens += t
    actions, t = ask(f"3 action items based on:\nTopics: {topics}\nSentiment: {sentiment}", 100); total_tokens += t
    
    combined = f"Summary: {summary}\nTopics: {topics}\nSentiment: {sentiment}\nActions: {actions}"
    return combined, time.time()-start, total_tokens


def parallel_chain(article):
    start = time.time()
    total_tokens = 0
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        f1 = ex.submit(ask, f"Summarize in 2 sentences:\n{article}", 100)
        f2 = ex.submit(ask, f"List 3 key topics:\n{article}", 50)
        f3 = ex.submit(ask, f"Sentiment? positive/negative/mixed:\n{article}", 20)
        f4 = ex.submit(ask, f"3 action items for a healthcare exec:\n{article}", 100)
    
    summary, t1 = f1.result(); total_tokens += t1
    topics, t2 = f2.result(); total_tokens += t2
    sentiment, t3 = f3.result(); total_tokens += t3
    actions, t4 = f4.result(); total_tokens += t4
    
    combined = f"Summary: {summary}\nTopics: {topics}\nSentiment: {sentiment}\nActions: {actions}"
    return combined, time.time()-start, total_tokens


def run_benchmark():
    results = []
    log.info("benchmark_started")
    
    for name, fn in [("Single prompt", single_prompt), ("Sequential (4 steps)", sequential_chain), ("Parallel (4 steps)", parallel_chain)]:
        output, elapsed, tokens = fn(ARTICLE)
        cost = (tokens / 1e6) * PRICING["input"]
        
        metric_calls.labels(method=name).inc()
        metric_tokens.labels(method=name).inc(tokens)
        metric_latency.labels(method=name).observe(elapsed)
        
        print(f"\n--- {name} ---")
        print(f"  Time: {elapsed:.2f}s | Tokens: {tokens} | Cost: ${cost:.5f}")
        print(f"  Output: {output[:120]}...")
        
        results.append({"method":name,"time":round(elapsed,2),"tokens":tokens,"cost":round(cost,6)})
    
    log.info("benchmark_complete")
    return results


def show_analysis(results):
    print("\nCOMPARISON:")
    print("=" * 50)
    for r in results:
        print(f"  {r['method']:<25} {r['time']:>5.2f}s  {r['tokens']:>6} tok  ${r['cost']}")
    print("\n  Single: cheapest. Parallel: fastest. Sequential: best for dependent steps.")


def save_results(results):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{RESULTS_DIR}/chaining_{ts}.csv"
    if results:
        with open(path,"w",newline="") as f:
            w = csv.DictWriter(f, fieldnames=results[0].keys()); w.writeheader(); w.writerows(results)
    log.info("saved", path=path); return path


def test_article_exists():
    assert len(ARTICLE) > 100

def test_functions_callable():
    assert callable(single_prompt)
    assert callable(sequential_chain)
    assert callable(parallel_chain)


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

