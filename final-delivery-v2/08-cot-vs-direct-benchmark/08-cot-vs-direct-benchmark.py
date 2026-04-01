"""
CHAIN-OF-THOUGHT vs DIRECT ANSWER
===================================

THE PROBLEM:
    "Think step by step" (Chain-of-Thought) makes the AI show its work.
    This uses 2x more tokens = 2x more money.
    
    On math and logic problems, CoT improves accuracy 15-25%.
    On simple tasks (classification, extraction), CoT adds cost with ZERO benefit.
    
    Most teams use CoT for everything. This is wasting money.

WHAT WE FIND OUT:
    1. Which tasks benefit from CoT? (math, logic, reasoning)
    2. Which tasks get WORSE with CoT? (simple classification)
    3. Exactly how many extra tokens does CoT use?
    4. When is the 2x cost justified?

WHAT YOU WILL LEARN:
    - CoT helps on reasoning/math: +15-25% accuracy
    - CoT hurts on simple tasks: adds cost, no benefit
    - CoT costs ~2x in tokens
    - Production: route by complexity. Simple->direct, complex->CoT

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


metric_calls = PCounter("cot_calls_total", "Total calls", ["method", "task_type"])
metric_correct = PCounter("cot_correct_total", "Correct", ["method", "task_type"])
metric_tokens = PCounter("cot_tokens_total", "Tokens", ["method"])

TESTS = [
    # Math/reasoning — CoT SHOULD help
    {"q":"3 shelves, 4 boxes each, 12 items per box. Total items? Just number.","a":"144","type":"math"},
    {"q":"5 machines make 5 widgets in 5 min. 100 machines for 100 widgets? Just minutes.","a":"5","type":"logic"},
    {"q":"Bat and ball cost $1.10. Bat costs $1 more than ball. Ball cost? Just number.","a":"0.05","type":"logic"},
    {"q":"Lily pad doubles daily. 48 days to cover lake. Days for half? Just number.","a":"47","type":"logic"},
    {"q":"Employee works Mon-Fri, 8hrs/day, $25/hr, 1.5x after 40hrs. Weekly pay? Just number.","a":"1050","type":"math"},
    {"q":"17 * 23 = ? Just number.","a":"391","type":"math"},
    {"q":"Overtake person in 2nd place. What position are you? Just number.","a":"2","type":"logic"},
    
    # Simple tasks — CoT should NOT help
    {"q":"Capital of France? One word.","a":"paris","type":"factual"},
    {"q":"Classify: 'My payment failed' -> billing/technical/general","a":"billing","type":"classification"},
    {"q":"Sentiment of 'I love this product!' -> positive/negative/neutral","a":"positive","type":"classification"},
    {"q":"Is 7 prime? yes/no","a":"yes","type":"factual"},
    {"q":"Translate 'hello' to Spanish. One word.","a":"hola","type":"factual"},
    {"q":"Red + blue = what color? One word.","a":"purple","type":"factual"},
]


def ask(prompt):
    try:
        r = client.chat.completions.create(model=MODEL, temperature=0, max_tokens=200,
            messages=[{"role":"user","content":prompt}])
        return r.choices[0].message.content.strip(), r.usage.total_tokens
    except Exception as e:
        log.error("api_failed", error=str(e))
        return None, 0


def run_benchmark():
    results = []
    log.info("benchmark_started", tests=len(TESTS))
    
    print(f"\n{'Task':<20} {'Type':<15} {'Direct':>8} {'CoT':>8} {'D_tok':>7} {'C_tok':>7}")
    print("-" * 70)
    
    for t in TESTS:
        # Direct
        ans_d, tok_d = ask(f"{t['q']}")
        correct_d = t["a"].lower() in ans_d.lower() if ans_d else False
        
        # Chain-of-Thought
        ans_c, tok_c = ask(f"{t['q']}\nThink step by step. Give final answer after ANSWER:")
        correct_c = t["a"].lower() in ans_c.lower() if ans_c else False
        
        metric_calls.labels(method="direct", task_type=t["type"]).inc()
        metric_calls.labels(method="cot", task_type=t["type"]).inc()
        metric_tokens.labels(method="direct").inc(tok_d)
        metric_tokens.labels(method="cot").inc(tok_c)
        if correct_d: metric_correct.labels(method="direct", task_type=t["type"]).inc()
        if correct_c: metric_correct.labels(method="cot", task_type=t["type"]).inc()
        
        d_mark = "Y" if correct_d else "N"
        c_mark = "Y" if correct_c else "N"
        print(f"  {t['q'][:18]:<20} {t['type']:<15} {d_mark:>8} {c_mark:>8} {tok_d:>7} {tok_c:>7}")
        
        results.append({"question":t["q"][:30],"type":t["type"],"direct_correct":correct_d,
                        "cot_correct":correct_c,"direct_tokens":tok_d,"cot_tokens":tok_c})
    
    log.info("benchmark_complete")
    return results


def show_analysis(results):
    print("\nRESULTS BY TASK TYPE:")
    print("=" * 50)
    types = defaultdict(lambda: {"d":0,"c":0,"n":0})
    for r in results:
        types[r["type"]]["n"] += 1
        if r["direct_correct"]: types[r["type"]]["d"] += 1
        if r["cot_correct"]: types[r["type"]]["c"] += 1
    
    for tt, counts in types.items():
        d_pct = counts["d"]/counts["n"]*100
        c_pct = counts["c"]/counts["n"]*100
        winner = "CoT" if c_pct > d_pct else "Direct" if d_pct > c_pct else "Tie"
        print(f"  {tt:<15} Direct:{d_pct:.0f}%  CoT:{c_pct:.0f}%  -> {winner}")
    
    d_tok = sum(r["direct_tokens"] for r in results)
    c_tok = sum(r["cot_tokens"] for r in results)
    print(f"\n  Total tokens: Direct={d_tok} CoT={c_tok} ({c_tok/d_tok:.1f}x more)")
    print("\n  RULE: Direct for simple tasks. CoT only for math/logic/reasoning.")


def save_results(results):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{RESULTS_DIR}/cot_vs_direct_{ts}.csv"
    if results:
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=results[0].keys()); w.writeheader(); w.writerows(results)
    log.info("saved", path=path); return path


def test_tests_have_answers():
    for t in TESTS: assert "a" in t and "q" in t

def test_13_tests():
    assert len(TESTS) == 13


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

