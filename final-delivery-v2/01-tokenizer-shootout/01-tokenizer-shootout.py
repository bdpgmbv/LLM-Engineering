"""
TOKENIZER SHOOTOUT
==================

THE PROBLEM:
    When you send text to ChatGPT, you pay per "token" (small pieces of text).
    But most people don't know:
    
        The word "Hello" = 1 token
        The Chinese word "你好" = 2 tokens
        Same meaning. Double the price.
    
    Different models also use different tokenizers.
    So the same text costs different amounts depending on the model.

WHAT WE WANT TO FIND OUT:
    1. How many tokens does each language produce?
       Is Chinese really 2-3x more expensive than English?
    
    2. Is the new tokenizer (GPT-4o) cheaper than the old one (GPT-3.5)?
       By how much?
    
    3. How much will this cost at scale?
       If we send 1 million messages per day, what is the monthly bill?
    
    4. Which model is cheapest?
       gpt-4o-mini vs gpt-4o vs gpt-4. How big is the difference?

WHY THIS MATTERS IN REAL LIFE:
    Imagine you work at a bank. Your team is building a customer support chatbot.
    Your boss asks: "How much will this cost us per month?"
    
    You can not guess. You need to:
        - Measure actual token counts on real customer messages
        - Multiply by the model price
        - Project to your expected volume (1K, 10K, 100K, 1M calls per day)
    
    That is exactly what this code does.

WHAT THE CODE DOES STEP BY STEP:
    Step 1. Take 27 real texts (English, Chinese, Arabic, code, documents)
    Step 2. Run each text through 2 tokenizers (GPT-4o and GPT-3.5)
    Step 3. Count the tokens each one produces
    Step 4. Calculate cost per API call for 4 different models
    Step 5. Project monthly cost at 1K, 10K, 100K, 1M calls per day
    Step 6. Save all results to a CSV file
    Step 7. Show live metrics in Prometheus (open http://localhost:8000/metrics)
    Step 8. If using Docker: see live Grafana dashboard with 8 charts

WHAT YOU WILL LEARN FROM THE RESULTS:
    - English gets about 4.5 characters per token (cheapest)
    - Chinese, Japanese, Korean get about 1.5 characters per token (2-3x more expensive)
    - Spanish, French, German are almost as cheap as English
    - gpt-4o-mini at 1 million calls/day costs about $3,000/month
    - gpt-4 at 1 million calls/day costs about $300,000/month (100x more!)
    - Model choice matters 100x more than language choice
    - The new tokenizer (o200k) is about 8% more efficient than the old one (cl100k)

HOW TO RUN AND TEST (COMPLETE GUIDE):

    WHAT YOU NEED FIRST:
        - Python 3.10 or higher (check: python --version)
        - pip (comes with Python)
        - Docker Desktop (only for Option 2 — download from https://docker.com)
        - A web browser (Chrome, Firefox, Edge — any will work)
        - Terminal (Command Prompt on Windows, Terminal on Mac/Linux)

    ─────────────────────────────────────────────────────────────
    OPTION 1: RUN JUST THE APP (no Docker needed)
    ─────────────────────────────────────────────────────────────

        Step 1. Open your terminal

        Step 2. Go to the project folder
            cd 01-tokenizer-shootout

        Step 3. Install Python packages
            pip install tiktoken structlog prometheus-client pytest

        Step 4. Run the app
            python main.py

        Step 5. You will see output like this in your terminal:
            - Structured log messages (timestamps, events)
            - A table showing every text sample with token counts
            - Category analysis (which languages cost more)
            - Monthly cost projection for 4 models
            - "Metrics server started on http://localhost:8000/metrics"

        Step 6. Open your browser and go to:

            http://localhost:8000/metrics

            You will see a page full of text like:
                tokenizer_tokens_total{encoding="o200k",category="english"} 156.0
                tokenizer_cost_dollars_total{model="gpt-4o-mini"} 0.000098
                tokenizer_duration_seconds_bucket{encoding="o200k",le="0.001"} 27.0

            This is what Prometheus reads. At a bank, Grafana turns this into charts.

        Step 7. Look at the CSV file
            Open the results/ folder. You will find a file like:
                results/tokenizer_benchmark_20240115_100000.csv

            Open it in Excel or VS Code. It has every result in a table.

        Step 8. Press Ctrl+C in your terminal to stop the app

    ─────────────────────────────────────────────────────────────
    OPTION 2: RUN WITH FULL MONITORING (Docker + Prometheus + Grafana)
    ─────────────────────────────────────────────────────────────

        Step 1. Make sure Docker Desktop is running
            Open Docker Desktop. Wait until it says "Docker is running."

        Step 2. Open your terminal and go to the project folder
            cd 01-tokenizer-shootout

        Step 3. Start everything with one command
            docker-compose up --build

            This will:
            - Build your app into a Docker container
            - Start Prometheus (metrics collector)
            - Start Grafana (dashboard)
            You will see logs from all 3 services in your terminal.

        Step 4. Wait about 30 seconds for everything to start

        Step 5. Open these URLs in your browser:

            URL 1: http://localhost:3000
            ─────────────────────────────
            This is GRAFANA — the dashboard.
            Login with: username = admin, password = admin
            Click "Skip" when it asks you to change password.

            You will see a dashboard called "Tokenizer Benchmark Dashboard"
            with 8 charts:
                Chart 1: Total Tokens Processed (big green number)
                Chart 2: Total Estimated Cost in dollars
                Chart 3: Samples Processed (how many texts we counted)
                Chart 4: Average Tokenization Latency (how fast)
                Chart 5: Tokens by Tokenizer (o200k vs cl100k bar chart)
                Chart 6: Tokens by Language Category (English vs Chinese vs Code)
                Chart 7: Cost by Model (mini vs 4o vs 4 bar chart)
                Chart 8: Latency Distribution (histogram)

            If the charts are empty, wait 30 seconds and refresh.
            Prometheus collects data every 15 seconds.

            URL 2: http://localhost:9090
            ─────────────────────────────
            This is PROMETHEUS — the metrics database.
            Type this in the search box and press Execute:
                tokenizer_tokens_total
            You will see the raw numbers Prometheus collected.

            Try these queries too:
                sum(tokenizer_tokens_total) by (category)
                sum(tokenizer_cost_dollars_total) by (model)
                histogram_quantile(0.95, tokenizer_duration_seconds_bucket)

            URL 3: http://localhost:8000/metrics
            ─────────────────────────────────────
            This is YOUR APP's raw metrics endpoint.
            Same data as Option 1 Step 6.

        Step 6. To stop everything
            Press Ctrl+C in the terminal where docker-compose is running.
            Or run: docker-compose down

    ─────────────────────────────────────────────────────────────
    OPTION 3: RUN TESTS
    ─────────────────────────────────────────────────────────────

        Step 1. Install packages (if you have not already)
            pip install tiktoken structlog prometheus-client pytest

        Step 2. Run all tests
            pytest main.py -v

        Step 3. You will see output like:
            test_empty_returns_zero PASSED
            test_hello_has_tokens PASSED
            test_longer_text_more_tokens PASSED
            test_count_both_gives_two_numbers PASSED
            test_cost_is_positive PASSED
            test_unknown_model_gives_zero PASSED
            test_mini_cheaper_than_4o PASSED

            7 passed in 0.5s

        If all tests say PASSED, the code is working correctly.
        If any test says FAILED, something is wrong.

    ─────────────────────────────────────────────────────────────
    TROUBLESHOOTING
    ─────────────────────────────────────────────────────────────

        Problem: "ModuleNotFoundError: No module named 'tiktoken'"
        Fix: Run pip install tiktoken

        Problem: "Port 8000 already in use"
        Fix: Another app is using port 8000. Kill it or change METRICS_PORT in the code.

        Problem: Docker says "Cannot connect to the Docker daemon"
        Fix: Open Docker Desktop and wait for it to say "Docker is running"

        Problem: Grafana shows empty charts
        Fix: Wait 30 seconds. Prometheus collects data every 15 seconds.
             Then refresh the page.

        Problem: "docker-compose: command not found"
        Fix: Install Docker Desktop from https://docker.com

    ─────────────────────────────────────────────────────────────
    ALL URLs IN ONE PLACE
    ─────────────────────────────────────────────────────────────

        http://localhost:8000/metrics  → Your app raw metrics (always works)
        http://localhost:9090          → Prometheus query page (Docker only)
        http://localhost:3000          → Grafana dashboard (Docker only, login: admin/admin)

"""


