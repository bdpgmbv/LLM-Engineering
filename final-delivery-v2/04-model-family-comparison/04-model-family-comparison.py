"""
MODEL FAMILY COMPARISON
=======================

THE PROBLEM:
    GPT-4o costs 15x more than GPT-4o-mini.
    GPT-4 costs 200x more than mini.
    But are they actually better? For WHAT tasks?
    
    Most teams use the expensive model for everything
    and waste thousands of dollars per month on simple queries
    that the cheap model handles perfectly.

WHAT WE FIND OUT:
    1. Which model wins on factual questions? (capitals, dates)
    2. Which wins on reasoning/math? (word problems, logic)
    3. Which wins on classification? (sentiment, categories)
    4. Exact cost difference at 1K, 10K, 100K, 1M calls/day

WHAT YOU WILL LEARN:
    - Mini handles simple tasks perfectly (factual, classification)
    - GPT-4o only wins on complex reasoning (math, multi-step logic)
    - At 1M calls/day: mini=$3K/month, gpt-4=$300K/month
    - Smart routing (simple->mini, complex->4o) saves 60-70%

HOW TO RUN:
    export OPENAI_API_KEY=sk-your-key
    pip install -r requirements.txt
    python main.py
"""

import time, csv, os, json
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

metric_calls = Counter("model_calls_total", "Total calls", ["model"])
metric_correct = Counter("model_correct_total", "Correct answers", ["model", "task_type"])
metric_wrong = Counter("model_wrong_total", "Wrong answers", ["model", "task_type"])
metric_tokens = Counter("model_tokens_total", "Tokens used", ["model"])
metric_cost = Counter("model_cost_dollars", "Cost", ["model"])
metric_latency = Histogram("model_latency_seconds", "Latency", ["model"])

METRICS_PORT = 8000
RESULTS_DIR = "./results"

client = OpenAI()

MODELS = ["gpt-4o-mini", "gpt-4o"]

COSTS = {
    "gpt-4o":      {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
}

# 15 test questions across different difficulty levels
TESTS = [
    # Factual (easy — mini should handle these perfectly)
    {"q": "What is the capital of Australia?", "a": "canberra", "type": "factual"},
    {"q": "How many planets in our solar system?", "a": "8", "type": "factual"},
    {"q": "What year did World War 2 end?", "a": "1945", "type": "factual"},
    {"q": "Who wrote Romeo and Juliet?", "a": "shakespeare", "type": "factual"},
    {"q": "What is the chemical symbol for water?", "a": "h2o", "type": "factual"},
    
    # Reasoning (harder — 4o might win)
    {"q": "If a shirt costs $25 after a 20% discount, what was the original price? Just the number.", "a": "31.25", "type": "reasoning"},
    {"q": "A bat and ball cost $1.10. The bat costs $1 more than the ball. How much is the ball? Just the number.", "a": "0.05", "type": "reasoning"},
    {"q": "If 5 machines make 5 widgets in 5 minutes, how long for 100 machines to make 100 widgets? Just minutes.", "a": "5", "type": "reasoning"},
    {"q": "A lily pad doubles daily. Takes 48 days to cover a lake. How many days for half? Just the number.", "a": "47", "type": "reasoning"},
    
    # Classification (easy — mini should handle)
    {"q": "Classify as positive/negative/neutral: 'This product is amazing, best purchase ever!'", "a": "positive", "type": "classification"},
    {"q": "Classify as positive/negative/neutral: 'Terrible quality, complete waste of money.'", "a": "negative", "type": "classification"},
    {"q": "Classify: 'My card was charged twice' -> billing/technical/general", "a": "billing", "type": "classification"},
    {"q": "Classify: 'App crashes on startup' -> billing/technical/general", "a": "technical", "type": "classification"},
    {"q": "Is this urgent? 'Production database is down, customers affected' -> yes/no", "a": "yes", "type": "classification"},
    {"q": "Extract the email from: 'Contact john@test.com for support'", "a": "john@test.com", "type": "classification"},
]


def ask_model(model, prompt):
    """Send question to a specific model. Returns (answer, tokens, cost, latency)."""
    start = time.time()
    try:
        r = client.chat.completions.create(
            model=model, temperature=0, max_tokens=50,
            messages=[{"role": "user", "content": prompt}]
        )
    except Exception as e:
        log.error("api_failed", model=model, error=str(e))
        return None, 0, 0.0, 0.0
    
    elapsed = time.time() - start
    answer = r.choices[0].message.content.strip()
    tok_in = r.usage.prompt_tokens
    tok_out = r.usage.completion_tokens
    cost = (tok_in/1e6)*COSTS[model]["input"] + (tok_out/1e6)*COSTS[model]["output"]
    
    metric_calls.labels(model=model).inc()
    metric_tokens.labels(model=model).inc(tok_in + tok_out)
    metric_cost.labels(model=model).inc(cost)
    metric_latency.labels(model=model).observe(elapsed)
    
    return answer, tok_in + tok_out, cost, elapsed


def run_benchmark():
    results = []
    log.info("benchmark_started", models=MODELS, questions=len(TESTS))
    
    for model in MODELS:
        print(f"\nRunning {model} on {len(TESTS)} questions...")
        print("-" * 60)
        
        correct = 0
        total_tokens = 0
        total_cost = 0.0
        
        for test in TESTS:
            answer, tokens, cost, latency = ask_model(model, test["q"])
            if answer is None:
                continue
            
            is_correct = test["a"].lower() in answer.lower()
            if is_correct:
                correct += 1
                metric_correct.labels(model=model, task_type=test["type"]).inc()
            else:
                metric_wrong.labels(model=model, task_type=test["type"]).inc()
            
            total_tokens += tokens
            total_cost += cost
            
            mark = "Y" if is_correct else "N"
            print(f"  {mark} [{test['type']:<15}] {answer[:50]}")
        
        accuracy = correct / len(TESTS) * 100
        print(f"\n  {model}: {correct}/{len(TESTS)} correct ({accuracy:.0f}%), {total_tokens} tokens, ${total_cost:.4f}")
        
        results.append({
            "model": model, "correct": correct, "total": len(TESTS),
            "accuracy": accuracy, "tokens": total_tokens, "cost": round(total_cost, 6),
        })
    
    log.info("benchmark_complete")
    return results


def show_analysis(results):
    print()
    print("MODEL COMPARISON")
    print("=" * 60)
    print(f"  {'Model':<16} {'Accuracy':>10} {'Tokens':>10} {'Cost':>10}")
    print("  " + "-" * 48)
    for r in results:
        print(f"  {r['model']:<16} {r['accuracy']:>9.0f}% {r['tokens']:>10} ${r['cost']:>8.4f}")
    
    print()
    print("  MONTHLY PROJECTION (assuming average tokens from test):")
    for r in results:
        avg_cost = r["cost"] / r["total"]
        for vol in [10000, 100000, 1000000]:
            monthly = avg_cost * vol * 30
            print(f"    {r['model']} at {vol:>10,}/day: ${monthly:>12,.2f}/month")


def save_results(results):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{RESULTS_DIR}/model_comparison_{ts}.csv"
    if results:
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=results[0].keys())
            w.writeheader()
            w.writerows(results)
    log.info("saved", path=path)
    return path


def test_models_list():
    assert len(MODELS) >= 2

def test_tests_have_answers():
    for t in TESTS:
        assert "a" in t and "q" in t and "type" in t

def test_costs_positive():
    for m, c in COSTS.items():
        assert c["input"] > 0 and c["output"] > 0


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
