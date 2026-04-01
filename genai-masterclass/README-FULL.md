# GenAI / LLM Senior Architect — Complete Training System

I built this to go from zero to senior architect level in GenAI/LLM systems.

Two parts:
1. **Masterclass** — 11 modules covering every topic a senior architect needs to know
2. **58 Mini-Projects** — production Python code you run locally with real monitoring

Everything here is written in simple English. Every concept has a real-world analogy.
Every piece of code runs on your machine and produces real numbers.


---


## Why I Built This

Most GenAI courses teach you to call the OpenAI API and stop there.
That is maybe 5% of what a senior architect actually does.

The other 95%:
- How do you pick the right model for each task?
- How do you stop the AI from making things up?
- How do you handle 1 million queries a day without going bankrupt?
- How do you test prompts before deploying them?
- How do you monitor everything like a real production system?
- How do you defend against prompt injection attacks?
- How do you deal with Chinese text costing 3x more than English?

Every one of these questions is answered by running actual code and looking at the numbers.


---


## What Is In Each Tar


### genai-masterclass.tar.gz (6.4 MB, 82 files)

This is the study material. 11 modules, each covering one major topic.

```
tar -xzf genai-masterclass.tar.gz
```

```
genai-masterclass/
├── README.md                       272 KB master reference guide
├── 00-revision/
│   ├── pocket-notes-all.jsx        Quick cards for revision before interviews
│   └── interview-prep-all.jsx      100+ interview Q&A with senior-level answers
├── 01-prompt-engineering/
│   ├── prompt-engineering-masterclass-v2.jsx      Interactive lesson (glassmorphism design)
│   ├── prompt-engineering-masterclass-original.jsx Original design
│   ├── prompt-engineering-masterclass.pdf          Dark-themed printable version
│   ├── 01-prompt-engineering-lab.ipynb             Runnable Jupyter notebook
│   ├── d7-prompt-engineering.mermaid               Architecture diagram source
│   └── d7-prompt-engineering.pdf                   Rendered diagram (zoomed, dark)
├── 02-rag/                          (same 6-file structure)
├── 03-agents/
├── 04-finetuning/
├── 05-orchestration/
├── 06-eval/
├── 07-infra/
├── 08-safety/
├── 09-multimodal/
├── 10-architecture/
└── 11-advanced/
```

Each module has 6 files:
- **v2 JSX** — the main interactive lesson with glassmorphism cards, expandable panels, code examples
- **original JSX** — first version, slightly different layout
- **PDF** — dark-themed printable version of the JSX (all panels preserved)
- **lab notebook** — Jupyter notebook with runnable code
- **mermaid source** — architecture diagram you can edit
- **diagram PDF** — rendered and zoomed version of the diagram

The 11 modules:

| # | Module | What It Covers |
|---|--------|---------------|
| 01 | Prompt Engineering | Zero-shot, few-shot, CoT, templates, injection defense |
| 02 | RAG | Chunking, embeddings, vector search, hybrid search, reranking |
| 03 | Agents | ReAct, Plan-Execute, tool use, human-in-the-loop |
| 04 | Fine-tuning | SFT, LoRA, QLoRA, DPO, data preparation |
| 05 | Orchestration | LangChain, LlamaIndex, semantic routing, fallback chains |
| 06 | Evaluation | LLM-as-judge, golden tests, A/B testing, RAGAS metrics |
| 07 | Infrastructure | Multi-provider gateway, caching, rate limiting, cost tracking |
| 08 | Safety | Guardrails, PII handling, bias testing, content filtering |
| 09 | Multimodal | Vision, audio, document processing, cost optimization |
| 10 | Architecture | Compound AI systems, model routing, platform design |
| 11 | Advanced | MCP, knowledge graphs, distillation, self-improving systems |

Plus revision pocket notes and 100+ interview Q&A at senior architect level.


### genai-mini-projects-all-58.tar.gz (208 KB, 523 files)

This is the hands-on part. 58 projects you run on your machine.

```
tar -xzf genai-mini-projects-all-58.tar.gz
```

```
final-delivery-v2/
├── README.md
├── 01-tokenizer-shootout/
│   ├── 01-tokenizer-shootout.py     All code and tests in one file
│   ├── README.md                    Problem statement and run instructions
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── docker-compose.yml           Starts app + Prometheus + Grafana
│   ├── prometheus.yml
│   └── grafana/                     Pre-built dashboard
├── 02-temperature-playground/
│   ├── 02-temperature-playground.py
│   └── ...
├── ...
└── 58-mcp-server-template/
```

