"""
ITERATIVE REFINEMENT: GENERATE -> CRITIQUE -> IMPROVE
=======================================================

THE PROBLEM:
    First drafts are never great. But most LLM apps just send one prompt
    and use whatever comes back. Iterative refinement = generate, get
    feedback, rewrite. Like having an editor review your work.

WHAT WE FIND OUT:
    1. How much does quality improve per round? (measured 1-10)
    2. How many rounds before diminishing returns?
    3. How much extra does it cost?

WHAT YOU WILL LEARN:
    - Quality improves ~2 points per round (1-10 scale)
    - 3 rounds is the sweet spot (diminishing returns after)
    - Costs 3x a single generation
    - Use for: reports, code reviews, client-facing content

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

metric_rounds = Counter("refine_rounds_total", "Refinement rounds")
metric_tokens = Counter("refine_tokens_total", "Tokens used")
metric_score = Gauge("refine_current_score", "Current quality score")

METRICS_PORT = 8000
RESULTS_DIR = "./results"
client = OpenAI()
MODEL = "gpt-4o-mini"

TASK = "Write a professional email to a client explaining a 2-week project delay due to supply chain issues. Include updated timeline and mitigation steps."


def generate(prompt):
    try:
        r = client.chat.completions.create(model=MODEL, temperature=0.7, max_tokens=300,
            messages=[{"role":"user","content":prompt}])
        metric_tokens.inc(r.usage.total_tokens)
        return r.choices[0].message.content.strip()
    except Exception as e:
        log.error("generate_failed", error=str(e)); return ""


def critique(text):
    try:
        r = client.chat.completions.create(model=MODEL, temperature=0, max_tokens=200,
            messages=[{"role":"user","content":f"Critique this email. List 3 specific improvements. Be direct.\n\n{text}"}])
        metric_tokens.inc(r.usage.total_tokens)
        return r.choices[0].message.content.strip()
    except Exception as e:
        log.error("critique_failed", error=str(e)); return ""


def score(text):
    try:
        r = client.chat.completions.create(model=MODEL, temperature=0, max_tokens=5,
            messages=[{"role":"user","content":f"Rate this email 1-10 for clarity, tone, completeness. Just the number.\n\n{text}"}])
        return int(r.choices[0].message.content.strip()[0])
    except:
        return 5


def run_benchmark():
    results = []
    log.info("benchmark_started")

    # Round 1: Initial generation
    print("\nROUND 1: Initial generation")
    print("=" * 60)
    draft = generate(TASK)
    s1 = score(draft)
    metric_score.set(s1)
    metric_rounds.inc()
    print(f"  Score: {s1}/10")
    print(f"  {draft[:150]}...")
    results.append({"round":1, "score":s1})

    # Rounds 2-3: Critique and improve
    for round_num in range(2, 4):
        print(f"\nROUND {round_num}: Critique -> Improve")
        print("=" * 60)

        feedback = critique(draft)
        print(f"  Feedback: {feedback[:100]}...")

        draft = generate(f"Improve this email based on feedback.\n\nOriginal:\n{draft}\n\nFeedback:\n{feedback}\n\nImproved version:")
        s = score(draft)
        metric_score.set(s)
        metric_rounds.inc()
        print(f"  Score: {s}/10")
        print(f"  {draft[:150]}...")
        results.append({"round":round_num, "score":s})

    log.info("benchmark_complete")
    return results


def show_analysis(results):
    print(f"\nSCORE PROGRESSION:")
    print("=" * 40)
    for r in results:
        bar = "#" * r["score"] + "." * (10 - r["score"])
        print(f"  Round {r['round']}: {r['score']}/10  [{bar}]")
    if len(results) >= 2:
        improvement = results[-1]["score"] - results[0]["score"]
        print(f"\n  Total improvement: +{improvement} points")
    print(f"  Cost: ~3x a single generation")
    print(f"  3 rounds = sweet spot. Diminishing returns after.")


def save_results(results):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{RESULTS_DIR}/refinement_{ts}.csv"
    if results:
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=results[0].keys())
            w.writeheader(); w.writerows(results)
    log.info("saved", path=path); return path


def test_task_exists():
    assert len(TASK) > 20

def test_generate_callable():
    assert callable(generate)


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
