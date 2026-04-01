# Tokenizer Shootout


## The Problem

When you send text to ChatGPT, you pay per "token" (small pieces of text).

But most people don't know this:

    The word "Hello"  = 1 token
    The Chinese "你好"  = 2 tokens

Same meaning. Double the price.

Different models also use different tokenizers. So the same text can cost
different amounts depending on which model you pick.


## What We Want to Find Out

1. **How many tokens does each language produce?**
   Is Chinese really 2-3x more expensive than English?

2. **Is the new tokenizer (GPT-4o) cheaper than the old one (GPT-3.5)?**
   By how much?

3. **How much will this cost at scale?**
   If we send 1 million messages per day, what is the monthly bill?

4. **Which model is cheapest?**
   gpt-4o-mini vs gpt-4o vs gpt-4. How big is the difference?


## Why This Matters

Imagine you work at a bank. Your team is building a customer support chatbot.
Your boss asks: "How much will this cost us per month?"

You need to measure actual token counts, multiply by the price, and project
to your expected volume. That is exactly what this code does.


## What the Code Does

```
Step 1. Take 27 real texts (English, Chinese, Arabic, code, documents)
Step 2. Run each text through 2 tokenizers (GPT-4o and GPT-3.5)
Step 3. Count the tokens each one produces
Step 4. Calculate cost per API call for 4 different models
Step 5. Project monthly cost at 1K, 10K, 100K, 1M calls per day
Step 6. Save all results to a CSV file
Step 7. Show live metrics in Prometheus
Step 8. If using Docker: see live Grafana dashboard with 8 charts
```


## What You Will Learn from the Results

- English: ~4.5 characters per token (cheapest)
- Chinese/Japanese/Korean: ~1.5 characters per token (2-3x more expensive)
- Spanish, French, German: almost as cheap as English
- gpt-4o-mini at 1M calls/day: ~$3,000/month
- gpt-4 at 1M calls/day: ~$300,000/month (100x more!)
- Model choice matters 100x more than language choice


---


## What You Need First

| What | How to check | Where to get it |
|------|-------------|-----------------|
| Python 3.10+ | `python --version` | https://python.org |
| pip | comes with Python | already installed |
| Docker Desktop | open the app | https://docker.com (only for Option 2) |
| Web browser | Chrome, Firefox, Edge | already installed |
| Terminal | Command Prompt (Win) / Terminal (Mac) | already installed |


---


## Option 1: Run Just the App (no Docker needed)

### Step 1. Open your terminal

### Step 2. Go to the project folder
```bash
cd 01-tokenizer-shootout
```

### Step 3. Install Python packages
```bash
pip install tiktoken structlog prometheus-client pytest
```

### Step 4. Run the app
```bash
python main.py
```

### Step 5. What you will see in the terminal

You will see this output:
```
2024-01-15T10:00:01Z [info] tokenizers_loaded  new=o200k_base old=cl100k_base
2024-01-15T10:00:01Z [info] benchmark_started  samples=27

Name             Category    Chars  GPT4o  GPT35    Diff  Ch/Tok
-----------------------------------------------------------------
greeting         english        33      8      8  +0.0%    4.1
refund_q         english        65     14     15  +6.7%    4.6
...
chinese          cjk            28     20     21  +4.8%    1.4
japanese         cjk            27     18     19  +5.3%    1.5
...

RESULTS BY CATEGORY
=======================================================
english        10          18          4.6
code            3          31          3.3
cjk             3          18          1.5  <-- EXPENSIVE
...

MONTHLY COST PROJECTION
=======================================================
gpt-4o-mini      |      $2.85     $28.50     $285.00    $2,850.00
gpt-4            |    $300.60  $3,006.00  $30,060.00  $300,600.00

DONE!
  CSV saved: results/tokenizer_benchmark_20240115_100001.csv
  Metrics: http://localhost:8000/metrics
```

### Step 6. Open your browser

Go to: **http://localhost:8000/metrics**

You will see a page with text like:
```
tokenizer_tokens_total{encoding="o200k",category="english"} 156.0
tokenizer_tokens_total{encoding="o200k",category="cjk"} 54.0
tokenizer_cost_dollars_total{model="gpt-4o-mini"} 0.000098
tokenizer_duration_seconds_bucket{encoding="o200k",le="0.001"} 27.0
```

This is what Prometheus reads. At a bank, Grafana turns this into charts.

### Step 7. Check the CSV file

Open the `results/` folder. You will find a file like:
```
results/tokenizer_benchmark_20240115_100001.csv
```

Open it in Excel. It has columns: name, category, chars, tokens_gpt4o, tokens_gpt35, efficiency_pct, chars_per_token

### Step 8. Stop the app
Press `Ctrl+C` in your terminal.


---


## Option 2: Full Monitoring Stack (Docker + Prometheus + Grafana)

