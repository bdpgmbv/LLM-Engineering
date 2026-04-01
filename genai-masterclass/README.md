# llm-engineering

58 production benchmarks for LLM systems. Each one runs locally, measures something real, and ships with **Prometheus + Grafana** monitoring.

Built alongside **11 deep-dive modules** covering the full GenAI stack. The modules are the theory. The projects are the proof.

```bash
cd 01-tokenizer-shootout
pip install -r requirements.txt
python 01-tokenizer-shootout.py

# or with full monitoring
docker-compose up --build
# localhost:3000 → Grafana  |  localhost:9090 → Prometheus
```

**15 of the 58 run without an API key.**

---

## Prompt Engineering

### Techniques

- **Zero-Shot** — just give the instruction, no examples. The simplest and cheapest way to use an LLM. Works **85-92%** of the time on clear tasks. Always start here — if it works, there is nothing else to do
- **Few-Shot** — show the model 2-3 examples of what good output looks like, then ask your question. Helps when the model gets the format wrong. Costs **3-5× more** because the examples eat up tokens. Only use when zero-shot accuracy drops below 90%
- **Dynamic Few-Shot** — instead of showing the same 3 examples every time, pick the 3 most relevant examples for each question. A billing question gets billing examples. A tech question gets tech examples. **10-15% better** than fixed examples at similar cost
- **Chain-of-Thought** — tell the model to think step by step before answering. This helps on math and logic problems (**+15-25% accuracy**) but on simple yes/no questions, it just doubles the cost and adds nothing. Use it only where reasoning is needed
- **Self-Consistency** — ask the same question 5 times and go with the most common answer. Like getting a second opinion from 5 doctors. Costs **5× more.** Only worth it when being wrong has real consequences — medical, legal, financial decisions
- **Tree-of-Thought** — instead of one answer, generate 3 completely different approaches (for example: the cheapest option, the fastest option, the highest quality option) and then evaluate which one fits best. Good for **architecture and strategy decisions**

### System Prompt

- **Structure it in 4 sections:** who the AI is (persona), what it must never do (constraints), how to format answers (format), what to do in emergencies (guardrails). Without this structure, the model follows instructions inconsistently
- **Put your most important rules at the start and end of the prompt.** The model pays less attention to rules buried in the middle. We tested this — rules in the middle got violated the most
- **Keep it under 2000 words.** Longer prompts sound more thorough but the model starts forgetting parts of them
- **Never put secrets or internal rules in the prompt.** Attackers can extract them 30-60% of the time. Treat everything in the prompt as public
- **Version every prompt in git with code review.** Treat prompt changes the same way you treat code changes — review, test, deploy carefully

### Structured Output

- **XML tags** — tell the model to wrap its answer in tags like `<name>...</name>`. Works with any model from any provider. Easy to parse. The most portable option
- **JSON mode** — a setting in the API that guarantees the model returns valid JSON. The JSON will always be parseable, but there is no guarantee it has the fields you asked for
- **instructor + Pydantic** — define the exact shape of the output you want as a Python class. The library automatically retries if the model returns the wrong shape. This is the **industry standard** for production systems
- **Outlines** — controls which tokens the model is allowed to generate, character by character. Guarantees the output matches your exact format with zero retries. Only works with models running on your own hardware

### Chaining

- **Sequential** — break a complex task into steps that run one after another (summarize → extract topics → classify sentiment). Each step uses the output from the previous one. Keep it to **2-4 steps** because errors build up
- **Parallel** — run independent steps at the same time instead of waiting for each one. Same cost, **2-3× faster.** Users notice the speed difference
- **Map-Reduce** — for documents too big to process at once. Split it into pieces, process each piece separately (the "map" step), then combine all the results (the "reduce" step). Handles **unlimited document sizes**
- **Mixed-Model** — use the expensive smart model only for the step that needs intelligence, and the cheap model for everything else like formatting or summarizing. Saves **60%** on most chains

### Prompt Optimization

- **Meta-Prompting** — ask a powerful model like GPT-4 to write your prompt for you. It often writes better prompts than humans because it thinks of edge cases we miss. You pay once to generate the prompt, then use a cheap model to run it forever
- **Optimize Loops** — start with a draft prompt, see where it fails, tell the model exactly what went wrong, have it rewrite. This works in **3-5 rounds.** If it still fails after 5 rounds, the task definition is the problem, not the prompt
- **A/B Testing** — run two prompt versions side by side on the same test cases. Pick the winner based on data, not gut feeling. **Re-test every month** because model updates can change which prompt works better

### Templates

- **Jinja2 Templates** — write one prompt with blanks that get filled in per customer. One template can generate **10,000 unique prompts** by filling in different names, issues, priorities, and contexts. Store templates in git like code
- **Template Inheritance** — create a base template with your safety rules. All other templates inherit from it. This way **nobody can accidentally delete the safety rules** when editing a specific template
- **Deploy Pipeline** — roll out prompt changes the same way you roll out code: test environment → staging → send to 10% of users first → watch the metrics → full rollout if everything looks good

### Injection Defense — 4 Layers

- **Layer 1: Delimiters** — wrap the user's message inside special tags so the model knows "everything between these tags is user input, not instructions." This alone stops about **70% of attacks**
- **Layer 2: Sanitize** — before the user's message reaches the model, scan it with regex and remove known attack phrases like "ignore all previous instructions." Stops about **90% of attacks**
- **Layer 3: Instruction Hierarchy** — mark certain rules as Level 1 (unbreakable) that the model can never override no matter what the user says. Stops about **98% of attacks**
- **Layer 4: Output Scan** — before sending the response to the user, check if it accidentally contains anything from the system prompt or internal rules. If it does, block it. Stops **99.9% of attacks**

We tested all 4 layers with 12 real attack types. Without defenses: **30-60% breach rate.** With all 4: **under 5%.** This takes about 30 minutes to implement.

---

## Retrieval Augmented Generation

### Pipeline

- **How it works:** take your documents, break them into small pieces, convert each piece into numbers (embeddings), store them in a database. When a user asks a question, convert the question into numbers, find the most similar pieces, and give them to the LLM along with the question. The LLM answers using your documents instead of making things up
- **What matters most:** the way you break documents into pieces (chunking) has **20-30% impact** on accuracy. Fix this first. The search method is second. The LLM prompt is last
- **Cost:** about **$0.01-0.05 per question.** Takes about 3 seconds end-to-end

### Chunking — How You Break Documents into Pieces

- **Fixed-size** — cut every 200 characters regardless of content. **Never use this.** It splits sentences in half and puts the two halves in different pieces. The LLM sees half an answer and gives the wrong response
- **Recursive** — try to split at paragraph boundaries first, then sentences, then words. Keeps natural text units together. This is the **right default for 90% of cases**
- **Semantic** — use AI to detect where the topic changes within a document and split there. Best quality but **100× more expensive** than recursive ($0.10 versus $0.001 per document)
- **Parent-Child** — create small precise pieces for searching AND keep the original large sections for giving to the LLM. You search the small pieces to find the right spot, then hand the LLM the large section so it has full context. This is the **production standard**
- **Overlap** — make adjacent pieces share 10-20% of their text so nothing falls through the cracks at the boundary

