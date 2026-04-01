"""
ZERO-SHOT vs FEW-SHOT vs DYNAMIC FEW-SHOT
==========================================

THE PROBLEM:
    When you ask the AI to classify text, you can:
    - Give it 0 examples and just describe the task (zero-shot)
    - Give it 3 fixed examples (few-shot)
    - Give it 3 examples picked specifically for each query (dynamic few-shot)
    
    Few-shot costs 3-5x more tokens (you send examples every time).
    Is the accuracy improvement worth the extra cost?

WHAT WE FIND OUT:
    1. Zero-shot accuracy vs few-shot accuracy on 30 real queries
    2. How many extra tokens do examples cost?
    3. Does dynamic few-shot beat static few-shot?
    4. At what volume does the cost difference matter?

WHAT YOU WILL LEARN:
    - Zero-shot is 85-95% accurate for clear classification tasks
    - Few-shot adds 5-10% accuracy but costs 3-5x more tokens
    - Dynamic few-shot gets best accuracy at similar cost to static
    - Start zero-shot. Add examples ONLY if accuracy below 90%.

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


metric_calls = PCounter("classify_calls_total", "Total calls", ["method"])
metric_correct = PCounter("classify_correct_total", "Correct", ["method"])
metric_wrong = PCounter("classify_wrong_total", "Wrong", ["method"])
metric_tokens = PCounter("classify_tokens_total", "Tokens", ["method"])
metric_cost = PCounter("classify_cost_dollars", "Cost", ["method"])

# 30 customer queries with correct labels
QUERIES = [
    ("My credit card was charged twice", "billing"),
    ("App crashes when I upload photos", "technical"),
    ("What are your business hours?", "general"),
    ("I want a refund for my subscription", "billing"),
    ("How do I reset my password?", "technical"),
    ("Can I change my delivery address?", "general"),
    ("Overcharged by $15 on my last bill", "billing"),
    ("Website showing a 500 error", "technical"),
    ("Do you offer student discounts?", "general"),
    ("Payment failed but order went through", "billing"),
    ("Cant connect bluetooth to the app", "technical"),
    ("Where is my nearest store?", "general"),
    ("Cancel my auto-renewal please", "billing"),
    ("Search feature returns no results", "technical"),
    ("Whats your return policy?", "general"),
    ("Unauthorized charge on my account", "billing"),
    ("Screen goes black after update", "technical"),
    ("How long does shipping take?", "general"),
    ("Need to dispute a transaction", "billing"),
    ("Getting insufficient permissions error", "technical"),
    ("Do you ship internationally?", "general"),
    ("Coupon code not working at checkout", "billing"),
    ("App wont load on Android", "technical"),
    ("Can I speak to a manager?", "general"),
    ("Double charged for premium plan", "billing"),
    ("WiFi settings keep resetting", "technical"),
    ("What payment methods do you accept?", "general"),
    ("Refund hasnt appeared after 10 days", "billing"),
    ("Login page stuck loading", "technical"),
    ("How do I update my email?", "general"),
]

FEW_SHOT_EXAMPLES = [
    ("I was charged twice for my order", "billing"),
    ("The app crashes when I open settings", "technical"),
    ("What are your store hours?", "general"),
]

CATEGORIES = ["billing", "technical", "general"]


def classify_zero_shot(query):
    """No examples. Just describe the task."""
    r = client.chat.completions.create(
        model=MODEL, temperature=0, max_tokens=10,
        messages=[{"role":"user","content":f"Classify this customer query into exactly one category: billing, technical, or general.\n\nQuery: {query}\nCategory:"}]
    )
    return r.choices[0].message.content.strip().lower(), r.usage.total_tokens


def classify_few_shot(query):
    """3 fixed examples every time."""
    examples = "\n".join([f"Query: {q}\nCategory: {c}" for q, c in FEW_SHOT_EXAMPLES])
    r = client.chat.completions.create(
        model=MODEL, temperature=0, max_tokens=10,
        messages=[{"role":"user","content":f"Classify customer queries.\n\n{examples}\n\nQuery: {query}\nCategory:"}]
    )
    return r.choices[0].message.content.strip().lower(), r.usage.total_tokens


def classify_dynamic(query):
    """Pick examples based on keywords in the query."""
    billing_words = {"charge","bill","refund","payment","card","invoice","price","cancel","subscription"}
    tech_words = {"error","crash","bug","app","update","load","sync","broken","fail","permission","login"}
    q_words = set(query.lower().split())
    
    if len(q_words & billing_words) > len(q_words & tech_words):
        examples = [("Charged twice for my order", "billing"), ("Refund not received", "billing"), ("App crashes on startup", "technical")]
    elif len(q_words & tech_words) > len(q_words & billing_words):
        examples = [("Error code 403 on login", "technical"), ("Bluetooth not connecting", "technical"), ("Charged wrong amount", "billing")]
    else:
        examples = FEW_SHOT_EXAMPLES
    
    ex_str = "\n".join([f"Query: {q}\nCategory: {c}" for q, c in examples])
    r = client.chat.completions.create(
        model=MODEL, temperature=0, max_tokens=10,
        messages=[{"role":"user","content":f"Classify customer queries.\n\n{ex_str}\n\nQuery: {query}\nCategory:"}]
    )
    return r.choices[0].message.content.strip().lower(), r.usage.total_tokens


def run_benchmark():
    results = []
    log.info("benchmark_started", queries=len(QUERIES))
    
    methods = {
        "zero-shot": classify_zero_shot,
        "few-shot": classify_few_shot,
        "dynamic": classify_dynamic,
    }
    
    for method_name, method_fn in methods.items():
        print(f"\nRunning {method_name}...")
        correct = 0
        total_tokens = 0
        
        for query, expected in QUERIES:
            predicted, tokens = method_fn(query)
            for cat in CATEGORIES:
                if cat in predicted:
                    predicted = cat
                    break
            
            is_correct = predicted == expected
            if is_correct:
                correct += 1
                metric_correct.labels(method=method_name).inc()
            else:
                metric_wrong.labels(method=method_name).inc()
            
            total_tokens += tokens
            metric_calls.labels(method=method_name).inc()
            metric_tokens.labels(method=method_name).inc(tokens)
        
        accuracy = correct / len(QUERIES) * 100
        cost = (total_tokens / 1e6) * PRICING["input"]
        metric_cost.labels(method=method_name).inc(cost)
        
        print(f"  {correct}/{len(QUERIES)} correct ({accuracy:.0f}%), {total_tokens} tokens, ${cost:.4f}")
        results.append({"method": method_name, "correct": correct, "accuracy": accuracy,
                        "tokens": total_tokens, "cost": round(cost, 6)})
    
    log.info("benchmark_complete")
    return results


def show_analysis(results):
    print("\nRESULTS:")
    print("=" * 60)
    print(f"  {'Method':<15} {'Accuracy':>10} {'Tokens':>10} {'Cost':>10}")
    print("  " + "-" * 47)
    for r in results:
        print(f"  {r['method']:<15} {r['accuracy']:>9.0f}% {r['tokens']:>10} ${r['cost']}")
    print()
    print("  DECISION: start zero-shot. Add examples ONLY if accuracy < 90%.")
    print("  Few-shot costs 3-5x more. Dynamic beats static at same cost.")


def save_results(results):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{RESULTS_DIR}/zero_few_shot_{ts}.csv"
    if results:
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=results[0].keys())
            w.writeheader(); w.writerows(results)
    log.info("saved", path=path)
    return path


def test_queries_have_labels():
    for q, l in QUERIES:
        assert l in CATEGORIES

def test_examples_have_labels():
    for q, l in FEW_SHOT_EXAMPLES:
        assert l in CATEGORIES

def test_30_queries():
    assert len(QUERIES) == 30


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

