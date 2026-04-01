"""
LORA CONFIG CALCULATOR
======================

THE PROBLEM:
    Input model size -> get VRAM, GPU count, training cost. Pure math.

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


metric_calc = Gauge("lora_calcs", "Configs calculated")
MODELS = {
    "7B": {"params":7, "fp16_gb":14},
    "13B":{"params":13,"fp16_gb":26},
    "70B":{"params":70,"fp16_gb":140},
}

def run_benchmark():
    results = []
    log.info("benchmark_started")
    print(f"\n  {'Model':<10} {'Method':<8} {'Trainable':>10} {'VRAM GB':>10} {'GPUs':>6}")
    print("  "+"="*48)
    for name, m in MODELS.items():
        metric_calc.inc()
        for method, pct, vram_mult in [("Full","100%",2.0),("LoRA","0.5%",1.3),("QLoRA","0.5%",0.35)]:
            vram = m["fp16_gb"] * vram_mult
            gpus = max(1, int(vram/75)+1)
            print(f"  {name:<10} {method:<8} {pct:>10} {vram:>10.0f} {gpus:>6}")
        print()
    results = [{"model":n,"fp16_gb":m["fp16_gb"]} for n,m in MODELS.items()]
    log.info("benchmark_complete"); return results

def show_analysis(results):
    print("  QLoRA: 70B fits on 1 GPU (49GB) vs Full: 4 GPUs (280GB)")
    print("  Quality drop: only 3%. Try QLoRA first.")
    print("  Config: r=16, alpha=32, target=['q_proj','v_proj']")


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

def test_3_models(): assert len(MODELS) == 3

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