# ──────────────────────────────────────────────────────
# STEP 1: IMPORTS
# ──────────────────────────────────────────────────────

import tiktoken      # OpenAI's tokenizer (breaks text into tokens)
import time          # to measure how long things take
import csv           # to save results to a CSV file
import os            # to create folders and read environment variables
from datetime import datetime
from collections import defaultdict

import structlog     # structured logging (what banks use instead of print)
from prometheus_client import (
    Counter,           # a number that only goes up (total tokens, total cost)
    Histogram,         # tracks how long things take (p50, p95 latency)
    Gauge,             # a number that goes up and down (progress)
    start_http_server, # starts a web page showing all metrics
    generate_latest,   # prints all metrics as text
)


# ──────────────────────────────────────────────────────
# STEP 2: LOGGING SETUP
# ──────────────────────────────────────────────────────
# Banks don't use print(). They use structured logging.
# Every log line becomes JSON that feeds into Splunk/Datadog.
# This lets you search millions of logs: "show me all errors from yesterday"

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
        # At a bank, replace the line above with:
        # structlog.processors.JSONRenderer()
        # That makes every log a JSON line → feeds into Splunk
    ],
    wrapper_class=structlog.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

log = structlog.get_logger()


# ──────────────────────────────────────────────────────
# STEP 3: PROMETHEUS METRICS SETUP
# ──────────────────────────────────────────────────────
# Prometheus collects numbers from your app.
# Grafana reads those numbers and draws charts on a big screen.
# At banks, teams watch these dashboards all day.
#
# Your code → Prometheus (collects) → Grafana (draws charts) → PagerDuty (alerts)