Every project follows the same pattern:
- Opens with THE PROBLEM (what goes wrong without this knowledge)
- Then WHAT WE FIND OUT (specific questions we answer with data)
- Then WHY THIS MATTERS (your boss asks you something, you need a number)
- Then WHAT YOU WILL LEARN (actual answers with real measurements)
- Then the code, clearly commented, simple functions and classes
- Then tests you run with pytest
- Then Docker + Prometheus + Grafana for real monitoring

The monitoring stack is the same one used at Morgan Stanley, Goldman Sachs, and every serious tech company. structlog for logging, prometheus_client for metrics, Grafana for dashboards.


---


## All 58 Mini-Projects

### LLM Foundations (01-06)

| # | Name | API? | What You Prove With Data |
|---|------|------|------------------------|
| 01 | tokenizer-shootout | No | Chinese costs 2-3x more tokens than English. Model choice matters 100x more than language choice |
| 02 | temperature-playground | Yes | temp=0 for facts, 0.3-0.7 for production, above 1.2 is garbage |
| 03 | context-window-stress-test | Yes | Info buried in the middle of long text gets ignored. Start and end are reliable |
| 04 | model-family-comparison | Yes | Mini handles factual and classification perfectly. GPT-4o only wins on complex reasoning |
| 05 | stop-sequences-repetition | Yes | Stop sequences save 20-50% of output tokens. frequency_penalty 0.3-0.7 is the sweet spot |
| 06 | token-cost-calculator | No | Exact monthly cost for any text at any scale. System prompts add up fast |

### Prompt Engineering (07-15)

| # | Name | API? | What You Prove With Data |
|---|------|------|------------------------|
| 07 | zero-few-dynamic-benchmark | Yes | Zero-shot is 85-95% on clear tasks. Few-shot costs 3-5x more tokens |
| 08 | cot-vs-direct-benchmark | Yes | Chain-of-thought helps math +15-25% but wastes money on simple classification |
| 09 | structured-output-benchmark | Yes | JSON mode is 100% parseable. Raw text fails 20-40% of the time |
| 10 | prompt-chaining-benchmark | Yes | Parallel chain gives same quality as sequential but finishes 2-3x faster |
| 11 | self-consistency-benchmark | Yes | Majority vote of 5 calls costs 5x but only helps on hard questions |
| 12 | system-prompt-position | Yes | Rules at top of prompt: followed most. Rules in middle: ignored most |
| 13 | meta-prompting | Yes | GPT-4 writes better prompts than humans because it covers edge cases |
| 14 | jinja2-templates | Yes | One template with variables serves 10,000 different customers |
| 15 | injection-attack-lab | Yes | Without defenses: 30-60% breach rate. With 4 layers: under 5% |

### RAG (16-22)

| # | Name | API? | What You Prove With Data |
|---|------|------|------------------------|
| 16 | chunking-benchmark | Yes | Fixed-size chunking is worst. Paragraph-aware is default. 20-30% accuracy swing |
| 17 | search-shootout | Yes | Dense search finds meaning. BM25 finds exact words. Hybrid catches everything |
| 18 | multi-query-benchmark | Yes | Rephrase question 3 ways, search each, combine. Finds 15-25% more relevant docs |
| 19 | hallucination-trap | Yes | Without grounding instruction: 50-80% hallucination. With one line: drops to 5-15% |
| 20 | embedding-shootout | Yes | Small embedding model is enough for 90% of use cases. Large costs 6x for 2-5% gain |
| 21 | bias-audit | Yes | Same prompt, different names. Measures leadership language disparity across groups |
| 22 | rag-eval-dashboard | Yes | Four metrics: precision, recall, faithfulness, relevance. If faithfulness below 90%, stop |

### Agents and Architecture (23-28)

| # | Name | API? | What You Prove With Data |
|---|------|------|------------------------|
| 23 | react-vs-plan-execute | Yes | ReAct works for simple tasks. Plan-Execute for multi-step. Tool descriptions matter more than pattern |
| 24 | tool-description-impact | Yes | Vague tool descriptions vs specific ones. 15-30% accuracy difference. This is the #1 quality lever |
| 25 | model-routing-savings | Yes | 70% of queries are simple. Route to mini. Save 60-70% with zero quality loss |
| 26 | compound-vs-monolith | Yes | Classifier + routed generator saves 70-90% vs sending everything to GPT-4o |
| 27 | pii-pipeline | Yes | Replace real emails and SSNs with placeholders before the LLM sees them. Put them back after |
| 28 | semantic-cache | Yes | "Refund policy?" and "how do returns work?" get the same cached answer. Saves 30-40% of API calls |

