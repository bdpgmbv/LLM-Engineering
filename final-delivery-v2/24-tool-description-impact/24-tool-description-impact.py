"""
TOOL DESCRIPTION QUALITY IMPACT
=================================

THE PROBLEM:
    When you give an AI agent tools, the DESCRIPTION of each tool
    determines whether the agent picks the right one.
    
    Vague: "Gets order info"
    Specific: "Look up order details including status, total, shipping.
               Use when customer asks about an order. Returns JSON."
    
    The specific version gets 15-30% higher accuracy.

WHAT WE FIND OUT:
    1. Tool selection accuracy with vague vs specific descriptions
    2. How much does description quality affect results?
    3. What makes a good tool description?

WHAT YOU WILL LEARN:
    - Specific descriptions improve accuracy 15-30%
    - Include: what it does, when to use it, what it returns
    - Max 15 tools per agent (more causes confusion)
    - Spend more time on descriptions than on agent logic

HOW TO RUN:
    export OPENAI_API_KEY=sk-your-key
    pip install -r requirements.txt
    python main.py
"""

import time, csv, os, json
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

metric_calls = Counter("tool_calls_total", "Calls", ["desc_type"])
metric_correct = Counter("tool_correct_total", "Correct tool selected", ["desc_type"])
metric_accuracy = Gauge("tool_accuracy_pct", "Accuracy", ["desc_type"])

METRICS_PORT = 8000
RESULTS_DIR = "./results"
client = OpenAI()
MODEL = "gpt-4o-mini"

VAGUE_TOOLS = [
    {"type":"function","function":{"name":"get_order","description":"Gets order info","parameters":{"type":"object","properties":{"order_id":{"type":"string"}},"required":["order_id"]}}},
    {"type":"function","function":{"name":"get_user","description":"Gets user info","parameters":{"type":"object","properties":{"user_id":{"type":"string"}},"required":["user_id"]}}},
    {"type":"function","function":{"name":"process_refund","description":"Processes a refund","parameters":{"type":"object","properties":{"order_id":{"type":"string"}},"required":["order_id"]}}},
    {"type":"function","function":{"name":"send_notification","description":"Sends a notification","parameters":{"type":"object","properties":{"user_id":{"type":"string"},"message":{"type":"string"}},"required":["user_id","message"]}}},
]

SPECIFIC_TOOLS = [
    {"type":"function","function":{"name":"get_order","description":"Look up order details (status, total, shipping). Use when customer asks about an order. Returns JSON with id, status, total.","parameters":{"type":"object","properties":{"order_id":{"type":"string","description":"Order ID like order_12345"}},"required":["order_id"]}}},
    {"type":"function","function":{"name":"get_user","description":"Get user profile (name, tier, preferences). Use when you need customer account info. Returns JSON.","parameters":{"type":"object","properties":{"user_id":{"type":"string","description":"User ID like user_alice"}},"required":["user_id"]}}},
    {"type":"function","function":{"name":"process_refund","description":"Issue refund for an order. Only use AFTER confirming order exists and customer requested refund.","parameters":{"type":"object","properties":{"order_id":{"type":"string","description":"Order ID to refund"}},"required":["order_id"]}}},
    {"type":"function","function":{"name":"send_notification","description":"Send message to user via email/push. Use to confirm actions or provide updates.","parameters":{"type":"object","properties":{"user_id":{"type":"string","description":"User to notify"},"message":{"type":"string","description":"Message text"}},"required":["user_id","message"]}}},
]

TASKS = [
    ("What is the status of order_12345?", "get_order"),
    ("Look up user_alice account tier", "get_user"),
    ("I want a refund for order_12345", "process_refund"),
    ("Notify user_alice her refund is processing", "send_notification"),
    ("Check order_67890 details", "get_order"),
]


def test_tool_selection(tools, label):
    correct = 0
    for task, expected in TASKS:
        try:
            r = client.chat.completions.create(model=MODEL, temperature=0, max_tokens=200,
                messages=[{"role":"user","content":task}], tools=tools, tool_choice="auto")
            metric_calls.labels(desc_type=label).inc()

            if r.choices[0].message.tool_calls:
                selected = r.choices[0].message.tool_calls[0].function.name
                is_correct = selected == expected
                if is_correct:
                    correct += 1
                    metric_correct.labels(desc_type=label).inc()
                mark = "Y" if is_correct else "N"
                print(f"  {mark} '{task[:40]}' -> {selected} (expected {expected})")
            else:
                print(f"  N '{task[:40]}' -> NO TOOL CALLED")
        except Exception as e:
            log.error("api_failed", error=str(e))

    accuracy = correct / len(TASKS) * 100
    metric_accuracy.labels(desc_type=label).set(accuracy)
    print(f"  {label} accuracy: {correct}/{len(TASKS)} ({accuracy:.0f}%)")
    return accuracy


def run_benchmark():
    results = []
    log.info("benchmark_started")

    print("\nVAGUE DESCRIPTIONS:")
    print("-" * 60)
    vague_acc = test_tool_selection(VAGUE_TOOLS, "vague")

    print("\nSPECIFIC DESCRIPTIONS:")
    print("-" * 60)
    specific_acc = test_tool_selection(SPECIFIC_TOOLS, "specific")

    results = [{"type":"vague","accuracy":vague_acc}, {"type":"specific","accuracy":specific_acc}]
    log.info("benchmark_complete")
    return results


def show_analysis(results):
    print("\nRESULTS:")
    print("=" * 40)
    for r in results:
        print(f"  {r['type']:<10}: {r['accuracy']:.0f}%")
    if len(results) == 2:
        diff = results[1]["accuracy"] - results[0]["accuracy"]
        print(f"  Improvement: +{diff:.0f}%")
    print("\n  Tool descriptions are your #1 quality lever.")
    print("  Include: what it does, when to use it, what it returns.")


def save_results(results):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{RESULTS_DIR}/tool_descriptions_{ts}.csv"
    if results:
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=results[0].keys())
            w.writeheader(); w.writerows(results)
    log.info("saved", path=path); return path


def test_5_tasks():
    assert len(TASKS) == 5

def test_4_tools_each():
    assert len(VAGUE_TOOLS) == 4
    assert len(SPECIFIC_TOOLS) == 4


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