# Counter: total tokens counted (only goes up — you can't un-count tokens)
metric_tokens = Counter(
    "tokenizer_tokens_total",
    "Total tokens counted",
    ["encoding", "category"],
)

# Counter: total estimated cost in dollars
metric_cost = Counter(
    "tokenizer_cost_dollars",
    "Estimated cost in USD",
    ["model"],
)

# Histogram: how long each tokenization takes
# Grafana shows: "50% take 0.001s, 95% take 0.005s" (called p50 and p95)
metric_duration = Histogram(
    "tokenizer_duration_seconds",
    "Time to tokenize one text",
    ["encoding"],
    buckets=[0.0001, 0.0005, 0.001, 0.005, 0.01],
)

# Gauge: progress counter (goes up as we process samples)
metric_progress = Gauge(
    "tokenizer_samples_processed",
    "Samples processed so far",
)


# ──────────────────────────────────────────────────────
# STEP 4: CONFIGURATION
# ──────────────────────────────────────────────────────
# All settings in one place. If anyone needs to change something,
# they look here — not buried somewhere in the code.

# Model pricing (per 1 million tokens)
# "input" = text you send to the model (your question)
# "output" = text the model sends back (its answer — costs more)
PRICING = {
    "gpt-4o":        {"input": 2.50,  "output": 10.00, "enc": "o200k"},
    "gpt-4o-mini":   {"input": 0.15,  "output": 0.60,  "enc": "o200k"},
    "gpt-3.5-turbo": {"input": 0.50,  "output": 1.50,  "enc": "cl100k"},
    "gpt-4":         {"input": 30.00, "output": 60.00, "enc": "cl100k"},
}

AVG_OUTPUT_TOKENS = 150    # typical response length
RESULTS_DIR = "./results"  # where CSV files get saved
METRICS_PORT = 8000        # http://localhost:8000/metrics


# ──────────────────────────────────────────────────────
# STEP 5: TOKENIZER SERVICE (the main business logic)
# ──────────────────────────────────────────────────────
# This class loads both tokenizers once and reuses them.
# Why a class? Because loading the tokenizer reads a big file.
# If we loaded it every time, it would be slow.

class TokenizerService:

    def __init__(self):
        # Load the tokenizer files (this takes ~0.5 seconds)
        self.tokenizer_new = tiktoken.get_encoding("o200k_base")   # GPT-4o family
        self.tokenizer_old = tiktoken.get_encoding("cl100k_base")  # GPT-3.5/4
        log.info("tokenizers_loaded", new="o200k_base", old="cl100k_base")

    def count(self, text, encoding="o200k", category="unknown"):
        """
        Count how many tokens a text produces.

        text     = the text (example: "Hello world")
        encoding = "o200k" for GPT-4o or "cl100k" for GPT-3.5
        category = what kind of text ("english", "cjk", "code")

        Returns: number of tokens (example: 2)
        """
        if not text:
            return 0

        start = time.time()

        if encoding == "o200k":
            token_count = len(self.tokenizer_new.encode(text))
        elif encoding == "cl100k":
            token_count = len(self.tokenizer_old.encode(text))
        else:
            log.error("unknown_encoding", encoding=encoding)
            return 0

        elapsed = time.time() - start

        # Record in Prometheus (Grafana will show this)
        metric_tokens.labels(encoding=encoding, category=category).inc(token_count)
        metric_duration.labels(encoding=encoding).observe(elapsed)

        return token_count

    def count_both(self, text, category="unknown"):
        """Count with both tokenizers. Returns (new_count, old_count)."""
        return self.count(text, "o200k", category), self.count(text, "cl100k", category)