We proved this matters: same document, same question. Bad chunking gave the wrong answer. Good chunking gave the right answer. The only thing that changed was how we split the document.

### Embeddings — Converting Text to Numbers

- **text-embedding-3-small** — the most popular model for this. Produces 1,536 numbers per piece of text. **Good enough for 90% of use cases.** Start here
- **text-embedding-3-large** — produces 3,072 numbers. More precise but costs **6× more** for only **2-5% better** accuracy. Rarely worth it
- **Matryoshka trick** — take the 1,536 numbers and keep only the first 256. You save **6× on storage** and still retain **95% of the quality**
- **Important:** if you change your embedding model later, you have to re-process every single document. Choose carefully at the start

### Vector Databases — Where You Store the Numbers

- **ChromaDB** — simplest to set up. Good for building prototypes. Not strong enough for production traffic
- **pgvector** — an extension for PostgreSQL. If you already run PostgreSQL, you can add vector search without a new database. Good up to about **10 million documents**
- **Qdrant** — purpose-built for vector search. Handles **100 million+ documents** at production scale
- **Pinecone** — fully managed service. You do not run any infrastructure. They handle everything

### Search — How You Find the Right Pieces

- **Dense search (embeddings)** — finds pieces that mean the same thing even if they use different words. "How do I get my money back?" finds a document about "refund policy." But it **completely misses** exact keyword matches like "error code 403"
- **BM25 (keyword search)** — finds exact word matches. "Error 403" finds documents containing "403." It is **free** and needs no embeddings. But it misses synonyms — "car" will not find "automobile"
- **Hybrid search** — runs both dense and keyword search, then merges the results. **Catches everything.** This is what every production system should use
- **Reranking** — after finding the top 20 results, use a smarter model to re-score them and pick the best 5. Adds about 200 milliseconds but improves precision by **10-20%**

### Advanced Retrieval

- **Multi-Query** — instead of searching once, rephrase the question 3 different ways and search each version. Combine all results. Finds **15-25% more relevant documents** that the original wording missed. Only 10 lines of code. Always worth doing
- **HyDE** — generate a hypothetical answer to the question first, then search using that answer instead of the question. Works **10-20% better** on abstract or complex questions
- **Self-RAG** — check if the question even needs document retrieval. Simple questions like "what is 2+2" do not need it. Skipping retrieval when it is not needed saves **30-50% of cost**
- **CRAG** — after retrieving documents, grade each one for relevance and throw away the irrelevant ones before giving them to the LLM. Reduces hallucination by **20-40%**
- **GraphRAG** — build a knowledge graph (a map of entities and their relationships) from your documents. This lets you answer questions that require following a chain across multiple documents, like "who does the new hire ultimately report to?" Regular search cannot do this

### Multimodal Documents

- **Tables** → convert to markdown. LLMs understand markdown tables surprisingly well
- **Images** → send to GPT-4o and ask it to describe what it sees. Costs about **$0.01 per image.** The text description becomes searchable
- **Audio** → transcribe with Whisper. Costs **$0.006 per minute.** Podcasts, meetings, and calls become searchable text
- **Best practice:** convert everything to text first. This gets **90% of the value** with zero infrastructure changes. Build complex multimodal systems only when that last 10% matters

### RAGAS Evaluation — How to Know If Your System Actually Works

- **Precision above 80%** — are you retrieving the right documents? If this is low, you are feeding the LLM irrelevant information. Fix your chunking or add reranking
- **Recall above 75%** — are you retrieving all the relevant documents? If this is low, you are missing documents that contain the answer. Add hybrid search or multi-query retrieval
- **Faithfulness above 90%** — is the answer based only on the documents you provided? If this is low, **your system is making things up and presenting them as facts.** This is the most dangerous metric to fail. Fix by adding a grounding instruction and requiring citations
- **Relevance above 85%** — does the answer address what the user actually asked? If this is low, the model is going off-topic. Fix with a better prompt or a more capable model

One grounding instruction — "answer ONLY from the provided context. If the answer is not there, say I do not have that information" — drops hallucination from **50-80% to 5-15%.** Always include questions that have no answer in your test suite. If the model never says "I don't know," it is guessing on everything.

---

## Agents

### Patterns

- **ReAct** — the agent thinks about what to do, takes one action (like searching a database or calling an API), looks at the result, then decides what to do next. Repeats until the task is done. This is the right choice for **80% of agent tasks.** Simple to build, simple to debug. About **$0.15 per task**
- **Plan-Execute** — the agent writes a complete plan of all the steps before doing anything, then executes the plan step by step. Better for complex tasks that need **5 or more coordinated steps.** About **$0.30 per task**
- **Reflexion** — the agent does the task, evaluates its own work, and improves it. Like writing a draft, reviewing it, and rewriting. **Maximum 3 rounds.** If it is still bad after 3, the task description needs to change

The biggest finding from testing both patterns: **how you describe your tools matters 10× more** than whether you use ReAct or Plan-Execute.

### Tool Use

- **Tool descriptions are the most important thing.** A vague description like "gets order info" causes the agent to pick the wrong tool **15-30% of the time.** A specific description like "Look up order status, total, and shipping details. Use when a customer asks about their order. Returns JSON with id, status, and total" makes it pick correctly almost every time. This is the **cheapest quality improvement** for any agent
- **Limit to 15 tools per agent.** Beyond that, similar-sounding tools confuse the model. If you need more, create multiple specialized agents
- **The LLM decides which tool to use and what inputs to send. Your code executes the tool.** The LLM never runs anything directly — that is the safety boundary. Always validate inputs on your server before executing
- **Require human approval for sensitive actions** like processing refunds, deleting data, or deploying code

### Frameworks

- **LangGraph** — build your agent as a flowchart with states, conditions, and loops. Can save progress and resume after a crash. Can pause and wait for human approval. This is the **production standard for 90% of agent use cases**
- **CrewAI** — create multiple AI agents with specific roles (researcher, writer, reviewer) that work together. Good for quick prototypes. Less control over edge cases
- **AutoGen** — agents that discuss and debate with each other. Good for reducing AI bias through structured disagreement
- Pick one framework and commit to it. **Mixing frameworks creates debugging nightmares**

### Multi-Agent

- **Orchestrator-Worker** — one boss agent delegates tasks to specialist agents. The **most practical pattern** for production
- **Debate** — two agents argue opposite sides, a judge agent decides. **Surprisingly effective** at reducing AI decision bias
- **Peer Review** — agents review each other's work before submitting. Extra cost but catches mistakes
- Keep teams to **2-4 agents maximum.** Each agent needs 3-5 LLM calls. A team of 4 agents uses about 15-20 API calls per task

### Memory

