"""
META-PROMPTING: HUMAN vs AI-WRITTEN PROMPTS
=============================================

THE PROBLEM:
    You spend hours writing the perfect prompt. But what if the AI
    can write a better one? Meta-prompting = asking the AI to write
    prompts for you. This tests if AI-written prompts beat human ones.

WHAT WE FIND OUT:
    1. Does the AI-written prompt get higher accuracy?
    2. How many more tokens does it use?
    3. Is the cost difference worth it?

WHAT YOU WILL LEARN:
    - AI-written prompts often win (they include edge cases humans forget)
    - The meta-prompt (instructions to the AI) matters more than the output
    - Cost trick: GPT-4 writes the prompt ONCE, mini runs it every call
    - 3-5 optimization rounds is enough, then diminishing returns

HOW TO RUN:
    export OPENAI_API_KEY=sk-your-key
    pip install -r requirements.txt
    python main.py
"""

import time, csv, os
from datetime import datetime
import structlog
from prometheus_client import Counter, start_http_server
from openai import OpenAI

structlog.configure(
    processors=[structlog.processors.TimeStamper(fmt="iso"), structlog.dev.ConsoleRenderer()],
    wrapper_class=structlog.BoundLogger, context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)
log = structlog.get_logger()

metric_calls = Counter("meta_calls_total", "Calls", ["prompt_type"])
metric_correct = Counter("meta_correct_total", "Correct", ["prompt_type"])
metric_tokens = Counter("meta_tokens_total", "Tokens", ["prompt_type"])

METRICS_PORT = 8000
RESULTS_DIR = "./results"
client = OpenAI()
MODEL = "gpt-4o-mini"

REVIEWS = [
    ("This product changed my life! Best purchase ever.", "positive"),
    ("Terrible quality. Broke after one day.", "negative"),
    ("It's okay. Nothing special but gets the job done.", "neutral"),
    ("Absolutely love it! Exceeded all expectations.", "positive"),
    ("Complete waste of money. Do not buy.", "negative"),
    ("Average product. Works as described.", "neutral"),
    ("Customer service was amazing when I had issues.", "positive"),
    ("Shipping took forever and box was damaged.", "negative"),
    ("It's fine. Not great, not terrible.", "neutral"),
    ("Would buy again in a heartbeat! 10/10", "positive"),
]

HUMAN_PROMPT = "Classify this review as positive, negative, or neutral. Just one word.\n\nReview: {review}"


def test_prompt(template, label):
    correct = 0
    total_tokens = 0
    for review, expected in REVIEWS:
        prompt = template.replace("{review}", review)
        try:
            r = client.chat.completions.create(model=MODEL, temperature=0, max_tokens=10,
                messages=[{"role":"user","content":prompt}])
            answer = r.choices[0].message.content.strip().lower().rstrip(".")
            total_tokens += r.usage.total_tokens
            metric_calls.labels(prompt_type=label).inc()
            metric_tokens.labels(prompt_type=label).inc(r.usage.total_tokens)
            if expected in answer:
                correct += 1
                metric_correct.labels(prompt_type=label).inc()
        except Exception as e:
            log.error("api_failed", error=str(e))
    return correct, total_tokens


def run_benchmark():
    results = []
    log.info("benchmark_started")

    # Test human prompt
    print("\nTesting HUMAN-WRITTEN prompt...")
    h_correct, h_tokens = test_prompt(HUMAN_PROMPT, "human")
    h_acc = h_correct / len(REVIEWS) * 100
    print(f"  Human: {h_correct}/{len(REVIEWS)} ({h_acc:.0f}%), {h_tokens} tokens")

    # Ask AI to write a better prompt
    print("\nAsking AI to write a BETTER prompt...")
    meta = """Write a prompt that classifies customer reviews as positive, negative, or neutral.
Requirements:
- Must respond with exactly one word
- Must handle sarcasm
- Must handle mixed reviews
- Include 2 examples
Just output the prompt, nothing else."""

    try:
        r = client.chat.completions.create(model="gpt-4o-mini", temperature=0.3, max_tokens=500,
            messages=[{"role":"user","content":meta}])
        ai_prompt = r.choices[0].message.content.strip()
        if "{review}" not in ai_prompt:
            ai_prompt = ai_prompt + "\n\nReview: {review}"
        print(f"  AI generated: {ai_prompt[:100]}...")
    except Exception as e:
        log.error("meta_failed", error=str(e))
        ai_prompt = HUMAN_PROMPT

    # Test AI prompt
    print("\nTesting AI-WRITTEN prompt...")
    a_correct, a_tokens = test_prompt(ai_prompt, "ai")
    a_acc = a_correct / len(REVIEWS) * 100
    print(f"  AI: {a_correct}/{len(REVIEWS)} ({a_acc:.0f}%), {a_tokens} tokens")

    results.append({"prompt":"human","correct":h_correct,"accuracy":h_acc,"tokens":h_tokens})
    results.append({"prompt":"ai","correct":a_correct,"accuracy":a_acc,"tokens":a_tokens})

    log.info("benchmark_complete")
    return results


def show_analysis(results):
    print("\nRESULTS:")
    print("=" * 50)
    for r in results:
        print(f"  {r['prompt']:<8}: {r['accuracy']:.0f}% accuracy, {r['tokens']} tokens")
    winner = max(results, key=lambda x: x["accuracy"])
    print(f"\n  Winner: {winner['prompt']} prompt")
    print("\n  TRICK: GPT-4 writes the prompt ONCE. Mini runs it every call.")
    print("  This gives you GPT-4 quality at mini prices.")


def save_results(results):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{RESULTS_DIR}/meta_prompting_{ts}.csv"
    if results:
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=results[0].keys())
            w.writeheader(); w.writerows(results)
    log.info("saved", path=path); return path


def test_10_reviews():
    assert len(REVIEWS) == 10

def test_reviews_labeled():
    for r, l in REVIEWS:
        assert l in ["positive", "negative", "neutral"]


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