# ──────────────────────────────────────────────────────
# STEP 6: COST CALCULATOR
# ──────────────────────────────────────────────────────

def calculate_cost(input_tokens, output_tokens, model):
    """
    How much does one API call cost in dollars?

    Example:
        calculate_cost(100, 150, "gpt-4o-mini")  → $0.000098
        calculate_cost(100, 150, "gpt-4")         → $0.012
        That's 100x difference!
    """
    pricing = PRICING.get(model)
    if not pricing:
        log.error("unknown_model", model=model)
        return 0.0

    # (tokens / 1,000,000) × price per million = cost in dollars
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    total = input_cost + output_cost

    # Record in Prometheus
    metric_cost.labels(model=model).inc(total)
    return total


# ──────────────────────────────────────────────────────
# STEP 7: TEST DATA — 27 real-world samples
# ──────────────────────────────────────────────────────
# Each entry: (name, category, text)
# Categories let us answer: "is Chinese more expensive than English?"

SAMPLES = [
    # English — simple (this is what 70% of real traffic looks like)
    ("greeting",      "english",  "Hello, how can I help you today?"),
    ("refund_q",      "english",  "What is your refund policy for orders in the last 30 days?"),
    ("shipping_q",    "english",  "Do you offer free shipping on orders over $50?"),
    ("hours_q",       "english",  "What are your business hours on weekends?"),
    ("password_q",    "english",  "How do I reset my password?"),
    ("cancel_q",      "english",  "I want to cancel my subscription."),

    # English — longer (support tickets, reviews)
    ("ticket",        "english",  "I ordered a MacBook Pro (order #45231) on Jan 15 and it has not arrived. Tracking stuck 5 days."),
    ("review_pos",    "english",  "Best purchase this year. Build quality exceptional, battery exceeds 12 hours."),
    ("review_neg",    "english",  "Terrible. Product damaged, support took 3 days, refused refund."),
    ("api_doc",       "english",  "POST /v2/users with JSON body. Auth via Bearer token. Rate: 100/min free, 1000/min Pro."),

    # Code
    ("python",        "code",     "def calc(items):\n    return round(sum(i.price * i.qty for i in items) * 1.08, 2)"),
    ("sql",           "code",     "SELECT name, COUNT(o.id) FROM users u JOIN orders o ON u.id=o.user_id GROUP BY u.id LIMIT 50;"),
    ("json",          "code",     '{"user":"alice","items":[{"sku":"LAPTOP","price":999.99}]}'),

    # CJK — these languages cost 2-3x more than English
    ("chinese",       "cjk",      "\u6211\u4eec\u516c\u53f8\u9700\u8981\u4e00\u4e2a\u80fd\u5904\u7406\u5927\u89c4\u6a21\u6570\u636e\u5206\u6790\u7684\u4f01\u4e1a\u7ea7\u89e3\u51b3\u65b9\u6848\u3002"),
    ("japanese",      "cjk",      "\u304a\u554f\u3044\u5408\u308f\u305b\u3042\u308a\u304c\u3068\u3046\u3054\u3056\u3044\u307e\u3059\u3002\u3054\u6ce8\u6587\u306e\u72b6\u6cc1\u3092\u78ba\u8a8d\u3044\u305f\u3057\u307e\u3059\u3002"),
    ("korean",        "cjk",      "\uc548\ub155\ud558\uc138\uc694. \uc8fc\ubb38 \uc0c1\ud0dc\ub97c \ud655\uc778\ud558\uace0 \uc2f6\uc2b5\ub2c8\ub2e4."),

    # Other languages
    ("arabic",        "other",    "\u0645\u0627 \u0647\u064a \u0633\u064a\u0627\u0633\u0629 \u0627\u0644\u0627\u0633\u062a\u0631\u062f\u0627\u062f\u061f"),
    ("hindi",         "other",    "\u0915\u094d\u092f\u0627 \u0906\u092a \u092c\u0924\u0627 \u0938\u0915\u0924\u0947 \u0939\u0948\u0902 \u0915\u093f \u0911\u0930\u094d\u0921\u0930 \u0915\u092c \u0921\u093f\u0932\u0940\u0935\u0930 \u0939\u094b\u0917\u093e?"),

    # European languages
    ("russian",       "european", "\u0417\u0434\u0440\u0430\u0432\u0441\u0442\u0432\u0443\u0439\u0442\u0435, \u044f \u0445\u043e\u0442\u0435\u043b \u0431\u044b \u0443\u0437\u043d\u0430\u0442\u044c \u043e \u0432\u043e\u0437\u0432\u0440\u0430\u0442\u0435."),
    ("spanish",       "european", "\u00bfCu\u00e1l es la pol\u00edtica de devoluci\u00f3n para electr\u00f3nicos?"),
    ("french",        "european", "Bonjour, je souhaiterais des informations sur votre programme."),
    ("german",        "european", "K\u00f6nnen Sie mir mitteilen, wann meine Bestellung geliefert wird?"),

    # RAG patterns (documents you feed to the LLM)
    ("rag_small",     "rag",      "Context: Returns allowed within 30 days.\nQuestion: Can I return my laptop?"),
    ("rag_large",     "rag",      "Answer from context only.\n\n" + "Policy docs. " * 50 + "\nQ: Refund timeline?"),

    # Prompt patterns
    ("zero_shot",     "prompt",   "Classify as positive/negative/neutral: 'Product fine but shipping slow.'"),
    ("few_shot",      "prompt",   "Classify:\n'Love it!'->positive\n'Terrible'->negative\n'Best ever!'->"),
    ("system_prompt", "prompt",   "You are a support agent.\nRULES: Be professional. Never share pricing."),
]