- **Short-Term** — keep the last 10 messages in the conversation. **Always use this.** Without it, the agent forgets what you said 5 messages ago. When the limit is reached, oldest messages drop off
- **Long-Term** — summarize past conversations and store them. When the user returns, the agent knows their history. 50 messages compressed into 3 sentences saves **50× the token space**
- **Entity Memory** — remember facts about specific people or things ("this customer prefers email, is on the Pro plan, had a billing issue in March"). Like an automatic customer database
- **Token budget:** plan how much space each part gets — system instructions (1,000 tokens) + tool descriptions (1,000) + memory (3,000) + user question (1,000) + answer (2,000) = **8,000 total**

### Safety

- **Without a step limit,** an agent given an impossible task will retry the same action over and over forever. Set a maximum of **5-10 steps.** This is non-negotiable. We tested this — the difference is between a $0.15 task and a **$50 runaway bill**
- **Stuck detection:** if the agent gets the exact same result 3 times in a row, force it to try something different or stop
- **Risk tiers for actions:** searching a database = execute automatically. Processing a refund = wait for human approval. Deploying to production = always blocked without explicit approval
- **Never run AI-generated code on your own server.** Use a sandboxed environment that auto-destroys after each use. About $0.10 per hour

---

## Fine-Tuning

### Methods — Try in This Order

- **QLoRA** — compress the model to 4-bit precision first, then add small trainable layers. A 70 billion parameter model that normally needs 4 GPUs **(140 gigabytes)** fits on **1 GPU (35 gigabytes).** Quality stays at **97%.** This is always where you should start
- **LoRA** — add small trainable layers without compressing the model. Reaches **95-99% quality.** Needs more hardware than QLoRA. Try this only if QLoRA has a quality gap larger than 2%
- **Full Fine-Tuning** — update every single parameter in the model. Maximum quality but a 70 billion parameter model needs **4 GPUs (280 gigabytes).** Rarely justified unless you have a specific quality requirement that nothing else meets

**The golden rule:** a large model at 97% quality (quantized 70 billion) produces better output than a small model at 100% quality (full-precision 13 billion). Always pick the bigger model and compress it.

### Data

- **Quality matters more than quantity.** Research showed that 1,000 carefully written examples beat 52,000 automatically generated ones (LIMA paper). Every example needs to be correct, consistent, and representative
- **Every production bug becomes a new training example.** The failures your model makes in the real world are exactly what it needs to learn from. Over time, your training data grows from real experience
- **Data formats:** Alpaca (single question and answer), ShareGPT (multi-turn conversations), ChatML (the production standard — match whatever format your API uses)
- **Remove near-duplicate examples.** Balance your categories evenly. Have humans check **5%** of your data for errors

### Alignment — Teaching the Model to Behave

- **Step 1: Supervised Fine-Tuning (SFT)** — train the model on examples of good instruction-following. You need **1,000-5,000 examples.** This teaches the model to actually follow your instructions instead of ignoring them. **Never skip this step**
- **Step 2: Direct Preference Optimization (DPO)** — show the model pairs of responses and tell it which one is better. It learns to prefer the good style over the bad style. The modern standard for alignment. Needs **5,000-10,000 pairs** of [prompt, good response, bad response]
- **Alternative: KTO** — instead of full pairs, just needs thumbs up or thumbs down on individual responses. Much easier to collect this kind of feedback
- **Alternative: RLAIF** — instead of human judges, use GPT-4 to decide which response is better. Gets **80% of human quality at 10% of the cost.** $10 for 5,000 judgments instead of $2,000
- Doing DPO on a model that has not been through SFT first is like **polishing a brick** — the surface looks nice but the foundation is broken

### Synthetic Data — Creating Training Data Cheaply

- Start with **5 perfect examples** written by hand. These set the quality standard
- Ask GPT-4 to generate hundreds more examples in the same style
- Use an LLM judge to **score each example from 1 to 10.** Keep only those scoring 7 or above
- Have humans spot-check **5%** of the kept examples as a final quality gate
- Generate twice as many as you need, keep the top half
- Cost: **$0.01 per example** versus $2.00 per example from human writers

### Quantization — Making Big Models Fit on Small Hardware

- **Full Precision (FP16)** — no compression. A 70 billion parameter model needs 140 gigabytes. **Almost never used** in production because it is too expensive
- **8-bit (INT8)** — light compression. 99% quality. 70 gigabytes. Use when 4-bit has a measurable quality problem
- **4-bit (INT4)** — the **production sweet spot.** 97% quality. 35 gigabytes. One GPU instead of four. This is where most teams end up
- **AWQ** — a smarter version of 4-bit compression. Best quality at the same size. Use for GPU-based production serving
- **GGUF Q4_K_M** — a 4-bit format designed for running on CPUs and with Ollama on laptops. Best balance for local deployment
- **Never go below 4-bit.** Quality drops sharply at 3-bit — the savings are not worth the degradation

### Platforms

- **OpenAI Fine-Tuning** — upload your data, they handle everything. Simplest option. About $25 per million tokens
- **Together AI** — fine-tune open-source models for $5-10 per million tokens. You can download and own the resulting model
- **Self-Hosted (Axolotl + Unsloth)** — run everything on your own hardware. Your data never leaves your servers. Full control over every setting
- Managed platforms are cheaper when you process **under 1 million tokens per day.** Self-hosting is cheaper above that

---

## Orchestration

### Frameworks

- **Raw API calls** — just call the LLM API directly with no framework. Best for simple applications and for learning how things work. Maximum control, no extra dependencies
- **LangChain LCEL** — connect components with a pipe operator: prompt | model | parser. Gives you streaming, batching, retries, and fallbacks automatically. The older Chain classes are deprecated — use only LCEL
- **LangGraph** — build agents as state machines with conditions, loops, and checkpoints. Can save progress and resume after a crash. Can pause for human approval. This is the **production standard for 90% of agent use cases**
- **LlamaIndex** — specialized for search and retrieval applications. 150+ built-in connectors for data sources. What takes 800 lines in LangChain often takes **50 lines in LlamaIndex**
- **Semantic Kernel** — Microsoft's framework. Works in Python, C#, and Java. Makes sense if your stack is Azure and .NET
- **Haystack** — German-engineered framework that checks your pipeline connections at build time. Catches errors before runtime

### Anti-Patterns

- **Adding a framework before you need one** — build the simplest version first with raw API calls. Add a framework only when you hit a specific pain it solves
- **Calling framework functions directly everywhere** — wrap them in your own interfaces. When you need to switch frameworks, you change one file instead of hundreds
- **Using multiple frameworks together** — pick one and commit. Mixing LangChain and LlamaIndex and Haystack creates debugging problems that are not worth the marginal benefits
- **Chasing framework version updates** — pin your version. Test upgrades deliberately instead of updating blindly

---

## Evaluation and Testing

### Metrics

