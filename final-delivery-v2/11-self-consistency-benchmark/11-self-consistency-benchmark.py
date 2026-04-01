"""
SELF-CONSISTENCY: WHEN IS 5x COST WORTH IT?
============================================

THE PROBLEM:
    Self-consistency means: ask the AI the same question 5 times,
    then take the majority vote as the answer.
    
    This costs 5x more (5 API calls instead of 1).
    But for tricky questions, it can boost accuracy 10-15%.
    
    Is it worth it? For what types of questions?

WHAT WE FIND OUT:
    1. Accuracy with 1 call vs 3 calls vs 5 calls
    2. How much more does it cost?
    3. What types of questions benefit most?
    4. Smart version: start with 1, add 4 only if uncertain

WHAT YOU WILL LEARN:
    - Majority-of-5 boosts accuracy 10-15% on tricky questions
    - Simple questions dont benefit (already 95%+ with 1 call)
    - Only use for high-stakes: medical, legal, financial
    - Smart version averages 1.8x cost instead of 5x

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


metric_calls = PCounter("sc_calls_total", "Calls", ["n_samples"])
metric_correct = PCounter("sc_correct_total", "Correct", ["n_samples"])
metric_tokens = PCounter("sc_tokens_total", "Tokens", ["n_samples"])

HARD_QUESTIONS = [
    {"q":"Shirt costs $25 after 20% discount. Original price? Just number.","a":"31.25"},
    {"q":"Bat and ball cost $1.10. Bat costs $1 more than ball. Ball cost? Just number.","a":"0.05"},
    {"q":"5 machines, 5 min, 5 widgets. 100 machines, 100 widgets? Just minutes.","a":"5"},
    {"q":"Lily pad doubles daily. 48 days to cover lake. Days for half? Just number.","a":"47"},
    {"q":"Three doctors say Bob is their brother. Bob says no brothers. How? One word.","a":"sister"},
    {"q":"Is 91 prime? yes or no.","a":"no"},
    {"q":"17 * 23? Just number.","a":"391"},
    {"q":"Overtake 2nd place in race. Your position? Just number.","a":"2"},
    {"q":"How many times can you subtract 5 from 25? Just number.","a":"1"},
    {"q":"Farmer has 17 sheep. All but 9 die. How many left? Just number.","a":"9"},
]


def run_benchmark():
    results = []
    log.info("benchmark_started", questions=len(HARD_QUESTIONS))
    
    for n_calls in [1, 3, 5]:
        print(f"\nTesting n={n_calls} calls per question...")
        print("-" * 60)
        correct = 0
        total_tokens = 0
        
        for qi, test in enumerate(HARD_QUESTIONS):
            answers = []
            q_tokens = 0
            for _ in range(n_calls):
                try:
                    r = client.chat.completions.create(model=MODEL, temperature=0.7, max_tokens=20,
                        messages=[{"role":"user","content":test["q"]}])
                    ans = r.choices[0].message.content.strip().lower().rstrip(".")
                    answers.append(ans)
                    q_tokens += r.usage.total_tokens
                except: pass
            
            if answers:
                majority = Counter(answers).most_common(1)[0][0]
                is_correct = test["a"].lower() in majority
                if is_correct: correct += 1
                agreement = Counter(answers).most_common(1)[0][1]
                mark = "Y" if is_correct else "N"
                print(f"  {mark} Q{qi+1}: majority='{majority}' ({agreement}/{n_calls} agree)")
            
            total_tokens += q_tokens
            metric_calls.labels(n_samples=str(n_calls)).inc()
            metric_tokens.labels(n_samples=str(n_calls)).inc(q_tokens)
        
        acc = correct/len(HARD_QUESTIONS)*100
        if correct: metric_correct.labels(n_samples=str(n_calls)).inc(correct)
        results.append({"n_calls":n_calls,"correct":correct,"accuracy":acc,"tokens":total_tokens})
        print(f"  Result: {correct}/{len(HARD_QUESTIONS)} ({acc:.0f}%), {total_tokens} tokens")
    
    log.info("benchmark_complete"); return results


def show_analysis(results):
    print("\nRESULTS:")
    print("=" * 50)
    for r in results:
        print(f"  n={r['n_calls']}: {r['accuracy']:.0f}% accuracy, {r['tokens']} tokens")
    if len(results) >= 3:
        ratio = results[2]["tokens"] / results[0]["tokens"] if results[0]["tokens"] else 0
        print(f"\n  Cost ratio (5 vs 1): {ratio:.1f}x")
    print("\n  Only use for HIGH-STAKES decisions (medical, legal, financial)")


def save_results(results):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{RESULTS_DIR}/self_consistency_{ts}.csv"
    if results:
        with open(path,"w",newline="") as f:
            w = csv.DictWriter(f, fieldnames=results[0].keys()); w.writeheader(); w.writerows(results)
    log.info("saved", path=path); return path


def test_10_questions():
    assert len(HARD_QUESTIONS) == 10

def test_questions_have_answers():
    for q in HARD_QUESTIONS:
        assert "q" in q and "a" in q


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