# ──────────────────────────────────────────────────────
# STEP 8: BENCHMARK FUNCTION
# ──────────────────────────────────────────────────────

def run_benchmark(tokenizer):
    """Go through every sample, count tokens, store results."""

    results = []

    log.info("benchmark_started", samples=len(SAMPLES))

    # Print header
    print()
    print(f"{'Name':<16} {'Category':<10} {'Chars':>6} {'GPT4o':>6} {'GPT35':>6} {'Diff':>7} {'Ch/Tok':>7}")
    print("-" * 65)

    for name, category, text in SAMPLES:

        chars = len(text)

        # Count tokens with both tokenizers
        tokens_new, tokens_old = tokenizer.count_both(text, category)

        # How much more efficient is the new tokenizer?
        if tokens_old > 0:
            efficiency = ((tokens_old - tokens_new) / tokens_old) * 100
        else:
            efficiency = 0

        # Characters per token (higher = cheaper)
        chars_per_token = chars / tokens_new if tokens_new > 0 else 0

        # Update progress (Grafana shows this)
        metric_progress.inc()

        # Save result
        results.append({
            "name": name,
            "category": category,
            "chars": chars,
            "tokens_gpt4o": tokens_new,
            "tokens_gpt35": tokens_old,
            "efficiency_pct": round(efficiency, 1),
            "chars_per_token": round(chars_per_token, 1),
        })

        # Print row
        print(f"{name:<16} {category:<10} {chars:>6} {tokens_new:>6} {tokens_old:>6} {efficiency:>+6.1f}% {chars_per_token:>6.1f}")

    log.info("benchmark_complete", samples=len(results))
    return results


# ──────────────────────────────────────────────────────
# STEP 9: ANALYSIS FUNCTIONS
# ──────────────────────────────────────────────────────

def show_category_analysis(results):
    """Group by category. Answers: which languages are expensive?"""

    groups = defaultdict(list)
    for r in results:
        groups[r["category"]].append(r)

    print()
    print("RESULTS BY CATEGORY")
    print("=" * 55)
    print(f"{'Category':<12} {'Count':>6} {'Avg Tokens':>11} {'Chars/Token':>12}")
    print("-" * 55)

    for cat in ["english", "code", "european", "cjk", "other", "rag", "prompt"]:
        if cat not in groups:
            continue
        items = groups[cat]
        avg_tok = sum(r["tokens_gpt4o"] for r in items) / len(items)
        avg_cpt = sum(r["chars_per_token"] for r in items) / len(items)
        warning = "  <-- EXPENSIVE" if avg_cpt < 2.0 else ""
        print(f"{cat:<12} {len(items):>6} {avg_tok:>11.0f} {avg_cpt:>11.1f}{warning}")

    print()
    print("Chars/Token: higher = cheaper. English ~4.5, Chinese ~1.5")
    print("A Chinese chatbot costs 2-3x more than English at the same volume.")