- **BERTScore** — compares the meaning of two texts using embeddings, not exact word matching. The best metric when you have a correct reference answer to compare against
- **LLM-as-Judge (score 1-10)** — ask a powerful model to rate the quality of a response. Agrees with human raters **80-90%** of the time. Costs **$0.002 per evaluation** versus $0.20 for a human rater
- **LLM-as-Judge (A versus B)** — show a powerful model two responses and ask which is better. Good for comparing different prompts or models. **Always randomize** which response is shown first because the model has a bias toward the first one
- **RAGAS** — four metrics specifically for Retrieval Augmented Generation systems: precision, recall, faithfulness, and relevance. Each one diagnoses a different problem and points to a specific fix

### Testing

- **Golden test suite:** a collection of 200+ questions with known correct answers. Every time you change a prompt, run the full suite. If any test fails, the deploy is blocked. **Every bug found in production becomes a new test case** — the suite grows from real experience
- **Adversarial testing:** use tools like garak (runs **100+ automated attack patterns**) and promptfoo (lets you write assertion-based tests) to find vulnerabilities before your users do. Run before every launch
- **Always include impossible questions.** If your model never says "I do not know," it is guessing on everything and you cannot trust any of its answers
- **A/B testing:** send 10% of traffic to the new prompt version, monitor the metrics for 24 hours, then roll out to everyone or roll back. Need at least **1,000 samples** for statistically meaningful results

### Observability

- **Log every LLM call:** the input, the output, which model was used, how many tokens it consumed, how long it took, and how much it cost. **Start on day one.** Retrofitting observability later is 10× harder because you need to change every call site
- **Platforms:** LangSmith (built for LangChain users) or LangFuse (open-source, you host it yourself, works with any framework)
- **Dashboards:** track the 50th, 95th, and 99th percentile of latency, the error rate, and the daily cost
- **Alerts:** page the on-call engineer when errors exceed 2%, when 95th percentile latency exceeds 5 seconds, or when daily cost exceeds 80% of the budget
- **Per-user tracking:** monitor token usage per user with rate limits and daily budgets to prevent one aggressive user from consuming the entire quota

---

## Infrastructure

### Serving — What Runs the Model

- **vLLM** — the **production standard** for self-hosted models. Uses a technique called PagedAttention that handles **2-4× more concurrent users** on the same hardware. Also includes continuous batching (the GPU never sits idle between requests) and speculative decoding (a small fast model guesses ahead, the big model verifies in bulk)
- **TGI (Text Generation Inference)** — a Docker-friendly serving engine from HuggingFace. Simpler to set up than vLLM
- **TensorRT-LLM** — NVIDIA's maximum-performance engine. **30-50% faster** than vLLM but more complex to set up and locked to NVIDIA hardware
- **Ollama** — run models locally with one command. 50+ models available. Great for development and testing. **Not suitable for production**
- **llama.cpp** — run models on CPU without a GPU. Useful for edge devices and laptops

### Gateway and Routing

- **LiteLLM** — a universal proxy that sits in front of **100+ LLM providers.** Switch from OpenAI to Anthropic by changing one configuration string. Handles fallbacks, load balancing, and budget tracking automatically. Every production application should have a gateway
- **Fallback chain** — configure a primary provider, a secondary, and a local backup. If the primary goes down, traffic automatically shifts. Health check every **30 seconds** to detect outages
- **Model routing** — 70% of real production queries are simple ("what are your business hours?"). Route those to the cheap model. Only send complex queries to the expensive model. This saves **60-70%.** At 100,000 queries per day, that is **over $1,000 per day saved**
- **Cascading** — try the cheap model first. If its response seems uncertain (hedging words, low confidence), automatically escalate to the expensive model
- **Domain override** — some domains like medical or legal cannot tolerate quality drops. Hard-code these to always use the best available model

### Deployment

- **Server-Sent Events streaming** — instead of waiting for the entire response before showing anything, push each word to the user as the model generates it. First word appears in **under 500 milliseconds** versus a 2-3 second blank screen. Users perceive the application as **3-5× faster** even though the total generation time is the same
- **Docker** — use the nvidia/cuda base image for GPU access. Mount model weights as a volume instead of baking them into the image (model files are too large for Docker images)
- **Kubernetes** — autoscale based on **queue length,** not CPU utilization. LLM workloads are GPU-bound. CPU sits at 5% while the GPU is maxed out. Queue length is the real signal

### Cloud Platforms

- **AWS Bedrock** — for teams already on AWS. Enterprise compliance built in
- **Azure OpenAI** — for teams already on Azure. Your data stays in your chosen region
- **Google Cloud Vertex** — for teams already on Google Cloud. Access to Gemini and open-source models
- **Groq** — the fastest API available. **10-50× faster** than standard providers. Limited model selection
- **Together AI** — cheapest option for open-source models. You can download and own the fine-tuned result
- Managed platforms are cheaper when you process **under 1 million tokens per day.** Self-hosting is cheaper above that

---

## Safety and Governance

### Protection

- **PII pipeline** — use Microsoft Presidio (detects **30+ types** of personal information) to find and replace every email, phone number, SSN, and credit card number with a placeholder before the text reaches the LLM. The LLM sees "[EMAIL_0]" instead of the real address. After the response, swap the real values back in. The LLM **never sees real personal data**
- **OpenAI Moderation API** — a **free** tool that checks text for toxicity, violence, self-harm, and other harmful content. Always enable this as the first checkpoint on every application
- **Canary tokens** — plant a secret string inside your system prompt and scan every response for it. If the string ever appears in a response, you know your prompt has been extracted. **Zero cost** early warning system
- **Dual-LLM architecture** — one model holds all the rules and makes decisions (privileged). A separate model sees only the user's message and generates text (quarantined). The generation model never has access to the rules. **Most secure architecture.** Used in banking and healthcare. Costs 2× more

### Hallucination Defense

- **Grounding instruction** — add one line to your prompt: "answer ONLY from the provided context." This is the **number one defense** against hallucination. Drops fabrication rates from 50%+ to under 10%
- **Citations** — require the model to cite [Source: document name, page number] for every claim. Users can verify the answer, and the model becomes more careful when it has to point to where it found the information
- **Confidence scoring** — ask the model to rate its own certainty from 1 to 10. When confidence is low, add a disclaimer or route to a human instead of serving an uncertain answer
- **Abstention training** — teach the model that saying "I do not know" is better than guessing. If your model never abstains, **it is guessing on everything** and you cannot trust any individual answer

### Guardrails

- **Guardrails AI** — validates the model's output against your rules and automatically retries if the output violates them. Good for enforcing structured output formats
- **NeMo Guardrails** — defines what topics the bot is allowed to discuss and what it must refuse. Uses a special language called Colang to set conversation boundaries
- **LLM Guard** — drop-in security scanners for both input and output. Checks for injection attacks, personal information leaks, and toxic content
- Combine LLM Guard for security and NeMo for conversation control. All guardrail systems add **50-200 milliseconds** of latency — budget for this in your response time targets

### Compliance

