"""
AGENT LIVE REASONING TRACE
===========================

THE PROBLEM:
    Agents are black boxes. You send a task, get a result.
    But WHAT did it think? WHY did it pick that tool?
    This shows the full reasoning trace: think -> act -> observe.

WHAT YOU WILL LEARN:
    - ReAct pattern: think, act, observe, repeat
    - Full trace = debuggable agents
    - Max steps prevents infinite loops
"""

import time, csv, os, json
from datetime import datetime
from collections import defaultdict
import structlog
from prometheus_client import Counter, Histogram, Gauge, start_http_server

structlog.configure(
    processors=[structlog.processors.TimeStamper(fmt="iso"), structlog.dev.ConsoleRenderer()],
    wrapper_class=structlog.BoundLogger, context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)
log = structlog.get_logger()
METRICS_PORT = 8000
RESULTS_DIR = "./results"
from openai import OpenAI
client = OpenAI()
MODEL = "gpt-4o-mini"

metric_steps = Counter("agent_steps_total", "Steps taken")
metric_tools = Counter("agent_tools_used", "Tools used", ["tool"])

tools = [
    {"type":"function","function":{"name":"lookup_order","description":"Look up order by ID","parameters":{"type":"object","properties":{"order_id":{"type":"string"}},"required":["order_id"]}}},
    {"type":"function","function":{"name":"calculate","description":"Math expression","parameters":{"type":"object","properties":{"expression":{"type":"string"}},"required":["expression"]}}},
]

def execute_tool(name, args):
    if name == "lookup_order":
        return json.dumps({"order_id":args.get("order_id","?"),"status":"shipped","total":89.99})
    elif name == "calculate":
        try: return str(eval(args.get("expression","0")))
        except: return "Error"
    return "Unknown tool"

def run_benchmark():
    results = []
    log.info("benchmark_started")
    task = "Look up order ORD-123, calculate 15% tax on the total, tell me the final amount."
    messages = [
        {"role":"system","content":"You are a helpful agent. Use tools to answer."},
        {"role":"user","content":task}
    ]
    print(f"\nTASK: {task}")
    print("=" * 60)
    for step in range(5):
        try:
            r = client.chat.completions.create(model=MODEL, messages=messages, tools=tools, temperature=0)
            msg = r.choices[0].message
            metric_steps.inc()
        except Exception as e:
            log.error("failed", error=str(e)); break
        if msg.tool_calls:
            for tc in msg.tool_calls:
                args = json.loads(tc.function.arguments)
                print(f"\n  THINK: Need to call {tc.function.name}")
                print(f"  ACT:   {tc.function.name}({json.dumps(args)})")
                result = execute_tool(tc.function.name, args)
                print(f"  OBSERVE: {result}")
                metric_tools.labels(tool=tc.function.name).inc()
                messages.append(msg)
                messages.append({"role":"tool","tool_call_id":tc.id,"content":result})
        else:
            print(f"\n  ANSWER: {msg.content}")
            results.append({"task":task[:40],"steps":step+1,"answer":msg.content[:60]})
            break
    log.info("benchmark_complete")
    return results

def show_analysis(results):
    print("\nFull trace shows: what the agent thought, why it picked each tool.")
    print("This is how you debug agents in production.")


def save_results(results):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{RESULTS_DIR}/results_{ts}.csv"
    if results:
        keys = set()
        for r in results: keys.update(r.keys())
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=sorted(keys))
            w.writeheader(); w.writerows(results)
    log.info("saved", path=path); return path

def test_execute_lookup():
    r = execute_tool("lookup_order", {"order_id":"123"})
    assert "shipped" in r

def test_execute_calc():
    assert execute_tool("calculate", {"expression":"2+2"}) == "4"

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