def show_cost_projection(results):
    """Monthly cost at 1K, 10K, 100K, 1M calls per day."""

    avg_input = sum(r["tokens_gpt4o"] for r in results) / len(results)

    print()
    print("MONTHLY COST PROJECTION")
    print("=" * 70)
    print(f"Assuming: {avg_input:.0f} input tokens + {AVG_OUTPUT_TOKENS} output tokens per call")
    print()
    print(f"{'Model':<16} | {'1K/day':>10} {'10K/day':>10} {'100K/day':>11} {'1M/day':>12}")
    print("-" * 65)

    for model in PRICING:
        cost = calculate_cost(avg_input, AVG_OUTPUT_TOKENS, model)
        print(f"{model:<16} |", end="")
        for volume in [1000, 10000, 100000, 1000000]:
            monthly = cost * volume * 30
            print(f" ${monthly:>9,.2f}", end="")
        print()

    print()
    print("gpt-4o-mini at 1M/day = ~$3,000/month")
    print("gpt-4 at 1M/day       = ~$300,000/month")
    print("That is 100x difference. Model choice matters most.")


def save_results(results):
    """Save to CSV file. Open it in Excel or load with Pandas."""

    os.makedirs(RESULTS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"{RESULTS_DIR}/tokenizer_benchmark_{timestamp}.csv"

    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    log.info("results_saved", path=path, rows=len(results))
    return path


def show_prometheus_metrics():
    """Print what Prometheus has collected (same as http://localhost:8000/metrics)."""

    print()
    print("PROMETHEUS METRICS")
    print("=" * 60)
    print("(same data visible at http://localhost:8000/metrics)")
    print()

    raw = generate_latest().decode()
    for line in raw.split("\n"):
        if line and not line.startswith("#"):
            print(f"  {line}")


# ──────────────────────────────────────────────────────
# STEP 10: TESTS
# ──────────────────────────────────────────────────────
# At banks, tests run every time someone changes code.
# If a test fails, the code cannot be deployed to production.
# Run tests with: pytest main.py -v

def test_empty_returns_zero():
    t = TokenizerService()
    assert t.count("") == 0

def test_hello_has_tokens():
    t = TokenizerService()
    assert t.count("Hello") >= 1

def test_longer_text_more_tokens():
    t = TokenizerService()
    assert t.count("Hello how are you today my friend") > t.count("Hi")

def test_count_both_gives_two_numbers():
    t = TokenizerService()
    result = t.count_both("Hello")
    assert len(result) == 2

def test_cost_is_positive():
    assert calculate_cost(100, 150, "gpt-4o-mini") > 0

def test_unknown_model_gives_zero():
    assert calculate_cost(100, 150, "fake-model") == 0.0

def test_mini_cheaper_than_4o():
    assert calculate_cost(100, 100, "gpt-4o-mini") < calculate_cost(100, 100, "gpt-4o")


# ──────────────────────────────────────────────────────
# STEP 11: RUN EVERYTHING
# ──────────────────────────────────────────────────────
# This runs when you type: python main.py

if __name__ == "__main__":

    # Start Prometheus metrics server
    # Visit http://localhost:8000/metrics in your browser to see live data
    try:
        start_http_server(METRICS_PORT)
        log.info("metrics_server_started", url=f"http://localhost:{METRICS_PORT}/metrics")
    except OSError:
        log.warning("port_already_in_use", port=METRICS_PORT)

    # Create the tokenizer (loads files once)
    tokenizer = TokenizerService()

    # Run the benchmark
    results = run_benchmark(tokenizer)

    # Show analysis
    show_category_analysis(results)
    show_cost_projection(results)

    # Save to CSV
    csv_path = save_results(results)

    # Show what Prometheus collected
    show_prometheus_metrics()

    # Done
    print()
    print("=" * 50)
    print("DONE!")
    print(f"  CSV saved: {csv_path}")
    print(f"  Metrics:   http://localhost:{METRICS_PORT}/metrics")
    print()
    print("Metrics server is still running.")
    print("Open the URL above in your browser to see live data.")
    print("Press Ctrl+C to stop.")
    print("=" * 50)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log.info("shutdown")
