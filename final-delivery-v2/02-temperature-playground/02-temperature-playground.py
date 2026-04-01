"""
TEMPERATURE PLAYGROUND
======================

THE PROBLEM:
    Temperature controls how random the AI answers are.
    temp=0: same answer every time (robotic).
    temp=1.5: creative but sometimes says nonsense.
    
    Set it wrong and your chatbot either sounds like a robot
    or tells customers their refund is a magical unicorn.

WHAT WE WANT TO FIND OUT:
    1. Does temp=0 really give the exact same answer every time?
    2. At what temperature does the AI start saying weird things?
    3. What is the best setting for customer support vs creative writing?
    4. What does top_p actually do?

WHY THIS MATTERS:
    Your team is deploying a customer support bot.
    You need the exact right temperature setting.
    Too low = robotic. Too high = crazy. This finds the sweet spot.

WHAT THE CODE DOES:
    1. Send same question at 5 temperatures (0, 0.3, 0.7, 1.0, 1.5)
    2. Each temperature tested 3 times to see variation
    3. Test top_p at 4 levels (0.1, 0.5, 0.9, 1.0)
    4. Test if temp=0 is truly deterministic (5 identical calls)
    5. Measure tokens, cost, uniqueness per setting

WHAT YOU WILL LEARN:
    - temp=0: use for classification, extraction, factual Q&A
    - temp=0.3-0.7: production sweet spot
    - temp=0.7-1.0: creative writing
    - temp above 1.2: NEVER use in production
    - top_p=0.9 + temp=0.7: the default creative setting

HOW TO RUN:
    export OPENAI_API_KEY=sk-your-key-here
    pip install -r requirements.txt
    python main.py
    
    Full stack: docker-compose up --build
    Tests: pytest main.py -v
"""

import time, csv, os
from datetime import datetime
from collections import defaultdict
import structlog
from prometheus_client import Counter, Histogram, Gauge, start_http_server, generate_latest
from openai import OpenAI

structlog.configure(
    processors=[structlog.processors.TimeStamper(fmt="iso"), structlog.dev.ConsoleRenderer()],
    wrapper_class=structlog.BoundLogger, context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)
log = structlog.get_logger()

# ── Prometheus metrics ──
metric_calls = Counter("llm_calls_total", "Total API calls", ["temperature"])
metric_tokens = Counter("llm_tokens_total", "Tokens used", ["direction"])
metric_cost = Counter("llm_cost_dollars", "Cost in USD")
metric_latency = Histogram("llm_latency_seconds", "Call latency")
metric_unique = Gauge("llm_unique_responses", "Unique responses in last batch")

METRICS_PORT = 8000
RESULTS_DIR = "./results"

# ── OpenAI setup ──
client = OpenAI()  # reads OPENAI_API_KEY from environment
MODEL = "gpt-4o-mini"
PRICING = {"input": 0.15, "output": 0.60}  # per 1M tokens


def ask(prompt, temperature=1.0, top_p=1.0):
    """Send a question to the AI. Returns (answer, total_tokens, cost)."""
    start = time.time()
    try:
        r = client.chat.completions.create(
            model=MODEL, messages=[{"role": "user", "content": prompt}],
            temperature=temperature, top_p=top_p, max_tokens=100,
        )
    except Exception as e:
        log.error("api_failed", error=str(e))
        return None, 0, 0.0

    elapsed = time.time() - start
    answer = r.choices[0].message.content.strip()
    tok_in = r.usage.prompt_tokens
    tok_out = r.usage.completion_tokens
    cost = (tok_in / 1e6) * PRICING["input"] + (tok_out / 1e6) * PRICING["output"]

    metric_calls.labels(temperature=str(temperature)).inc()
    metric_tokens.labels(direction="input").inc(tok_in)
    metric_tokens.labels(direction="output").inc(tok_out)
    metric_cost.inc(cost)
    metric_latency.observe(elapsed)

    return answer, tok_in + tok_out, cost


def run_benchmark():
    """Run all temperature experiments."""
    results = []
    log.info("benchmark_started")

    # Experiment 1: Temperature sweep
    prompt = "Give me a one-sentence startup idea for a mobile app."
    print("\nEXPERIMENT 1: Temperature Sweep")
    print("Same prompt, different temperatures, 3 attempts each")
    print("=" * 70)

    for temp in [0, 0.3, 0.7, 1.0, 1.5]:
        answers = []
        for _ in range(3):
            a, tok, cost = ask(prompt, temperature=temp)
            if a:
                answers.append(a)
        unique = len(set(answers))
        metric_unique.set(unique)
        print(f"\n  temp={temp}  ({unique}/3 unique)")
        for i, a in enumerate(answers):
            print(f"    [{i+1}] {a[:80]}...")
        results.append({"experiment": "temp_sweep", "temperature": temp, "unique": unique})

    # Experiment 2: Top-p sweep
    print("\nEXPERIMENT 2: Top-p Sweep (temp fixed at 0.8)")
    print("=" * 70)
    for tp in [0.1, 0.5, 0.9, 1.0]:
        a, tok, cost = ask("Complete: The robot walked into the bar and", temperature=0.8, top_p=tp)
        if a:
            print(f"  top_p={tp}: {a[:80]}...")
        results.append({"experiment": "top_p", "top_p": tp})

    # Experiment 3: Determinism
    print("\nEXPERIMENT 3: Is temp=0 truly deterministic? (5 calls)")
    print("=" * 70)
    det = []
    for i in range(5):
        a, _, _ = ask("What is 2+2? Just the number.", temperature=0)
        if a:
            det.append(a)
            print(f"  Run {i+1}: {a}")
    print(f"  All identical? {len(set(det)) == 1}")

    log.info("benchmark_complete", results=len(results))
    return results


def show_analysis(results):
    """Print what we learned."""
    print("\nPRODUCTION TEMPERATURE GUIDE:")
    print("  temp=0     -> classification, extraction, factual")
    print("  temp=0.3   -> customer support (safe, slight variation)")
    print("  temp=0.7   -> general purpose (good balance)")
    print("  temp=1.0   -> creative writing, brainstorming")
    print("  temp>1.2   -> NEVER in production")


def save_results(results):
    """Save to CSV."""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{RESULTS_DIR}/temperature_{ts}.csv"
    if results:
        keys = set()
        for r in results:
            keys.update(r.keys())
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=sorted(keys))
            w.writeheader()
            w.writerows(results)
    log.info("saved", path=path)
    return path


# ── Tests ──

def test_ask_callable():
    assert callable(ask)

def test_pricing_positive():
    assert PRICING["input"] > 0
    assert PRICING["output"] > 0

def test_model_set():
    assert MODEL == "gpt-4o-mini"


# ── Run ──

if __name__ == "__main__":
    try:
        start_http_server(METRICS_PORT)
        log.info("metrics_started", url=f"http://localhost:{METRICS_PORT}/metrics")
    except OSError:
        log.warning("port_in_use", port=METRICS_PORT)

    results = run_benchmark()
    show_analysis(results)
    csv_path = save_results(results)

    print(f"\nDONE! CSV: {csv_path} | Metrics: http://localhost:{METRICS_PORT}/metrics")
    print("Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("shutdown")