### Step 1. Open Docker Desktop
Wait until it says "Docker is running."

### Step 2. Open terminal and go to the project folder
```bash
cd 01-tokenizer-shootout
```

### Step 3. Start everything
```bash
docker-compose up --build
```

Wait about 30 seconds. You will see logs from 3 services.

### Step 4. Open these 3 URLs:

---

#### http://localhost:3000 — GRAFANA DASHBOARD

**Login:** admin / admin (click "Skip" when asked to change password)

You will see **8 charts:**

| # | Chart Name | What It Shows |
|---|-----------|---------------|
| 1 | Total Tokens Processed | Big green number — how many tokens counted |
| 2 | Total Estimated Cost | Dollars spent |
| 3 | Samples Processed | How many texts processed |
| 4 | Average Latency | How fast tokenization runs |
| 5 | Tokens by Tokenizer | Bar chart: o200k vs cl100k |
| 6 | Tokens by Language | Bar chart: English vs Chinese vs Code |
| 7 | Cost by Model | Bar chart: mini vs 4o vs 4 |
| 8 | Latency Distribution | Histogram: fast vs slow calls |

**If charts are empty:** wait 30 seconds and refresh the page.

---

#### http://localhost:9090 — PROMETHEUS

Type these queries in the search box and click "Execute":

| Query | What You See |
|-------|-------------|
| `tokenizer_tokens_total` | Total tokens by encoding and category |
| `sum(tokenizer_tokens_total) by (category)` | Tokens grouped by language |
| `sum(tokenizer_cost_dollars_total) by (model)` | Cost grouped by model |
| `histogram_quantile(0.95, tokenizer_duration_seconds_bucket)` | 95th percentile latency |

---

#### http://localhost:8000/metrics — RAW METRICS

Same raw metrics page as Option 1 Step 6.

---

### Step 5. Stop everything
```bash
Ctrl+C
```
or
```bash
docker-compose down
```


---


## Option 3: Run Tests

```bash
pip install tiktoken structlog prometheus-client pytest
pytest main.py -v
```

You will see:
```
test_empty_returns_zero PASSED
test_hello_has_tokens PASSED
test_longer_text_more_tokens PASSED
test_count_both_gives_two_numbers PASSED
test_cost_is_positive PASSED
test_unknown_model_gives_zero PASSED
test_mini_cheaper_than_4o PASSED

7 passed in 0.5s
```

All PASSED = code works. Any FAILED = something is wrong.


---


## All URLs in One Place

| URL | What | When |
|-----|------|------|
| http://localhost:8000/metrics | Raw Prometheus metrics | Option 1 and 2 |
| http://localhost:9090 | Prometheus query page | Option 2 only |
| http://localhost:3000 | Grafana dashboard (admin/admin) | Option 2 only |


---


## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError: No module named 'tiktoken'` | Run `pip install tiktoken` |
| `Port 8000 already in use` | Another app uses port 8000. Close it or change METRICS_PORT in main.py |
| `Cannot connect to the Docker daemon` | Open Docker Desktop, wait for "Docker is running" |
| Grafana charts are empty | Wait 30 seconds, then refresh. Prometheus collects every 15s. |
| `docker-compose: command not found` | Install Docker Desktop from https://docker.com |
| `pytest: command not found` | Run `pip install pytest` |


---


## Files

| File | What |
|------|------|
| `main.py` | All the code: tokenizer, cost calculator, benchmark, metrics, tests |
| `requirements.txt` | Python packages |
| `Dockerfile` | Packages app into Docker container |
| `docker-compose.yml` | Starts app + Prometheus + Grafana |
| `prometheus.yml` | Tells Prometheus where to scrape |
| `grafana/` | Pre-built dashboard (8 charts, auto-loaded) |
| `README.md` | This file |


## What is Inside main.py (11 sections)

| Section | What |
|---------|------|
| Step 1 | Imports — loads all tools |
| Step 2 | Logging — structlog setup (what banks use instead of print) |
| Step 3 | Prometheus — metrics counters and histograms |
| Step 4 | Config — all settings (prices, ports) |
| Step 5 | TokenizerService — class that counts tokens |
| Step 6 | calculate_cost — function that gives dollars |
| Step 7 | Test data — 27 texts in 11 languages |
| Step 8 | run_benchmark — counts tokens for all texts |
| Step 9 | Analysis — category breakdown, cost projection |
| Step 10 | Tests — 7 tests (run with pytest) |
| Step 11 | Run everything — starts server, runs benchmark, saves CSV |


## How Banks Use These Tools

```
main.py (your code)
    |  produces metrics on port 8000
    v
Prometheus (collects every 15 seconds)
    |  stores time-series data
    v
Grafana (charts on big screens)
    |  alerts if something wrong
    v
PagerDuty (wakes up engineer at 3am)
    v
Splunk (search millions of log lines)
```
