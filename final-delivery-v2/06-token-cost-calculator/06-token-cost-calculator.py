"""
TOKEN COST CALCULATOR
=====================

THE PROBLEM:
    Before deploying an LLM app, your boss asks: "How much will this cost?"
    You need to count tokens for your typical prompts and multiply by the price.
    
    But different models charge different rates, and different tokenizers
    produce different token counts. This tool does the math for you.

WHAT WE FIND OUT:
    1. Exact token count for any text you paste in
    2. Cost per call for every major model
    3. Monthly cost at 1K, 10K, 100K, 1M calls/day
    4. Which model gives the best value

WHAT YOU WILL LEARN:
    - System prompts add up fast (200 tokens x 1M calls = 200M extra tokens/day)
    - RAG context is the biggest token cost (5 chunks x 200 tokens = 1000 tokens)
    - gpt-4o-mini is nearly impossible to beat below 500K calls/day
    - Output tokens cost 2-4x more than input tokens

HOW TO RUN:
    pip install -r requirements.txt
    python main.py
    No API key needed. Runs locally.
"""

import time, csv, os
from datetime import datetime
import tiktoken
import structlog
from prometheus_client import Counter, Gauge, start_http_server

structlog.configure(
    processors=[structlog.processors.TimeStamper(fmt="iso"), structlog.dev.ConsoleRenderer()],
    wrapper_class=structlog.BoundLogger, context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)
log = structlog.get_logger()

metric_texts = Counter("cost_texts_analyzed", "Texts analyzed")
metric_total_tokens = Counter("cost_tokens_total", "Total tokens counted")

METRICS_PORT = 8000
RESULTS_DIR = "./results"

enc_o200k = tiktoken.get_encoding("o200k_base")
enc_cl100k = tiktoken.get_encoding("cl100k_base")

MODELS = {
    "gpt-4o":        {"input": 2.50,  "output": 10.00, "enc": "o200k"},
    "gpt-4o-mini":   {"input": 0.15,  "output": 0.60,  "enc": "o200k"},
    "gpt-3.5-turbo": {"input": 0.50,  "output": 1.50,  "enc": "cl100k"},
    "gpt-4":         {"input": 30.00, "output": 60.00, "enc": "cl100k"},
    "claude-sonnet": {"input": 3.00,  "output": 15.00, "enc": "cl100k"},
    "claude-haiku":  {"input": 0.25,  "output": 1.25,  "enc": "cl100k"},
}


def count_tokens(text, encoding="o200k"):
    enc = enc_o200k if encoding == "o200k" else enc_cl100k
    return len(enc.encode(text))


def calculate_cost(input_tokens, output_tokens, model):
    p = MODELS[model]
    return (input_tokens/1e6)*p["input"] + (output_tokens/1e6)*p["output"]


SCENARIOS = {
    "Simple query": "What is your refund policy?",
    "Support ticket": "I ordered a laptop (order #12345) on Jan 15 and it hasnt arrived. Tracking stuck for 5 days. Can you help me track it and send a replacement?",
    "System prompt": "You are a helpful customer support agent for TechCorp. Be professional and empathetic. Never share internal pricing. " * 3,
    "RAG context": "Based on the following context, answer the question.\n\n" + "Company policy documentation section. " * 50 + "\n\nQuestion: What is the refund timeline?",
    "Code review": "def process_order(order_id, user_id):\n    order = db.get(order_id)\n    if not order: raise NotFoundError\n    if order.user_id != user_id: raise AuthError\n    order.status = 'processing'\n    db.save(order)\n    notify(user_id, 'Order processing')\n    return order",
}


def run_benchmark():
    results = []
    log.info("benchmark_started")
    
    avg_output = 150
    
    for scenario_name, text in SCENARIOS.items():
        tokens = count_tokens(text, "o200k")
        metric_texts.inc()
        metric_total_tokens.inc(tokens)
        
        print(f"\n{scenario_name}")
        print(f"  Text: {text[:60]}...")
        print(f"  Characters: {len(text)} | Tokens: {tokens}")
        print()
        print(f"  {'Model':<16} {'Per call':>10} {'1K/day':>10} {'100K/day':>11} {'1M/day':>12}")
        print(f"  {'-'*62}")
        
        for model, pricing in MODELS.items():
            enc = pricing["enc"]
            tok = count_tokens(text, enc)
            cost = calculate_cost(tok, avg_output, model)
            
            print(f"  {model:<16} ${cost:.6f}", end="")
            for vol in [1000, 100000, 1000000]:
                monthly = cost * vol * 30
                print(f" ${monthly:>9,.2f}", end="")
            print()
        
        results.append({"scenario": scenario_name, "chars": len(text), "tokens": tokens})
    
    log.info("benchmark_complete")
    return results


def show_analysis(results):
    print()
    print("KEY INSIGHTS:")
    print("=" * 50)
    print("  1. System prompts add up: 200 tokens x 1M calls = $30/day on mini")
    print("  2. RAG context is your biggest cost driver")
    print("  3. Output tokens cost 2-4x more than input")
    print("  4. gpt-4o-mini is hard to beat below 500K calls/day")
    print()
    print("  YOUR COST FORMULA:")
    print("  Monthly = (input_tok x input_price + output_tok x output_price) x calls/day x 30")


def save_results(results):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{RESULTS_DIR}/cost_calc_{ts}.csv"
    if results:
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=results[0].keys())
            w.writeheader()
            w.writerows(results)
    log.info("saved", path=path)
    return path


def test_count_tokens_positive():
    assert count_tokens("Hello world") > 0

def test_empty_zero():
    assert count_tokens("") == 0

def test_cost_positive():
    assert calculate_cost(100, 150, "gpt-4o-mini") > 0

def test_mini_cheaper():
    assert calculate_cost(100, 100, "gpt-4o-mini") < calculate_cost(100, 100, "gpt-4o")


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