- **EU AI Act** — requires risk assessment, bias testing, and transparency for high-risk AI systems. **Mandatory** for applications deployed in the European Union
- **GDPR** — requires minimizing personal data collection, providing the right to deletion, and obtaining informed consent. Auto-delete logs containing personal data after **30 days**
- **HIPAA** — strict rules for handling protected health information in the United States. Self-hosting the model is typically required so health data never leaves your servers
- **Model cards** — document what every deployed model can do, what it was trained on, its known limitations, and ethical considerations. Version every prompt in git. A/B test every change with at least 1,000 samples

---

## Multimodal

- **GPT-4o Vision** — the model can look at images and extract information. The detail setting controls quality and cost: low detail uses **85 tokens** per image, high detail uses **1,000+ tokens.** That is a **10× cost difference.** Always start with low
- **Claude Vision** — particularly strong on dense text documents and long screenshots
- **Gemini Vision** — can process multiple images in a single request and has the largest context window
- **LLaVA** — an open-source vision model you can run on your own hardware. Nothing leaves your server
- **Whisper** — converts speech to text in **100+ languages.** The API costs $0.006 per minute. Self-hosting is free
- **Text-to-Speech** — OpenAI TTS ($15 per million characters, 6 voices). ElevenLabs (best quality, can clone a voice from 30 seconds of audio)
- **CLIP and Jina-CLIP** — put text and images into the same number space so you can search images with text queries and vice versa
- **Voice agent pipeline** — user speaks → Whisper converts to text → LLM generates answer → text-to-speech reads it out. Target: **under 1 second** total latency
- **Production rule:** before building complex multimodal pipelines, try converting everything to text first (tables to markdown, images to descriptions, audio to transcripts). This gets **90% of the value with zero infrastructure changes**

---

## Architecture

### Patterns

- **Gateway (LiteLLM)** — a single entry point for all LLM providers. Switching from one provider to another requires changing **one configuration string** — no code changes
- **Semantic cache** — if someone asks "what is your refund policy?" and five minutes later someone asks "how do returns work?", the cache recognizes these mean the same thing and returns the saved answer. Hit rate: **30-40%.** Each hit costs zero and returns in 10 milliseconds instead of 1-2 seconds
- **Model routing** — classify each incoming query as simple or complex. Simple queries go to the cheap model, complex to the expensive one. Saves **60-70%** because 70% of real traffic is simple
- **Compound AI** — instead of one big expensive model doing everything, build separate specialized components: a classifier, a retriever, a generator, guardrails, and a cache. Each component can be tested, replaced, and scaled independently. **80-90% cheaper** than a monolith
- **MapReduce** — split large documents into pieces, process each piece in parallel with the cheap model, then combine all results with the smart model. Handles unlimited document sizes
- **Iterative refinement** — generate a response, get a critique, rewrite based on the critique. Quality improves about **+2 points per round** on a 1-10 scale. Three rounds is the sweet spot
- **Fallback chain** — primary provider → secondary → local model → graceful error message. Timeout of **2-3 seconds** before switching to the next provider

### Design Rules

- **Async everywhere** — LLM calls take 1-3 seconds. If your code blocks while waiting, you can serve about 5 users at a time. With async (non-blocking) calls, you can serve **500.** This is non-negotiable
- **Circuit breaker** — if a provider fails 5 times in a row, stop trying and route to the fallback. Periodically test if the provider has recovered. Prevents cascading failures
- **Token budget** — plan how much context space each component gets. When conversation history grows too long, summarize older messages to free up space
- **Idempotency** — if a network timeout causes a retry, the action should not execute twice. Use idempotency keys on every write operation

### Data Architecture

- **Embedding pipeline** — extract text from documents → break into chunks → remove duplicate chunks (hash-based deduplication saves **10-30%** on embedding costs) → convert to embeddings → store with metadata
- **Metadata on every chunk** — always attach the source, date, and document type. Filtering by metadata **before** running vector search dramatically improves results
- **Incremental updates** — when a document changes, only re-process that document instead of re-embedding everything. Track the last modified timestamp
- **Zero-downtime re-indexing** — when you need to change your embedding model (which means re-processing everything), build the new index alongside the old one and swap them atomically. Users never see downtime

---

## Advanced and Emerging

- **Model Context Protocol (MCP)** — a standard way to connect any tool to any LLM, like USB-C for AI. Build one server and it works with Claude, GPT, Gemini, and local models. Before MCP: 50 custom integrations. With MCP: one standard protocol. FastMCP lets you build a server in **20 lines of code**
- **Compound AI systems** — multiple specialized components working together instead of one big model. Each component has a single responsibility. **80-90% cheaper** than a monolith. Each piece is independently testable and replaceable
- **GraphRAG** — extract entities and relationships from your documents and build a knowledge graph. This lets you answer questions that require following chains across multiple documents. Regular search finds individual pieces. Graph traversal follows the whole chain. Worth building when **20% or more** of your queries need cross-document connections
- **Knowledge distillation** — use a powerful expensive model (the teacher) to label your data, then fine-tune a small cheap model (the student) on those labels. The student achieves **85-95% of the teacher's quality** at **1/30th the cost.** Combined with quantization: **100× cheaper** than the original teacher
- **Mixture of Experts (MoE)** — models like Mixtral have 8 expert sub-networks but only activate 2 of them for each word. Total knowledge of a 47 billion parameter model, but the speed and cost of a 13 billion parameter model
- **Context compression (LLMLingua)** — automatically removes filler words and redundant phrases from text before feeding it to the LLM. Shrinks 10,000 words to 3,000 while retaining **90% of the quality.** Use when your text barely exceeds the context window
- **Local inference** — Ollama (one command to download and run any model), llama.cpp (runs on CPU without a GPU), MLX (fastest on Apple Silicon). Good for development and privacy-sensitive work. Deploy to the cloud for production
- **LLMOps** — version prompts in git → run the golden test suite → deploy to 10% of users for 24 hours → monitor → roll out to everyone or roll back instantly. **Every bug becomes a new test case.** Treat prompt changes with the same discipline as code changes

---

---

## The 58 projects

Every project ships with **`{project-name}.py`** · **`README.md`** · **`requirements.txt`** · **`Dockerfile`** · **`docker-compose.yml`** (application + Prometheus + Grafana) · **`grafana/`** dashboard

---

### 🔬 Benchmarks

- **`01` Tokenizer Shootout** `no API key needed`
  - Fed 27 real texts in 11 languages through both tokenizers
  - Chinese produced **2.3× more tokens** than English for the same meaning
  - But switching from GPT-4 to GPT-4o-mini saves **100× more money** than optimizing for any language
  - Language barely matters compared to picking the right model

- **`02` Temperature Playground**
  - Sent the same prompt at 5 temperatures (0, 0.3, 0.7, 1.0, 1.5) — three times each
  - At 0: identical answers every time. At 0.7: creative but coherent. Above 1.2: **unusable output**
  - Tested top_p separately to understand what it actually controls
  - Production defaults: **0 for factual tasks, 0.3-0.7 for creative, never above 1.2**

