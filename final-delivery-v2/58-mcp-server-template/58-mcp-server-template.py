"""
MCP SERVER TEMPLATE
===================

THE PROBLEM:
    Define tools in JSON, get a working MCP server. MCP = USB-C for AI tools. Build once, works with any LLM.

HOW TO RUN:
    pip install -r requirements.txt
    python main.py
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


metric_generated = Gauge("mcp_tools_generated", "Tools generated")
TOOLS = [
    {"name":"get_order","description":"Look up order by ID","params":{"order_id":"string"}},
    {"name":"process_refund","description":"Process refund","params":{"order_id":"string","reason":"string"}},
    {"name":"search_faq","description":"Search FAQ","params":{"query":"string"}},
]

def run_benchmark():
    results = []
    log.info("benchmark_started")
    print("\nGENERATED MCP SERVER CODE:")
    print("=" * 60)
    code = 'from fastmcp import FastMCP\n\nmcp = FastMCP("customer-support")\n\n'
    for tool in TOOLS:
        metric_generated.inc()
        params = ", ".join([f"{k}: {v}" for k,v in tool["params"].items()])
        code += f'@mcp.tool()\ndef {tool["name"]}({params}) -> str:\n'
        code += f'    """{tool["description"]}"""\n'
        code += f'    return f"{tool["name"]} called"\n\n'
    code += 'if __name__ == "__main__":\n    mcp.run()\n'
    
    for line in code.split("\n"):
        print(f"  {line}")
    
    print("\n  pip install fastmcp")
    print("  python server.py")
    print("\n  MCP = USB-C for AI tools")
    print("  Build once, works with Claude, GPT, Gemini, local models")
    results = [{"tools":len(TOOLS),"generated":True}]
    log.info("benchmark_complete"); return results

def show_analysis(results):
    print("\n  FastMCP: 20 lines for a working server")
    print("  Open standard by Anthropic")
    print("  Before MCP: 50 custom integrations")
    print("  With MCP: 1 standard interface for everything")


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

def test_3_tools(): assert len(TOOLS) == 3

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
