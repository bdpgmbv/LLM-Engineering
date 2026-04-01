"""
PROMPT A/B TESTER
==================

THE PROBLEM:
    You wrote two versions of a prompt. Which one is better?
    "I think prompt B is better" is not good enough. You need DATA.
    
    This tool: feed 2 prompt variants + test cases -> run both ->
    compare accuracy -> declare statistical winner.

WHAT WE FIND OUT:
    1. Accuracy of prompt A vs prompt B on 15 test cases
    2. Token cost difference
    3. Where they disagree (edge cases to study)

WHAT YOU WILL LEARN:
    - Always A/B test prompts before deploying
    - 15-50 test cases is enough to see a difference
    - Deploy the winner, keep the loser for comparison
    - Re-run monthly — model updates change which prompt wins

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

metric_calls = Counter("ab_calls_total", "Calls", ["variant"])
metric_correct = Counter("ab_correct_total", "Correct", ["variant"])
metric_accuracy = Gauge("ab_accuracy_pct", "Accuracy", ["variant"])

METRICS_PORT = 8000
RESULTS_DIR = "./results"
client = OpenAI()
MODEL = "gpt-4o-mini"

# Two prompt variants to compare
PROMPT_A = "Classify this customer query into one category: billing, technical, or general. Just the category."
PROMPT_B = "You are a support classifier. Given a query, respond with exactly one word: billing, technical, or general. Consider the primary intent."

TESTS = [
    ("My card was charged twice", "billing"),
    ("App crashes on startup", "technical"),
    ("What are your hours?", "general"),
    ("Refund not received after 10 days", "billing"),
    ("Cant connect to API", "technical"),
    ("Do you have a free plan?", "general"),
    ("Invoice shows wrong amount", "billing"),
    ("Error 404 on dashboard", "technical"),
    ("How do I contact support?", "general"),
    ("Payment method declined", "billing"),
    ("Login page wont load", "technical"),
    ("Is there a student discount?", "general"),
    ("Subscription charged after cancel", "billing"),
    ("Push notifications broken", "technical"),
    ("What languages do you support?", "general"),
]


def run_benchmark():
    results_a = []
    results_b = []
    log.info("benchmark_started", tests=len(TESTS))

    print(f"\n{'Query':<40} {'A':>5} {'B':>5}")
    print("-" * 55)

    for query, expected in TESTS:
        for label, prompt, result_list in [("A", PROMPT_A, results_a), ("B", PROMPT_B, results_b)]:
            try:
                r = client.chat.completions.create(model=MODEL, temperature=0, max_tokens=10,
                    messages=[{"role":"user","content":f"{prompt}\n\nQuery: {query}"}])
                answer = r.choices[0].message.content.strip().lower().rstrip(".")
                correct = expected in answer
                tokens = r.usage.total_tokens
                metric_calls.labels(variant=label).inc()
                if correct: metric_correct.labels(variant=label).inc()
                result_list.append({"query":query[:30],"correct":correct,"tokens":tokens})
            except:
                result_list.append({"query":query[:30],"correct":False,"tokens":0})

        a_mark = "Y" if results_a[-1]["correct"] else "N"
        b_mark = "Y" if results_b[-1]["correct"] else "N"
        print(f"  {query[:38]:<40} {a_mark:>5} {b_mark:>5}")

    acc_a = sum(1 for r in results_a if r["correct"]) / len(results_a) * 100
    acc_b = sum(1 for r in results_b if r["correct"]) / len(results_b) * 100
    metric_accuracy.labels(variant="A").set(acc_a)
    metric_accuracy.labels(variant="B").set(acc_b)

    results = [{"variant":"A","accuracy":acc_a,"tokens":sum(r["tokens"] for r in results_a)},
               {"variant":"B","accuracy":acc_b,"tokens":sum(r["tokens"] for r in results_b)}]

    log.info("benchmark_complete")
    return results


def show_analysis(results):
    print(f"\nRESULTS:")
    print("=" * 40)
    for r in results:
        print(f"  Prompt {r['variant']}: {r['accuracy']:.0f}% accuracy, {r['tokens']} tokens")
    winner = max(results, key=lambda x: x["accuracy"])
    print(f"\n  WINNER: Prompt {winner['variant']}")
    print(f"  Deploy it. Re-test monthly (model updates change results).")


def save_results(results):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{RESULTS_DIR}/ab_test_{ts}.csv"
    if results:
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=results[0].keys())
            w.writeheader(); w.writerows(results)
    log.info("saved", path=path); return path


def test_15_tests():
    assert len(TESTS) == 15

def test_prompts_different():
    assert PROMPT_A != PROMPT_B


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