- **`03` Context Window Stress Test**
  - Hid a secret fact at 9 different positions inside 20-200 lines of filler text
  - The fact placed at the **middle (40-60% position) was missed the most**
  - Start and end positions were reliable. Middle recall got worse as context grew
  - Proved the "lost in the middle" problem with measured data

- **`04` Model Family Comparison**
  - Ran 15 questions (factual, reasoning, classification) on both GPT-4o-mini and GPT-4o
  - Mini **matched perfectly on factual questions and classification**
  - GPT-4o only pulled ahead on multi-step math and logic
  - Most teams are paying **15× more** for zero benefit on 70% of their traffic

- **`07` Zero-Shot versus Few-Shot versus Dynamic Few-Shot**
  - Classified 30 real customer support messages three different ways
  - Zero-shot: **85-95% accuracy** on clear tasks
  - Few-shot: **+5-15% accuracy** but **3-5× more token cost**
  - Dynamic few-shot (picks best-matching examples per query): **best accuracy per dollar**

- **`08` Chain-of-Thought versus Direct Answer**
  - Tested 13 questions across math, logic, factual, and classification
  - "Think step by step" added **+15-25% accuracy on math and logic**
  - On simple classification: **doubled the cost and changed nothing**
  - Conclusion: use chain-of-thought only for reasoning tasks

- **`09` Structured Output Benchmark**
  - Extracted contact information from 8 texts using raw text, JSON mode, and XML tags
  - Raw text: **20-40% of responses could not be parsed by code**
  - JSON mode: **100% parseable every time**
  - XML tags: worked with every model tested

- **`10` Prompt Chaining Benchmark**
  - Analyzed an article three ways: one big prompt, a 4-step sequential chain, a 4-step parallel chain
  - Parallel chain = **same quality as sequential but 2-3× faster**
  - Using GPT-4 for the thinking step and mini for formatting saved **60%**

- **`11` Self-Consistency Benchmark**
  - Asked 10 trick questions 1 time, then 3 times, then 5 times — took the majority vote each time
  - **+10-15% accuracy** on hard questions with 5 calls
  - Simple questions were **already correct on the first call** — extra calls added nothing
  - 5× cost is only justified for high-stakes decisions

- **`12` System Prompt Position Test**
  - Placed a secret rule at the top, middle, and bottom of a 30-line system prompt
  - Attacked the rule 5 times per position
  - **Middle position had the lowest compliance rate.** Top had the highest
  - Confirmed that LLMs pay more attention to the start and end of their instructions

- **`13` Meta-Prompting**
  - Wrote a sentiment classification prompt by hand, then asked GPT-4o-mini to write one
  - Tested both on 10 product reviews
  - The AI-written prompt **scored higher** because it handled sarcasm and mixed reviews
  - GPT-4 writes the prompt once **(costs $0.01),** mini runs it forever **(costs $0.0001 per call)**

- **`16` Chunking Strategy Benchmark**
  - Same documents, same questions, 4 different chunking strategies
  - Accuracy swung **20-30% based on chunking alone**
  - Fixed-size chunking was the **worst performer every time**
  - This single decision matters more than which prompt you write for the LLM

- **`17` Dense versus BM25 versus Hybrid Search**
  - Built a 10-document corpus and ran 8 queries (keyword-heavy, meaning-heavy, and mixed)
  - Dense search caught meaning matches but missed keyword matches
  - BM25 caught keyword matches but missed meaning matches
  - **Hybrid search with Reciprocal Rank Fusion caught everything**

- **`18` Multi-Query Retrieval**
  - Rephrased each question 3 different ways, searched with each version, combined all results
  - Found **15-25% more relevant documents** that the original wording had missed
  - Only 10 lines of code for a significant improvement

- **`20` Embedding Model Shootout**
  - Embedded 8 documents with both text-embedding-3-small and text-embedding-3-large
  - Ran 5 retrieval queries against each
  - The small model was **good enough for nearly every query**
  - The large model cost **6× more** for only **2-5% better accuracy**

- **`24` Tool Description Quality Impact**
  - Gave an agent the same 4 tools with two sets of descriptions: vague and specific
  - Ran 5 function-calling tasks with each set
  - Specific descriptions improved correct tool selection by **15-30%**
  - **The cheapest quality improvement you can make** to any agent system

- **`29` LLM-as-Judge**
  - Had a human rate 8 responses on a 1-5 scale, then asked GPT-4o-mini to rate the same ones
  - Agreement within 1 point: **80-90%**
  - Cost per evaluation: **$0.002 with AI versus $0.20 with a human**
  - For 10,000 evaluations: **$20 versus $2,000**

- **`36` Prompt A/B Tester**
  - Ran two classification prompts against 15 real test cases
  - Tracked accuracy and token cost for each variant
  - Declared a **statistical winner based on the data**
  - This is a reusable framework for any prompt comparison. Re-run monthly because model updates change results

---

### 🏗️ Architecture

- **`14` Jinja2 Prompt Templates**
  - Built one template with variables, conditions, and loops
  - Rendered 3 completely different prompts from the same template (formal billing, casual tech support, enterprise sales)
  - This is how you go from **1 prompt to 10,000 unique prompts** at scale
  - Store templates in git. Template inheritance prevents accidental deletion of safety rules

- **`23` ReAct versus Plan-Execute Agents**
  - Ran 5 tasks through both agent patterns: simple lookups, multi-step calculations, impossible requests
  - Measured steps taken, tokens consumed, and completion rate
  - The biggest finding was not about the patterns — **tool descriptions matter 10× more** than which agent architecture you use

- **`25` Model Routing**
  - Built a simple classifier (query length + keywords) that routes 16 real queries
  - Simple queries go to GPT-4o-mini, complex ones go to GPT-4o
  - Measured the exact dollar amounts. Savings: **60-70%**
  - At 100,000 queries per day: **over $1,000 per day saved** from one architectural decision

- **`26` Compound AI versus Monolith**
  - Ran 8 queries through all-GPT-4o (monolith) versus a classifier **($0.0001 per call)** plus routed generators (compound)
  - The compound system saved **70-90%**
  - Quality was **identical** on simple queries because the cheap model handles them perfectly

- **`27` PII Redaction Pipeline**
  - Fed 3 messages containing real emails, SSNs, phone numbers, and credit card numbers
  - The pipeline replaced every piece of personal data with a placeholder before the LLM saw it
  - After the LLM responded using placeholders, real values were swapped back in
  - **Audit check confirmed: zero personal data reached the LLM at any point**

- **`28` Semantic Cache**
  - Sent 13 queries where some are the same question in different words
  - "What is your refund policy?" and "How do returns work?" hit the **same cached entry**
  - Measured hit rate: **30-40%**
  - Each cache hit: **zero API cost, 10 milliseconds response** instead of 1-2 seconds

- **`30` Retrieval Augmented Generation in 30 Lines**
  - Embedded 4 documents, built a search function, and wrote a grounded answer generator
  - Complete working pipeline in **30 lines of actual logic**
  - Asked 5 questions including one that is NOT in the documents
  - The model **correctly said "I don't have that information"** instead of making something up

