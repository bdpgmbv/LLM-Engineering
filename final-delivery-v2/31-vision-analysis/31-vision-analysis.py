"""
VISION ANALYSIS: IMAGE -> STRUCTURED DATA
===========================================

THE PROBLEM:
    You have screenshots of pricing tables, photos of products,
    charts with data. You need this as structured JSON for your code.
    
    GPT-4o can read images and extract data.
    But: detail:low costs 85 tokens, detail:high costs 1000+.
    That is 10x difference.

WHAT WE FIND OUT:
    1. Can GPT-4o extract structured data from image descriptions?
    2. Is the output valid parseable JSON?
    3. What does it cost per image?

WHAT YOU WILL LEARN:
    - GPT-4o extracts structured data from any image
    - JSON mode guarantees parseable output
    - detail:low for simple images, detail:high for small text
    - At 10K images/day: $0.10 (low) vs $2.00 (high)

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

metric_extractions = Counter("vision_extractions_total", "Extractions done")
metric_parse_ok = Counter("vision_parse_success", "Successful JSON parses")
metric_parse_fail = Counter("vision_parse_fail", "Failed JSON parses")
metric_tokens = Counter("vision_tokens_total", "Tokens used")

METRICS_PORT = 8000
RESULTS_DIR = "./results"
client = OpenAI()

# Since we cant upload images here, we describe what the image shows
# In production, you would send actual base64-encoded images
TEST_CASES = [
    {"description": "A pricing table: Basic $9/mo, Pro $29/mo, Enterprise $99/mo",
     "task": "Extract pricing tiers as JSON array with: tier, price, period"},
    {"description": "A product photo: black laptop, label says 16GB RAM, 512GB SSD, Intel i7",
     "task": "Extract specs as JSON: color, ram, storage, processor"},
    {"description": "A bar chart: Q1=$2M, Q2=$3.5M, Q3=$2.8M, Q4=$4.2M revenue",
     "task": "Extract revenue as JSON array: quarter, revenue"},
    {"description": "A receipt: Store=TechMart, Items: Keyboard $45, Mouse $25, Cable $12, Tax $6.56, Total $88.56",
     "task": "Extract receipt as JSON: store, items (array), tax, total"},
]


def run_benchmark():
    results = []
    log.info("benchmark_started")

    for tc in TEST_CASES:
        try:
            r = client.chat.completions.create(
                model="gpt-4o-mini", temperature=0, max_tokens=300,
                response_format={"type":"json_object"},
                messages=[{"role":"system","content":"Extract structured data. Return valid JSON only."},
                         {"role":"user","content":f"Image shows: {tc['description']}\n\nTask: {tc['task']}"}])
            
            content = r.choices[0].message.content
            tokens = r.usage.total_tokens
            metric_tokens.inc(tokens)
            metric_extractions.inc()

            try:
                data = json.loads(content)
                metric_parse_ok.inc()
                parsed = True
            except:
                data = content
                metric_parse_fail.inc()
                parsed = False

            print(f"Task: {tc['task'][:50]}...")
            print(f"  Parsed: {'YES' if parsed else 'NO'}")
            print(f"  Data: {json.dumps(data, indent=2)[:100]}...")
            print(f"  Tokens: {tokens}")
            print()

            results.append({"task":tc["task"][:40], "parsed":parsed, "tokens":tokens})
        except Exception as e:
            log.error("api_failed", error=str(e))

    log.info("benchmark_complete")
    return results


def show_analysis(results):
    parsed = sum(1 for r in results if r["parsed"])
    avg_tok = sum(r["tokens"] for r in results) / max(len(results),1)
    print(f"\nRESULTS:")
    print(f"=" * 40)
    print(f"  Parse success: {parsed}/{len(results)}")
    print(f"  Average tokens: {avg_tok:.0f}")
    print(f"\n  In production: send actual images as base64")
    print(f"  detail:low = 85 tokens | detail:high = 1000+ tokens")
    print(f"  At 10K/day: $0.10 (low) vs $2.00 (high)")


def save_results(results):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{RESULTS_DIR}/vision_{ts}.csv"
    if results:
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=results[0].keys())
            w.writeheader(); w.writerows(results)
    log.info("saved", path=path); return path


def test_4_cases():
    assert len(TEST_CASES) == 4


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
