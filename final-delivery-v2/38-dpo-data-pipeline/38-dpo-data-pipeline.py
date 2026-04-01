"""
DPO PREFERENCE DATA PIPELINE
==============================

THE PROBLEM:
    DPO (Direct Preference Optimization) needs training data in the format:
    [prompt, chosen_response, rejected_response]
    
    Getting humans to pick winners: $0.40 per pair = $2,000 for 5,000 pairs.
    Using GPT-4 to judge (RLAIF): $0.002 per pair = $10 for 5,000 pairs.

WHAT WE FIND OUT:
    1. Can we generate chosen/rejected pairs automatically?
    2. Does the LLM judge pick reasonable winners?
    3. Cost per pair

WHAT YOU WILL LEARN:
    - DPO needs [prompt, chosen, rejected] triples
    - RLAIF: GPT-4 judges instead of humans (80% quality at 10% cost)
    - 5K-10K pairs for effective DPO training
    - Pipeline: SFT first, then DPO

HOW TO RUN:
    export OPENAI_API_KEY=sk-your-key
    pip install -r requirements.txt
    python main.py
"""

import time, csv, os, json
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

metric_pairs = Counter("dpo_pairs_total", "Pairs generated")
metric_tokens = Counter("dpo_tokens_total", "Tokens used")

METRICS_PORT = 8000
RESULTS_DIR = "./results"
client = OpenAI()

PROMPTS = [
    "Explain quantum computing to a 10-year-old",
    "Write a professional email declining a meeting",
    "How should I invest $10,000?",
    "Best way to learn programming?",
    "Explain why the sky is blue",
]


def run_benchmark():
    results = []
    log.info("benchmark_started")

    print("\nGenerating preference pairs...")
    print("=" * 60)

    for prompt in PROMPTS:
        # Generate 2 responses with different temperatures
        try:
            r1 = client.chat.completions.create(model="gpt-4o-mini", temperature=0.3, max_tokens=150,
                messages=[{"role":"user","content":prompt}])
            r2 = client.chat.completions.create(model="gpt-4o-mini", temperature=1.0, max_tokens=150,
                messages=[{"role":"user","content":prompt}])

            resp_a = r1.choices[0].message.content.strip()
            resp_b = r2.choices[0].message.content.strip()

            # Judge picks winner
            judge = client.chat.completions.create(model="gpt-4o-mini", temperature=0, max_tokens=50,
                messages=[{"role":"user","content":f"Which is better? Reply A or B with one-sentence reason.\n\nPrompt: {prompt}\n\nA: {resp_a[:200]}\n\nB: {resp_b[:200]}"}])

            judgment = judge.choices[0].message.content.strip()
            a_wins = judgment.upper().startswith("A")
            chosen = resp_a if a_wins else resp_b
            rejected = resp_b if a_wins else resp_a

            metric_pairs.inc()
            total_tok = r1.usage.total_tokens + r2.usage.total_tokens + judge.usage.total_tokens
            metric_tokens.inc(total_tok)

            print(f"\n  Prompt: {prompt[:40]}...")
            print(f"  Winner: {'A' if a_wins else 'B'} — {judgment[:50]}...")
            results.append({"prompt":prompt[:30],"winner":"A" if a_wins else "B","tokens":total_tok})
        except Exception as e:
            log.error("failed", error=str(e))

    log.info("benchmark_complete")
    return results


def show_analysis(results):
    total_tok = sum(r["tokens"] for r in results)
    cost = total_tok / 1e6 * 0.15
    print(f"\nRESULTS:")
    print(f"=" * 40)
    print(f"  Pairs generated: {len(results)}")
    print(f"  Total tokens: {total_tok}")
    print(f"  Total cost: ${cost:.4f}")
    print(f"  Cost per pair: ${cost/max(len(results),1):.4f}")
    print(f"\n  Scale: 5K pairs at ~${cost/max(len(results),1)*5000:.2f}")
    print(f"  Manual: 5K pairs at ~$2,000")


def save_results(results):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{RESULTS_DIR}/dpo_{ts}.csv"
    if results:
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=results[0].keys())
            w.writeheader(); w.writerows(results)
    log.info("saved", path=path); return path


def test_5_prompts():
    assert len(PROMPTS) == 5


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