- **`34` MapReduce Summarization**
  - Processed a 10-chapter document in two stages
  - MAP: GPT-4o-mini summarized each chapter **in parallel** (fast and cheap)
  - REDUCE: GPT-4o combined all 10 summaries into one executive summary (quality matters for the final output)
  - Handles **unlimited document size** at optimal cost

- **`35` Iterative Refinement**
  - Generated a professional email, scored it on a 1-10 scale
  - Got a critique, rewrote based on the feedback, scored again
  - Quality climbed approximately **+2 points per round**
  - **Round 3 was the sweet spot.** After that, improvement flattened. Costs 3× a single generation

- **`41` Embedding Pipeline with Deduplication**
  - Processed 10 documents where 3 were exact duplicates appearing in different sources
  - The pipeline hashed each chunk before embedding — all duplicates caught and skipped
  - **Saved 30% on embedding API calls**
  - Full production pipeline: extract → chunk → deduplicate → embed → attach metadata

- **`44` Model Router**
  - Built an auto-classifier that categorizes incoming queries and routes to the appropriate model
  - The classifier itself costs **$0.0001 per call** — essentially free
  - Total savings from routing: **60-70%**
  - The classifier **pays for itself thousands of times over** in a single day

---

### 💥 Failure Analysis

- **`03` Lost in the Middle**
  - Placed important facts at 9 different positions in a long context
  - Facts at the **40-60% position were recalled least reliably**
  - Fix: put critical information at the **start and end** of the context
  - Never bury important data in the middle of a long prompt

- **`15` Injection Attack Lab**
  - Fired 12 real attack types at a chatbot: direct override, social engineering, persona swap, multilingual tricks, delimiter escape
  - Without any defense: **30-60% of attacks successfully breached** the system
  - Added 4 defense layers (delimiters → sanitize → hierarchy → output scan)
  - With all 4 layers: **under 5% breach rate.** Each layer catches what the previous one misses

- **`19` Hallucination Trap**
  - Gave the model a small product catalog and asked 12 questions
  - 8 of the questions were **deliberately unanswerable** (the information is not in the catalog)
  - Without a grounding instruction: the model **confidently made up answers over 50% of the time**
  - Added one line to the prompt ("answer ONLY from the provided context"): **dropped to under 10%**

- **`21` Bias Audit**
  - Sent the same career advice prompt but swapped in 12 different names across 4 demographic groups
  - Measured whether the model uses more "leadership" language for some names and more "support" language for others
  - **Found measurable differences** in the language used across groups
  - The EU AI Act requires this kind of testing for high-risk AI systems. Flag any disparity above **5%**

- **`51` Stale Data Problem** `no API key needed`
  - Put two versions of a document in the knowledge base — an old one saying "$29 per month" and a current one saying "$49 per month"
  - Without freshness filtering, the search engine might return the **old document with the wrong price**
  - Fix: attach date metadata to every chunk and **filter by freshness before searching**

- **`52` Agent Infinite Loops** `no API key needed`
  - Gave agents 3 tasks that are impossible to complete (orders that do not exist)
  - Without a step limit: the agent searched for the same thing **over and over forever.** $50 bill for nothing
  - With a maximum of 5 steps and stuck detection (same result 3 times = stop): **$0.15 and a graceful failure message**

- **`53` Context Window Overflow** `no API key needed`
  - Built growing contexts from 500 to 10,000 characters with a secret hidden in the middle
  - As the context grew, the **middle became a dead zone** where information was effectively invisible
  - Retrieving only the relevant pieces (Retrieval Augmented Generation) **works better than stuffing everything into the context**

- **`54` Chunking Failure Modes** `no API key needed`
  - One document about refund timelines. One question about international bank transfers
  - Fixed-size chunking **split the answer across two chunks.** The model saw half and gave the wrong answer
  - Paragraph-aware chunking **kept the full answer together.** The model found it and gave the right answer
  - **Same document, same question. Only the chunking strategy was different**

- **`56` Injection Firewall** `no API key needed`
  - Ran 8 common injection attack patterns through regex defense layers
  - Generated a **per-attack pass/fail report** showing which patterns are caught by fast regex and which need the slower LLM safety check
  - **Takes about 30 minutes to implement.** Blocks the majority of common attacks

---

### 💰 Cost Analysis

- **`01` Token Costs Across Languages** `no API key needed`
  - Priced 27 texts across **11 languages, 4 models, and 4 daily volumes** (1,000 to 1,000,000)
  - Complete cost table for any workload and language combination
  - The model you choose makes **100× more difference** than which language your users speak

- **`05` Stop Sequence Savings**
  - Ran the same prompts with and without stop sequences
  - Without: the model rambled past the requested 3 items and gave 10
  - With stop sequences: the model stopped cleanly at 3
  - **20-50% fewer output tokens** from adding one parameter

- **`06` Cost Scenario Calculator** `no API key needed`
  - Priced 5 real-world scenarios (simple query, support ticket, RAG with context, system prompt, code review) across **6 models and 4 daily volumes**
  - The system prompt and the RAG context are the **biggest hidden cost drivers** — not the user's question

- **`25` Routing Savings**
  - Measured exact dollar difference between sending everything to GPT-4o versus routing with a classifier
  - Savings: **60-70%**
  - At 100,000 queries per day: **over $1,000 per day saved** from one architectural decision

- **`26` Compound System Savings**
  - Compared one expensive model doing everything versus specialized components working together
  - Savings: **70-90%**
  - The classifier that routes queries costs **$0.0001 per call** — it pays for itself in the first second of operation

- **`37` Cost Anomaly Detection**
  - Simulated 30 API calls with 3 hidden cost spikes (someone sent extremely long prompts)
  - The detector maintains a rolling average and flags anything above **2 standard deviations**
  - **Every spike was caught.** In production, these alerts feed into PagerDuty or Slack

- **`40` Quantization Impact** `no API key needed`
  - Calculated the hardware requirements for a 70 billion parameter model at each compression level
  - Full precision: **140 gigabytes (4 GPUs)**
  - 4-bit quantized: **35 gigabytes (1 GPU)**
  - Quality drops **only 3%.** One architectural decision eliminates 3 expensive GPUs

- **`47` RAG versus Fine-Tuning versus Zero-Shot Total Cost** `no API key needed`
  - Computed total cost of ownership at 4 daily volumes
  - Below **10,000 queries per day: zero-shot wins** because there is no setup cost
  - Above **100,000 queries per day: fine-tuning always wins** because the upfront investment gets spread across millions of calls

- **`48` Cache Return on Investment** `no API key needed`
  - Streamed 12 queries including repeats and paraphrases
  - Exact-match cache: **20-30% hit rate.** Semantic cache: **30-50% hit rate**
  - At 100,000 queries per day with a 35% hit rate: **35,000 queries served for free every day**