### Eval and Tools (29-42)

| # | Name | API? | What You Prove With Data |
|---|------|------|------------------------|
| 29 | llm-as-judge | Yes | AI judges agree with humans 80-90% of the time at 1/100th the cost |
| 30 | rag-in-30-lines | Yes | The entire RAG pipeline works in 30 lines. Everything else is optimization |
| 31 | vision-analysis | Yes | GPT-4o extracts structured JSON from image descriptions. detail:low saves 10x |
| 32 | synthetic-data-pipeline | Yes | 5 seed examples generate 20+ quality training examples at $0.01 each |
| 33 | streaming-demo | Yes | One flag (stream=True) makes first word appear in 200ms instead of 2-3 seconds |
| 34 | mapreduce-summarization | Yes | Split big doc into chunks, summarize in parallel, combine. Handles unlimited size |
| 35 | iterative-refinement | Yes | Generate, critique, rewrite. Quality improves +2 points per round. 3 rounds is the sweet spot |
| 36 | prompt-ab-tester | Yes | Two prompt variants, 15 test cases, statistical winner. Reusable for any comparison |
| 37 | cost-anomaly-detector | Yes | Track every API call. Alert when cost spikes above 2 standard deviations |
| 38 | dpo-data-pipeline | Yes | Generate chosen/rejected pairs for alignment. 5K pairs for $10 instead of $2K human annotators |
| 39 | guardrail-comparison | Yes | Output validation, topic control, input scanning. Each catches different threats |
| 40 | quantization-calculator | No | 70B at INT4 fits on 1 GPU. At FP16 needs 4 GPUs. Quality drops only 3% |
| 41 | embedding-pipeline-dedup | Yes | Hash dedup removes 10-30% duplicate chunks before embedding. Saves money and storage |
| 42 | llmops-pipeline | Yes | Golden tests run before every deploy. Bad prompt caught. Canary for 24h. Rollback is instant |

### Quick Demos and Advanced (43-58)

| # | Name | API? | What You Prove With Data |
|---|------|------|------------------------|
| 43 | agent-live-reasoning | Yes | Full think, act, observe trace. This is how you debug agents |
| 44 | model-router | Yes | Auto-classify queries and route to cheap vs expensive model |
| 45 | voice-of-customer | Yes | 10 reviews in, sentiment + topics + actions out, one API call |
| 46 | distillation | Yes | GPT-4o labels data once. Fine-tune mini on those labels. Deploy at 1/30th cost |
| 47 | rag-vs-finetune-tco | No | Below 10K/day: zero-shot wins. Above 100K: fine-tune always wins |
| 48 | cache-roi | No | Exact match catches 20-30%, semantic catches 30-50%. Both save real money |
| 49 | platform-cost-calculator | No | Monthly cost across 6 LLM platforms at 4 different volumes |
| 50 | content-filter-pipeline | No | PII regex, injection regex, LLM safety check. Ordered fast to slow |
| 51 | stale-data-detector | No | Old docs in your index give wrong answers. Freshness metadata fixes it |
| 52 | agent-loop-detection | No | Give agents impossible tasks. Without max steps they loop forever |
| 53 | context-overflow | No | Quality drops as context grows. RAG retrieval beats context stuffing |
| 54 | chunking-failures | No | Bad chunks split answers across pieces. Good chunks keep them together |
| 55 | lora-config-calculator | No | QLoRA puts 70B on 1 GPU at 49GB. Full fine-tune needs 4 GPUs at 280GB |
| 56 | injection-firewall | No | 8 attack patterns through regex defense layers |
| 57 | knowledge-graph-mini | No | Multi-hop questions that cross 4 documents. Regular RAG misses these |
| 58 | mcp-server-template | No | MCP is USB-C for AI tools. FastMCP gives you a working server in 20 lines |


---


## How Everything Connects

The masterclass teaches you the concepts:
- Module 02 (RAG) explains chunking strategies, vector search, hybrid search, reranking

