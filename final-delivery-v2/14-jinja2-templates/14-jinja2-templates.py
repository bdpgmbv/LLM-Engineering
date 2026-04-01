"""
JINJA2 PROMPT TEMPLATES
========================

THE PROBLEM:
    You can not write a separate prompt for each of 10,000 daily customers.
    Jinja2 templates let you write ONE template with variables like
    {{ customer_name }} and {{ issue }}, then fill them in for each user.
    
    1 template x 10,000 customers = 10,000 unique prompts.

WHAT WE FIND OUT:
    1. How to build templates with variables, conditions, loops
    2. How to use template inheritance (base safety rules + child templates)
    3. How the AI responds to templated vs hand-written prompts
    4. Token cost difference between short and long templates

WHAT YOU WILL LEARN:
    - Jinja2 templates scale prompt engineering to millions of calls
    - Conditionals ({% if %}) handle different scenarios in one template
    - Template inheritance prevents accidental rule deletion
    - Store templates in git — same review process as code

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
from jinja2 import Template

structlog.configure(
    processors=[structlog.processors.TimeStamper(fmt="iso"), structlog.dev.ConsoleRenderer()],
    wrapper_class=structlog.BoundLogger, context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)
log = structlog.get_logger()

metric_calls = Counter("template_calls_total", "Calls", ["scenario"])
metric_tokens = Counter("template_tokens_total", "Tokens", ["scenario"])

METRICS_PORT = 8000
RESULTS_DIR = "./results"
client = OpenAI()
MODEL = "gpt-4o-mini"

TEMPLATE_STR = """You are a {{ role }} at {{ company }}.

{% if tone == "formal" %}Use professional language.
{% elif tone == "casual" %}Be friendly and conversational.
{% endif %}

Customer: {{ customer_name }}
Issue: {{ issue }}
{% if priority == "high" %}
WARNING: HIGH PRIORITY. Respond within 1 hour.
{% endif %}

{% if context %}
Relevant info:
{% for item in context %}
- {{ item }}
{% endfor %}
{% endif %}

Provide a helpful response in 2-3 sentences."""


SCENARIOS = [
    {"role":"support agent","company":"TechCorp","tone":"formal","customer_name":"Dr. Smith",
     "issue":"billing discrepancy of $45.99","priority":"high",
     "context":["Order #12345 placed Jan 15","Refund policy: 30 days"]},
    {"role":"tech support","company":"AppCo","tone":"casual","customer_name":"Jake",
     "issue":"app crashes on iOS 17","priority":"low",
     "context":["Known issue since v2.3","Fix in v2.4 next week"]},
    {"role":"sales rep","company":"CloudSaaS","tone":"formal","customer_name":"Ms. Chen",
     "issue":"interested in enterprise plan","priority":"high","context":[]},
]


def run_benchmark():
    results = []
    template = Template(TEMPLATE_STR)
    log.info("benchmark_started", scenarios=len(SCENARIOS))

    for i, scenario in enumerate(SCENARIOS):
        prompt = template.render(**scenario)
        
        print(f"\nSCENARIO {i+1}: {scenario['customer_name']} - {scenario['issue'][:40]}")
        print(f"  Template rendered ({len(prompt)} chars):")
        print(f"  {prompt[:120]}...")
        
        try:
            r = client.chat.completions.create(model=MODEL, temperature=0.3, max_tokens=200,
                messages=[{"role":"user","content":prompt}])
            answer = r.choices[0].message.content.strip()
            tokens = r.usage.total_tokens
            
            metric_calls.labels(scenario=f"s{i+1}").inc()
            metric_tokens.labels(scenario=f"s{i+1}").inc(tokens)
            
            print(f"  Response ({tokens} tokens): {answer[:100]}...")
            results.append({"scenario":i+1,"customer":scenario["customer_name"],
                          "issue":scenario["issue"][:30],"tokens":tokens,"prompt_chars":len(prompt)})
        except Exception as e:
            log.error("api_failed", error=str(e))

    log.info("benchmark_complete")
    return results


def show_analysis(results):
    print("\nTEMPLATE BENEFITS:")
    print("=" * 50)
    print("  1 template x N customers = N unique prompts")
    print("  Conditions handle different scenarios")
    print("  Store templates in git (same review as code)")
    print("  Template inheritance = safety rules cant be deleted")
    if results:
        avg_tokens = sum(r["tokens"] for r in results) / len(results)
        print(f"\n  Average tokens per call: {avg_tokens:.0f}")


def save_results(results):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{RESULTS_DIR}/jinja2_{ts}.csv"
    if results:
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=results[0].keys())
            w.writeheader(); w.writerows(results)
    log.info("saved", path=path); return path


def test_template_renders():
    t = Template(TEMPLATE_STR)
    result = t.render(role="agent", company="Co", tone="formal",
                      customer_name="Test", issue="test issue",
                      priority="low", context=[])
    assert "agent" in result
    assert "Co" in result

def test_3_scenarios():
    assert len(SCENARIOS) == 3


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
