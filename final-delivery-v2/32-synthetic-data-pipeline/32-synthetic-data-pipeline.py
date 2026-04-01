"""
SYNTHETIC DATA PIPELINE
=========================

THE PROBLEM:
    Fine-tuning needs thousands of training examples.
    Hiring humans to write them: $2 per example = $2,000 for 1,000.
    Using AI to generate them: ~$0.01 per example = $10 for 1,000.
    
    But AI-generated data can be garbage. So you:
    1. Write 5 high-quality seed examples by hand
    2. Ask GPT to generate more like them
    3. Use LLM-as-judge to score each one
    4. Keep only the good ones (score >= 7)

WHAT WE FIND OUT:
    1. How many generated examples pass quality filter?
    2. What does the score distribution look like?
    3. Are categories balanced?

WHAT YOU WILL LEARN:
    - 5 seeds -> 20+ quality examples in one API call
    - LLM-as-judge filters out garbage (keep score >= 7)
    - Cost: $5-10 for 1,000 examples
    - Always check category balance

HOW TO RUN:
    export OPENAI_API_KEY=sk-your-key
    pip install -r requirements.txt
    python main.py
"""

import time, csv, os, json
from datetime import datetime
from collections import Counter
import structlog
from prometheus_client import Counter as PCounter, Gauge, start_http_server
from openai import OpenAI

structlog.configure(
    processors=[structlog.processors.TimeStamper(fmt="iso"), structlog.dev.ConsoleRenderer()],
    wrapper_class=structlog.BoundLogger, context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)
log = structlog.get_logger()

metric_generated = PCounter("synth_generated_total", "Examples generated")
metric_kept = PCounter("synth_kept_total", "Examples kept after filtering")
metric_rejected = PCounter("synth_rejected_total", "Examples rejected")
metric_pass_rate = Gauge("synth_pass_rate_pct", "Pass rate")

METRICS_PORT = 8000
RESULTS_DIR = "./results"
client = OpenAI()
MODEL = "gpt-4o-mini"

SEEDS = [
    {"input":"My payment was declined twice","output":"billing"},
    {"input":"App crashes when uploading photos","output":"technical"},
    {"input":"What are your store hours?","output":"general"},
    {"input":"Overcharged on my last invoice","output":"billing"},
    {"input":"Cant connect to the API endpoint","output":"technical"},
]


def run_benchmark():
    results = []
    log.info("benchmark_started")

    # Step 1: Generate 15 new examples
    print("\nStep 1: Generating examples from seeds...")
    seed_text = json.dumps(SEEDS, indent=2)
    try:
        r = client.chat.completions.create(
            model=MODEL, temperature=0.8, max_tokens=2000,
            response_format={"type":"json_object"},
            messages=[{"role":"user","content":f"Examples:\n{seed_text}\n\nGenerate 15 MORE diverse examples in same format. Include edge cases. Return JSON with key 'examples'."}])
        generated = json.loads(r.choices[0].message.content).get("examples", [])
        gen_cost = r.usage.total_tokens / 1e6 * 0.15
        print(f"  Generated: {len(generated)} examples (${gen_cost:.4f})")
        for g in generated[:3]:
            print(f"    [{g.get('output','?'):>10}] {g.get('input','')[:50]}")
        if len(generated) > 3:
            print(f"    ... and {len(generated)-3} more")
    except Exception as e:
        log.error("generation_failed", error=str(e))
        generated = []

    # Step 2: Score quality
    print("\nStep 2: Scoring quality (1-10)...")
    scored = []
    for ex in generated:
        metric_generated.inc()
        try:
            sr = client.chat.completions.create(model=MODEL, temperature=0, max_tokens=10,
                messages=[{"role":"user","content":f"Rate 1-10 for quality (clear, realistic, correct label).\nInput: {ex.get('input','')}\nLabel: {ex.get('output','')}\nScore (just number):"}])
            score = int(sr.choices[0].message.content.strip()[0])
        except:
            score = 5
        scored.append({**ex, "quality_score": score})

    # Step 3: Filter
    high = [s for s in scored if s["quality_score"] >= 7]
    low = [s for s in scored if s["quality_score"] < 7]
    pass_rate = len(high) / max(len(scored), 1) * 100

    for _ in high: metric_kept.inc()
    for _ in low: metric_rejected.inc()
    metric_pass_rate.set(pass_rate)

    print(f"\nStep 3: Filtering...")
    print(f"  Total: {len(scored)}")
    print(f"  Kept (score >= 7): {len(high)}")
    print(f"  Rejected: {len(low)}")
    print(f"  Pass rate: {pass_rate:.0f}%")

    # Score distribution
    dist = Counter(s["quality_score"] for s in scored)
    print(f"\n  Score distribution:")
    for score in sorted(dist.keys()):
        bar = "#" * dist[score]
        print(f"    {score}: {bar} ({dist[score]})")

    # Category balance
    cats = Counter(s.get("output","?") for s in high)
    print(f"\n  Category balance (kept):")
    for cat, count in cats.most_common():
        print(f"    {cat}: {count}")

    results = [{"stage":"generated","count":len(generated)},
               {"stage":"kept","count":len(high)},
               {"stage":"rejected","count":len(low)},
               {"stage":"pass_rate","count":pass_rate}]

    log.info("benchmark_complete")
    return results


def show_analysis(results):
    print(f"\nSUMMARY:")
    print(f"=" * 40)
    print(f"  5 seeds -> {results[0]['count'] if results else 0} generated -> {results[1]['count'] if len(results)>1 else 0} quality examples")
    print(f"  Cost: ~$0.01 total")
    print(f"  Manual equivalent: ~${(results[1]['count'] if len(results)>1 else 0)*2} (at $2/example)")
    print(f"\n  Scale to 5K-10K pairs for real fine-tuning")


def save_results(results):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{RESULTS_DIR}/synthetic_data_{ts}.csv"
    if results:
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=results[0].keys())
            w.writeheader(); w.writerows(results)
    log.info("saved", path=path); return path


def test_5_seeds():
    assert len(SEEDS) == 5

def test_seeds_labeled():
    for s in SEEDS:
        assert "input" in s and "output" in s


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
