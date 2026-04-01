"""
RAG EVAL DASHBOARD (RAGAS)
===========================

THE PROBLEM:
    You built a RAG system. But how do you know if it is actually working?
    "It seems fine" is not good enough for production.
    
    You need 4 specific metrics:
    - Precision: did we find the RIGHT documents?
    - Recall: did we find ALL relevant documents?
    - Faithfulness: is the answer actually from the documents? (not made up)
    - Relevance: does the answer address the actual question?

WHAT WE FIND OUT:
    1. Score for each metric on 5 test questions
    2. Which metrics pass the quality threshold
    3. What to fix when each metric is low

WHAT YOU WILL LEARN:
    - Faithfulness below 90% = STOP, system is lying
    - Low precision = fix chunking or reranking
    - Low recall = add hybrid search or multi-query
    - Run on 200+ samples in production

HOW TO RUN:
    export OPENAI_API_KEY=sk-your-key
    pip install -r requirements.txt
    python main.py
"""

import time, csv, os
from datetime import datetime
import structlog
from prometheus_client import Gauge, Counter, start_http_server
from openai import OpenAI

structlog.configure(
    processors=[structlog.processors.TimeStamper(fmt="iso"), structlog.dev.ConsoleRenderer()],
    wrapper_class=structlog.BoundLogger, context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)
log = structlog.get_logger()

metric_precision = Gauge("rag_precision_pct", "Retrieval precision")
metric_recall = Gauge("rag_recall_pct", "Retrieval recall")
metric_faithfulness = Gauge("rag_faithfulness_pct", "Answer faithfulness")
metric_relevance = Gauge("rag_relevance_pct", "Answer relevance")
metric_overall = Gauge("rag_overall_pass", "Overall pass (1) or fail (0)")

METRICS_PORT = 8000
RESULTS_DIR = "./results"
client = OpenAI()
MODEL = "gpt-4o-mini"

KB = [
    "CloudSync Pro costs $49/month and includes 100GB storage with API access.",
    "SecureVault is a password manager at $29/month with Chrome and Firefox extensions.",
    "DataPipe ETL tool costs $99/month and connects to 50+ data sources.",
    "All products offer a 14-day free trial. No credit card required.",
    "Enterprise plans start at $499/month with custom SLAs.",
]

EVAL_SET = [
    {"q":"How much does CloudSync Pro cost?", "expected":"$49", "relevant":[0]},
    {"q":"Does SecureVault work with Safari?", "expected":"not mentioned", "relevant":[1]},
    {"q":"What is the free trial period?", "expected":"14 days", "relevant":[3]},
    {"q":"How much is the enterprise plan?", "expected":"$499", "relevant":[4]},
    {"q":"What storage comes with CloudSync?", "expected":"100GB", "relevant":[0]},
]


def get_embedding(text):
    r = client.embeddings.create(model="text-embedding-3-small", input=text)
    return r.data[0].embedding

def cosine_sim(a, b):
    dot = sum(x*y for x,y in zip(a,b))
    return dot / ((sum(x*x for x in a)**0.5) * (sum(x*x for x in b)**0.5) + 1e-10)


def run_benchmark():
    results = []
    log.info("benchmark_started")

    print("\nEmbedding knowledge base...")
    kb_embs = [get_embedding(d) for d in KB]

    all_precision = []
    all_recall = []
    all_faithfulness = []
    all_relevance = []

    print(f"\n  {'Question':<35} {'Prec':>6} {'Rec':>6} {'Faith':>6} {'Rel':>6}")
    print("  " + "-" * 62)

    for test in EVAL_SET:
        # Retrieve top 2
        q_emb = get_embedding(test["q"])
        scores = [(cosine_sim(q_emb, kb_embs[i]), i) for i in range(len(KB))]
        scores.sort(key=lambda x: -x[0])
        retrieved = [scores[0][1], scores[1][1]]
        context = " ".join([KB[i] for i in retrieved])

        # Generate answer
        try:
            r = client.chat.completions.create(model=MODEL, temperature=0, max_tokens=100,
                messages=[{"role":"system","content":"Answer from context only. If not found, say not mentioned."},
                         {"role":"user","content":f"Context: {context}\nQuestion: {test['q']}"}])
            answer = r.choices[0].message.content.strip()
        except: continue

        # Precision: did we get the right docs?
        precision = len(set(retrieved) & set(test["relevant"])) / len(retrieved)
        
        # Recall: did we find all relevant docs?
        recall = len(set(retrieved) & set(test["relevant"])) / len(test["relevant"])

        # Faithfulness: is answer from context?
        try:
            fr = client.chat.completions.create(model=MODEL, temperature=0, max_tokens=10,
                messages=[{"role":"user","content":f"Is this answer supported by the context? yes/no.\nContext: {context}\nAnswer: {answer}"}])
            faithful = "yes" in fr.choices[0].message.content.lower()
        except: faithful = False

        # Relevance: does answer address the question?
        try:
            rr = client.chat.completions.create(model=MODEL, temperature=0, max_tokens=10,
                messages=[{"role":"user","content":f"Does this answer address the question? yes/no.\nQ: {test['q']}\nA: {answer}"}])
            relevant = "yes" in rr.choices[0].message.content.lower()
        except: relevant = False

        all_precision.append(precision)
        all_recall.append(recall)
        all_faithfulness.append(1 if faithful else 0)
        all_relevance.append(1 if relevant else 0)

        print(f"  {test['q'][:33]:<35} {precision:>5.0%} {recall:>5.0%} {'Y' if faithful else 'N':>6} {'Y' if relevant else 'N':>6}")

    # Averages
    avg_p = sum(all_precision)/len(all_precision)*100 if all_precision else 0
    avg_r = sum(all_recall)/len(all_recall)*100 if all_recall else 0
    avg_f = sum(all_faithfulness)/len(all_faithfulness)*100 if all_faithfulness else 0
    avg_rel = sum(all_relevance)/len(all_relevance)*100 if all_relevance else 0

    metric_precision.set(avg_p)
    metric_recall.set(avg_r)
    metric_faithfulness.set(avg_f)
    metric_relevance.set(avg_rel)

    overall = avg_p >= 70 and avg_r >= 70 and avg_f >= 90 and avg_rel >= 80
    metric_overall.set(1 if overall else 0)

    results = [{"metric":"precision","score":round(avg_p,1),"target":70},
               {"metric":"recall","score":round(avg_r,1),"target":70},
               {"metric":"faithfulness","score":round(avg_f,1),"target":90},
               {"metric":"relevance","score":round(avg_rel,1),"target":80}]

    log.info("benchmark_complete")
    return results


def show_analysis(results):
    print("\nRAG QUALITY DASHBOARD")
    print("=" * 50)
    for r in results:
        status = "PASS" if r["score"] >= r["target"] else "FAIL"
        print(f"  {r['metric']:<14} {r['score']:>5.0f}% (target: {r['target']}%)  {status}")
    
    overall = all(r["score"] >= r["target"] for r in results)
    print(f"\n  OVERALL: {'PASS — safe to deploy' if overall else 'FAIL — fix before deploying'}")
    if any(r["metric"]=="faithfulness" and r["score"]<90 for r in results):
        print("  WARNING: Faithfulness below 90% = system is lying to users!")


def save_results(results):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{RESULTS_DIR}/rag_eval_{ts}.csv"
    if results:
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=results[0].keys())
            w.writeheader(); w.writerows(results)
    log.info("saved", path=path); return path


def test_5_eval_questions():
    assert len(EVAL_SET) == 5

def test_5_kb_docs():
    assert len(KB) == 5


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