The mini-projects prove those concepts with code:
- Project 16 (chunking-benchmark) runs 4 chunking methods on the same documents and measures accuracy
- Project 17 (search-shootout) runs dense vs BM25 vs hybrid on the same queries
- Project 19 (hallucination-trap) measures hallucination rate with and without grounding

You read the module, then run the project. Theory becomes data.

| Masterclass Module | Related Mini-Projects |
|---|---|
| 01 Prompt Engineering | 07, 08, 09, 10, 11, 12, 13, 14, 15, 36 |
| 02 RAG | 16, 17, 18, 19, 20, 22, 30, 54 |
| 03 Agents | 23, 24, 43, 52 |
| 04 Fine-tuning | 32, 38, 40, 46, 55 |
| 05 Orchestration | 10, 25, 26, 34, 44 |
| 06 Evaluation | 22, 29, 36, 42 |
| 07 Infrastructure | 28, 37, 47, 48, 49 |
| 08 Safety | 15, 21, 27, 39, 50, 56 |
| 09 Multimodal | 31 |
| 10 Architecture | 25, 26, 44, 51 |
| 11 Advanced | 57, 58 |


---


## How to Run the Mini-Projects

### You need
- Python 3.10 or higher
- pip
- Docker Desktop (only for the Grafana dashboards, not required)
- OpenAI API key (only for 43 of the 58 projects)

### Start with these (no API key, no cost)
```
cd 01-tokenizer-shootout
pip install -r requirements.txt
python 01-tokenizer-shootout.py
```

15 projects run without any API key: 01, 06, 40, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58

### When you have an API key
```
export OPENAI_API_KEY=sk-your-key-here
cd 02-temperature-playground
pip install -r requirements.txt
python 02-temperature-playground.py
```

Most projects cost under $0.01 to run once.

### Full monitoring stack
```
cd 01-tokenizer-shootout
docker-compose up --build
```

Then open:
- http://localhost:3000 — Grafana dashboard (admin / admin)
- http://localhost:9090 — Prometheus queries
- http://localhost:8000/metrics — raw metrics from your app

### Run tests
```
cd 01-tokenizer-shootout
pytest 01-tokenizer-shootout.py -v
```


---


## What Tools We Use and Why

| Tool | Why | Who Uses It |
|------|-----|-------------|
| structlog | JSON logging that feeds into Splunk. Banks search millions of logs this way | Every bank |
| prometheus_client | Counters and histograms that Grafana reads. Teams watch these on big screens | Every tech company |
| pytest | Tests that block bad code from deploying. If a test fails, the change is rejected | Everyone |
| Docker | Same environment everywhere. Works on my machine = works in production | Everyone |
| Prometheus | Scrapes metrics every 15 seconds. Stores time-series data | Industry standard |
| Grafana | Draws charts. PagerDuty alerts if something breaks | Industry standard |
| tiktoken | Same tokenizer ChatGPT uses. Counts tokens locally without an API call | OpenAI |
| Jinja2 | Prompt templates with variables, conditions, loops. Store in git like code | Production teams |
| OpenAI SDK | API calls to GPT-4o, GPT-4o-mini. Most common LLM provider | Most teams |


---


## Troubleshooting

| What Went Wrong | Fix |
|-----------------|-----|
| ModuleNotFoundError | pip install -r requirements.txt |
| Port 8000 already in use | Kill the other process or change METRICS_PORT in the code |
| Grafana shows empty charts | Wait 30 seconds then refresh. Prometheus collects every 15 seconds |
| Cannot connect to Docker daemon | Open Docker Desktop and wait for it to say running |
| OPENAI_API_KEY not set | export OPENAI_API_KEY=sk-your-key-here |
| Rate limited by OpenAI | Wait 60 seconds and run again. Or add time.sleep(1) between calls |
| pytest command not found | pip install pytest |


---


## The Interview Answer

"I built a complete GenAI training system: 11 masterclass modules covering prompt engineering through advanced architectures, plus 58 production mini-projects that I ran locally with real monitoring. Every project uses structlog for observability, prometheus_client for metrics, and Docker with Prometheus and Grafana — the same stack you would see at any bank. I can show you benchmarks proving things like: chunking strategy swings RAG accuracy by 20-30%, model routing saves 60-70% on API costs, and one grounding instruction cuts hallucination from 50% to 5%. I have the numbers from running the code myself."
