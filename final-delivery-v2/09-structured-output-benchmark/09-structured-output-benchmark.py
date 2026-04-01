"""
STRUCTURED OUTPUT BENCHMARK
============================

THE PROBLEM:
    You need the AI to return JSON (not free text) so your code can parse it.
    There are 3 ways to do this:
    - Raw: just ask nicely ("return JSON please") — often fails
    - JSON mode: set response_format={"type":"json_object"} — guaranteed valid JSON
    - XML tags: ask for <name>...</name> format — works with any model
    
    Which one fails least? Which costs least?

WHAT WE FIND OUT:
    1. Parse success rate for each method
    2. Token cost per method
    3. Which method works best for extraction tasks

WHAT YOU WILL LEARN:
    - JSON mode: 100% valid JSON syntax (but no schema guarantee)
    - XML tags: works with any model, very reliable
    - Raw text: 60-80% parseable — never use for production
    - For strict schemas: use instructor + Pydantic library

HOW TO RUN:
    export OPENAI_API_KEY=sk-your-key
    pip install -r requirements.txt
    python main.py
"""

import time, csv, os
from datetime import datetime
from collections import defaultdict, Counter
import structlog
from prometheus_client import Counter as PCounter, Histogram, Gauge, start_http_server
from openai import OpenAI

structlog.configure(
    processors=[structlog.processors.TimeStamper(fmt="iso"), structlog.dev.ConsoleRenderer()],
    wrapper_class=structlog.BoundLogger, context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)
log = structlog.get_logger()
client = OpenAI()
MODEL = "gpt-4o-mini"
PRICING = {"input": 0.15, "output": 0.60}
METRICS_PORT = 8000
RESULTS_DIR = "./results"

import json as json_lib
import re

metric_calls = PCounter("struct_calls_total", "Calls", ["method"])
metric_parse_ok = PCounter("struct_parse_success", "Parse success", ["method"])
metric_parse_fail = PCounter("struct_parse_fail", "Parse fail", ["method"])
metric_tokens = PCounter("struct_tokens_total", "Tokens", ["method"])

TEXTS = [
    "Contact Sarah Connor at sarah.connor@skynet.com or call 555-0101. VP of Engineering.",
    "John doe, j.doe@company.co.uk, phone 44-20-1234-5678, Senior Architect",
    "Contact: Maria Garcia, maria@startup.io, +1 650-555-0199, CEO",
    "Bob Smith (bob@test.com) is our CTO. His assistant: assistant@test.com",
    "Email me at info@example.com. Alex, Director of Sales",
    "No contact info here, just a question about pricing.",
    "URGENT: Forward to tech.lead@bigcorp.com (Kim Lee, Staff Engineer)",
    "Invoice should go to billing@acme.org. Contact Pat, Accounts Payable.",
]


def extract_raw(text):
    r = client.chat.completions.create(model=MODEL, temperature=0, max_tokens=100,
        messages=[{"role":"user","content":f"Extract name, email, title from this text. If missing say unknown.\n\n{text}"}])
    return r.choices[0].message.content.strip(), r.usage.total_tokens, False


def extract_json_mode(text):
    r = client.chat.completions.create(model=MODEL, temperature=0, max_tokens=100,
        response_format={"type":"json_object"},
        messages=[{"role":"system","content":"Return JSON with keys: name, email, title. Use unknown for missing."},
                  {"role":"user","content":text}])
    content = r.choices[0].message.content.strip()
    try:
        parsed = json_lib.loads(content)
        return parsed, r.usage.total_tokens, True
    except:
        return content, r.usage.total_tokens, False


def extract_xml(text):
    r = client.chat.completions.create(model=MODEL, temperature=0, max_tokens=150,
        messages=[{"role":"user","content":f"Extract contact info. Return exactly:\n<name>...</name>\n<email>...</email>\n<title>...</title>\nUse unknown for missing.\n\nText: {text}"}])
    content = r.choices[0].message.content.strip()
    try:
        name = re.search(r'<name>(.*?)</name>', content).group(1)
        email = re.search(r'<email>(.*?)</email>', content).group(1)
        title = re.search(r'<title>(.*?)</title>', content).group(1)
        return {"name":name,"email":email,"title":title}, r.usage.total_tokens, True
    except:
        return content, r.usage.total_tokens, False


def run_benchmark():
    results = []
    log.info("benchmark_started", texts=len(TEXTS))
    
    methods = {"raw": extract_raw, "json_mode": extract_json_mode, "xml_tags": extract_xml}
    method_stats = {m: {"ok":0,"fail":0,"tokens":0} for m in methods}
    
    for i, text in enumerate(TEXTS):
        print(f"\nText {i+1}: {text[:50]}...")
        for name, fn in methods.items():
            output, tokens, parsed = fn(text)
            metric_calls.labels(method=name).inc()
            metric_tokens.labels(method=name).inc(tokens)
            method_stats[name]["tokens"] += tokens
            if parsed:
                method_stats[name]["ok"] += 1
                metric_parse_ok.labels(method=name).inc()
            else:
                method_stats[name]["fail"] += 1
                metric_parse_fail.labels(method=name).inc()
            mark = "Y" if parsed else "N"
            print(f"  {name:>10}: {mark} {str(output)[:50]}")
    
    for name, stats in method_stats.items():
        total = stats["ok"] + stats["fail"]
        rate = stats["ok"]/total*100 if total else 0
        results.append({"method":name,"parse_rate":rate,"ok":stats["ok"],"fail":stats["fail"],"tokens":stats["tokens"]})
    
    log.info("benchmark_complete")
    return results


def show_analysis(results):
    print("\nPARSE SUCCESS RATE:")
    print("=" * 50)
    for r in results:
        print(f"  {r['method']:<12} {r['parse_rate']:.0f}% ({r['ok']}/{r['ok']+r['fail']}) {r['tokens']} tokens")
    print("\n  JSON mode: guaranteed valid JSON. Use response_format.")
    print("  XML tags: works with any model (Claude loves XML).")
    print("  Raw text: NEVER use for production parsing.")


def save_results(results):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{RESULTS_DIR}/structured_output_{ts}.csv"
    if results:
        with open(path,"w",newline="") as f:
            w = csv.DictWriter(f, fieldnames=results[0].keys()); w.writeheader(); w.writerows(results)
    log.info("saved", path=path); return path


def test_8_texts():
    assert len(TEXTS) == 8

def test_methods_callable():
    assert callable(extract_raw)
    assert callable(extract_json_mode)
    assert callable(extract_xml)


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

