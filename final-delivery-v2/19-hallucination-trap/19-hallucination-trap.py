"""
HALLUCINATION TRAP
===================

THE PROBLEM:
    You give the AI some documents and ask a question.
    If the answer is NOT in the documents, a good system says "I don't know."
    A bad system MAKES UP an answer that sounds correct but is completely wrong.
    
    This is called hallucination. It is the most dangerous failure mode
    because the user trusts a confident wrong answer.

WHAT WE FIND OUT:
    1. How often does the AI hallucinate without grounding instructions?
    2. How much does a simple grounding prompt reduce hallucinations?
    3. What percentage of unanswerable questions get hallucinated answers?

WHAT YOU WILL LEARN:
    - Without grounding: 50-80% hallucination rate on unanswerable questions
    - With grounding instruction: drops to 5-15%
    - One line in the prompt ("answer from context only") fixes most hallucinations
    - Always include unanswerable questions in your test suite

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

metric_questions = Counter("hallucination_questions_total", "Questions asked", ["type", "grounded"])
metric_hallucinated = Counter("hallucination_count", "Hallucinated answers", ["grounded"])
metric_abstained = Counter("hallucination_abstained", "Correctly said I dont know", ["grounded"])
metric_rate = Gauge("hallucination_rate_pct", "Hallucination rate", ["grounded"])

METRICS_PORT = 8000
RESULTS_DIR = "./results"
client = OpenAI()
MODEL = "gpt-4o-mini"

CONTEXT = """TechCorp Product Catalog (2024)

Product A: CloudSync Pro — $49/month. File sync across devices.
Supports Windows, Mac, Linux. 100GB storage. API access available.

Product B: SecureVault — $29/month. Password manager with encrypted storage.
Browser extension for Chrome and Firefox. Supports 2FA. Team sharing.

Product C: DataPipe — $99/month. ETL pipeline tool.
Connects to 50+ data sources. Visual pipeline builder. Scheduled runs."""

QUESTIONS = [
    # ANSWERABLE — answer IS in the context
    ("What does CloudSync Pro cost?", True, "$49"),
    ("Which browsers does SecureVault support?", True, "Chrome and Firefox"),
    ("How many data sources does DataPipe connect to?", True, "50"),
    
    # UNANSWERABLE — answer is NOT in the context (should say "I don't know")
    ("Does TechCorp offer a mobile app?", False, None),
    ("What is the uptime SLA for CloudSync Pro?", False, None),
    ("Can I pay annually for a discount?", False, None),
    ("Is there a free trial available?", False, None),
    ("What happens if I exceed 100GB storage?", False, None),
    ("Does SecureVault support Safari?", False, None),
    ("Who is the CEO of TechCorp?", False, None),
    ("What is the cancellation policy?", False, None),
]

ABSTAIN_PHRASES = ["don't know", "not mentioned", "not specified", "no information",
                   "not stated", "not explicitly", "don't have", "cannot find",
                   "not available", "not provided"]


def ask_with_context(question, grounded=False):
    if grounded:
        system = "Answer ONLY from the provided context. If the answer is NOT in the context, say: I don't have that information."
    else:
        system = "You are a helpful assistant. Answer questions about TechCorp."
    
    try:
        r = client.chat.completions.create(model=MODEL, temperature=0, max_tokens=100,
            messages=[{"role":"system","content":system},
                     {"role":"user","content":f"Context:\n{CONTEXT}\n\nQuestion: {question}"}])
        return r.choices[0].message.content.strip()
    except Exception as e:
        log.error("api_failed", error=str(e))
        return None


def check_hallucination(answer, answerable):
    """For UNANSWERABLE questions: did the AI make something up?"""
    if answerable:
        return False  # answerable questions can't hallucinate
    # Check if the AI correctly abstained
    abstained = any(phrase in answer.lower() for phrase in ABSTAIN_PHRASES)
    return not abstained  # hallucinated = did NOT abstain


def run_benchmark():
    results = []
    log.info("benchmark_started")
    
    for grounded in [False, True]:
        label = "grounded" if grounded else "ungrounded"
        print(f"\nPHASE: {'WITH' if grounded else 'WITHOUT'} grounding instruction")
        print("=" * 65)
        
        hallucination_count = 0
        unanswerable_count = 0
        
        for question, answerable, expected in QUESTIONS:
            answer = ask_with_context(question, grounded=grounded)
            if answer is None: continue
            
            q_type = "answerable" if answerable else "unanswerable"
            metric_questions.labels(type=q_type, grounded=label).inc()
            
            if not answerable:
                unanswerable_count += 1
                hallucinated = check_hallucination(answer, answerable)
                if hallucinated:
                    hallucination_count += 1
                    metric_hallucinated.labels(grounded=label).inc()
                    print(f"  HALLUCINATED: {question[:45]}")
                    print(f"    -> {answer[:60]}...")
                else:
                    metric_abstained.labels(grounded=label).inc()
                    print(f"  CORRECT:      {question[:45]}")
                    print(f"    -> {answer[:60]}...")
            else:
                correct = expected.lower() in answer.lower() if expected else True
                mark = "CORRECT" if correct else "WRONG"
                print(f"  {mark}:      {question[:45]} -> {answer[:40]}")
        
        rate = hallucination_count / unanswerable_count * 100 if unanswerable_count else 0
        metric_rate.labels(grounded=label).set(rate)
        print(f"\n  Hallucination rate: {hallucination_count}/{unanswerable_count} ({rate:.0f}%)")
        
        results.append({"phase":label, "hallucinated":hallucination_count,
                        "unanswerable":unanswerable_count, "rate":round(rate,1)})
    
    log.info("benchmark_complete")
    return results


def show_analysis(results):
    print("\nRESULTS:")
    print("=" * 50)
    for r in results:
        print(f"  {r['phase']:<12}: {r['rate']:.0f}% hallucination rate")
    if len(results) == 2:
        improvement = results[0]["rate"] - results[1]["rate"]
        print(f"\n  Grounding reduced hallucination by {improvement:.0f}%")
    print("\n  ONE LINE fixes most hallucinations:")
    print('  "Answer ONLY from the provided context."')
    print("\n  ALWAYS include unanswerable questions in your test suite.")


def save_results(results):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{RESULTS_DIR}/hallucination_{ts}.csv"
    if results:
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=results[0].keys())
            w.writeheader(); w.writerows(results)
    log.info("saved", path=path); return path


def test_has_answerable():
    assert any(a for _, a, _ in QUESTIONS)

def test_has_unanswerable():
    assert any(not a for _, a, _ in QUESTIONS)

def test_12_questions():
    assert len(QUESTIONS) == 12


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