- **`49` Platform Cost Comparison** `no API key needed`
  - Priced the same workload across **GPT-4o, GPT-4o-mini, Claude Sonnet, Claude Haiku, Groq, and Together AI** at 4 daily volumes
  - One table that answers **"which platform is cheapest for my specific workload"**

- **`55` LoRA versus Full Fine-Tuning Hardware** `no API key needed`
  - Calculated memory requirements for 3 model sizes across 3 training methods
  - 70 billion parameters with QLoRA: **49 gigabytes (1 GPU)**
  - 70 billion parameters with full fine-tuning: **280 gigabytes (4 GPUs)**
  - Always start with QLoRA. Full fine-tuning only if the quality difference is worth 3 extra GPUs

---

### 🔧 Novel Tools

- **`32` Synthetic Data Generator**
  - Wrote 5 high-quality seed examples by hand
  - GPT-4o-mini generated 15+ more examples in the same style
  - An LLM judge scored each one from 1 to 10. Kept only those scoring 7 or above
  - Humans checked 5% of the final set as a last quality gate
  - **$0.01 per example** versus $2.00 per example from human writers

- **`36` Prompt A/B Testing Framework**
  - A reusable tool: feed in **any 2 prompt variants plus any test set**
  - Get back accuracy and cost for each variant
  - **A statistical winner is declared automatically**
  - Use before every prompt change in production. Run again every month

- **`37` Cost Anomaly Alerting**
  - Tracks every API call cost in real time
  - Maintains a **rolling average plus a threshold at 2 standard deviations**
  - Fires an alert the moment any call exceeds the threshold
  - Catches runaway costs from unexpected long prompts **before they become $500 surprises**

- **`38` Direct Preference Optimization Pair Generator**
  - Generates the exact training data format that preference alignment needs
  - For each prompt: generates 2 responses at different settings. An LLM judge picks the better one
  - Outputs: [prompt, winning response, losing response]
  - **$0.002 per pair.** For 5,000 training pairs: **$10 instead of $2,000** with human annotators

- **`42` LLMOps Deployment Gate**
  - Runs the golden test suite on every prompt change
  - **If tests pass, the deploy is allowed. If any test fails, the deploy is blocked**
  - Tested with 3 prompt versions: version 1 passed, version 2 passed and deployed, version 3 (deliberately bad) **was caught and blocked**
  - Every bad prompt is caught before any user sees it

- **`57` Knowledge Graph Builder** `no API key needed`
  - Extracted entities and relationships from 4 documents
  - Built a graph: Alice is CEO → Bob reports to Alice → Carol reports to Bob → Dave reports to Carol
  - Asked: "Who does Dave ultimately report to?"
  - **Regular search finds only one connection.** The graph follows the full chain: **Dave → Carol → Bob → Alice → Board**

- **`58` Model Context Protocol Server Generator** `no API key needed`
  - Defined 3 tools in a simple list and generated a complete **working server in 20 lines of code**
  - Model Context Protocol is the emerging standard for connecting any tool to any LLM
  - Build the server once and it works with **Claude, GPT, Gemini, and local models**

---

### ⚡ Quick Demos

- **`30` Retrieval Augmented Generation in 30 Lines**
  - Embed 4 documents → search by meaning → generate a grounded answer
  - **Complete working pipeline in 30 lines of logic**
  - Asked a question that is NOT in the documents — the model correctly said "I don't have that information"

- **`33` Streaming versus Blocking**
  - Sent the same question twice: once waiting for the full response, once streaming word by word
  - Without streaming: **2-3 seconds of blank screen** before anything appeared
  - With streaming: the first word appeared in **200 milliseconds**
  - One setting change. Same total time. Users perceive the application as **3-5× faster**

- **`43` Agent Reasoning Trace**
  - Gave an agent a real task: "look up this order, calculate 15% tax, tell me the total"
  - Printed every single step: **what it thought, which tool it chose, what result it got back, what it decided next**
  - This is how you debug agents in production — reading the full reasoning chain instead of guessing

- **`45` Voice of Customer Analysis**
  - Fed 10 customer reviews into a single API call
  - Got back structured data: **sentiment, key topics, and recommended action items** for each review
  - One call replaces hours of manual reading. Cost: approximately **$0.001 per review**

- **`46` Knowledge Distillation**
  - GPT-4o-mini classified 20 customer queries into categories (billing, technical, general)
  - Output formatted as **JSONL — the exact format you upload to the fine-tuning API**
  - After fine-tuning, the student model handles the same task at **1/30th the cost** of the teacher

- **`50` Content Safety Filter** `no API key needed`
  - Three defense layers running in order from fastest to slowest
  - PII regex catches social security numbers and credit cards in **microseconds**
  - Injection regex catches "ignore all instructions" in **microseconds**
  - LLM safety check catches subtle threats in **200 milliseconds**
  - Most threats are caught **before they ever reach the expensive LLM layer**

---

## Study Modules

11 modules. Each has an **interactive JSX lesson,** a **printable PDF,** a **runnable Jupyter lab,** and an **architecture diagram.** Plus **pocket revision cards** and **100+ interview questions and answers.**

- **01 Prompt Engineering** — techniques, system prompt design, structured output, chaining patterns, **injection defense with 4 layers**
- **02 Retrieval Augmented Generation** — chunking strategies, embeddings, **hybrid search,** reranking, multi-query retrieval, **RAGAS evaluation,** hallucination defense
- **03 Agents** — ReAct, Plan-Execute, **function calling,** tool descriptions, multi-agent patterns, memory types, **safety controls**
- **04 Fine-Tuning** — **QLoRA** and LoRA and full, data quality, **supervised fine-tuning → preference optimization pipeline,** synthetic data generation, quantization
- **05 Orchestration** — LangChain LCEL, **LangGraph,** LlamaIndex, framework selection, **anti-patterns to avoid**
- **06 Evaluation and Testing** — **LLM-as-judge,** golden test suites, adversarial testing, **observability from day one**
- **07 Infrastructure** — **vLLM,** LiteLLM gateway, model routing, streaming, quantized serving, cloud platforms
- **08 Safety and Governance** — **PII redaction pipeline,** injection defense, bias testing, guardrails, **EU AI Act, GDPR, HIPAA**
- **09 Multimodal** — vision **(10× cost difference between detail levels),** Whisper, CLIP, **convert-to-text-first approach**
- **10 Architecture** — gateway pattern, **semantic cache,** compound AI, routing, **async is non-negotiable,** circuit breakers
- **11 Advanced and Emerging** — **Model Context Protocol,** GraphRAG, distillation, Mixture of Experts, **LLMOps pipeline,** local inference

---

## Stack

**`structlog`** · **`prometheus_client`** · **`pytest`** · **`Docker`** · **`Prometheus`** · **`Grafana`** · **`tiktoken`** · **`Jinja2`** · **`OpenAI SDK`**

**No API key needed:** `01` `06` `40` `47` `48` `49` `50` `51` `52` `53` `54` `55` `56` `57` `58`
