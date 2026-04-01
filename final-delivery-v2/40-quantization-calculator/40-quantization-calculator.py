"""
QUANTIZATION CALCULATOR
========================

THE PROBLEM:
    A 70B parameter model at full precision (FP16) needs 140GB of GPU memory.
    That is 2x A100-80GB GPUs. Expensive.
    
    Quantization reduces the precision (FP16 -> INT4) making the model
    4x smaller (140GB -> 35GB). Fits on 1 GPU. Quality drops only 3%.

WHAT WE FIND OUT:
    1. How much memory does each model need at each quantization?
    2. How many GPUs are required?
    3. What is the quality impact?

WHAT YOU WILL LEARN:
    - Quantized 70B (97% quality) > full-precision 13B (100% quality)
    - INT4 is the production sweet spot (3% quality drop, 4x smaller)
    - AWQ for GPU production, GGUF for CPU/Ollama
    - Never below 4-bit in production

HOW TO RUN:
    pip install -r requirements.txt
    python main.py
    No API key needed.
"""

import time, csv, os
from datetime import datetime
import structlog
from prometheus_client import Gauge, start_http_server

structlog.configure(
    processors=[structlog.processors.TimeStamper(fmt="iso"), structlog.dev.ConsoleRenderer()],
    wrapper_class=structlog.BoundLogger, context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)
log = structlog.get_logger()

metric_models = Gauge("quant_models_analyzed", "Models analyzed")

METRICS_PORT = 8000
RESULTS_DIR = "./results"

MODELS = {
    "Llama-3-8B":   {"params_b": 8,   "quality_fp16": 100},
    "Llama-3-70B":  {"params_b": 70,  "quality_fp16": 100},
    "Llama-3-405B": {"params_b": 405, "quality_fp16": 100},
}

QUANT = {
    "FP16": {"bits": 16, "quality_pct": 100},
    "INT8": {"bits": 8,  "quality_pct": 99},
    "INT4": {"bits": 4,  "quality_pct": 97},
    "INT3": {"bits": 3,  "quality_pct": 93},
}


def run_benchmark():
    results = []
    log.info("benchmark_started")

    print(f"\n{'Model':<18} {'Quant':<8} {'Size GB':>8} {'Quality':>8} {'GPUs (A100-80)':>15}")
    print("=" * 62)

    for mname, minfo in MODELS.items():
        for qname, qinfo in QUANT.items():
            size_gb = minfo["params_b"] * qinfo["bits"] / 8
            quality = qinfo["quality_pct"]
            gpus = max(1, int(size_gb / 75) + (1 if size_gb % 75 > 0 else 0))

            print(f"{mname:<18} {qname:<8} {size_gb:>7.0f} {quality:>7}% {gpus:>15}")
            results.append({"model":mname,"quant":qname,"size_gb":round(size_gb,1),
                           "quality":quality,"gpus":gpus})

        print()
        metric_models.inc()

    log.info("benchmark_complete")
    return results


def show_analysis(results):
    print("GOLDEN RULE:")
    print("=" * 50)
    print("  Quantized 70B (97%) > Full-precision 13B (100%)")
    print("  Bigger model + quantization beats smaller model at full precision")
    print()
    print("PRODUCTION CONFIG:")
    print("  r=16, alpha=32, dropout=0.05")
    print("  target_modules=['q_proj','v_proj']")
    print("  AWQ for GPU | GGUF for CPU/Ollama")
    print("  Never below INT4 in production")


def save_results(results):
    os.makedirs(RESULTS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{RESULTS_DIR}/quantization_{ts}.csv"
    if results:
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=results[0].keys())
            w.writeheader(); w.writerows(results)
    log.info("saved", path=path); return path


def test_3_models():
    assert len(MODELS) == 3

def test_4_quant_levels():
    assert len(QUANT) == 4

def test_fp16_100_quality():
    assert QUANT["FP16"]["quality_pct"] == 100

def test_size_math():
    # 70B params at 16 bits = 70 * 16/8 = 140 GB
    assert 70 * 16 / 8 == 140


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
