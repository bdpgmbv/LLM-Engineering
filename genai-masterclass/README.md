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

- **Zero-Shot**
  - Give the model one instruction with zero examples. The simplest and cheapest way to use an LLM
  - Works **85-92%** of the time on clear, well-defined tasks
  - Costs about **$0.001 per call**
  - Always start here. If accuracy is above 90%, ship it. Do not add complexity unless the numbers demand it
  - A smarter model with zero-shot **always beats** a weaker model with fancy prompting techniques

- **Few-Shot**
  - Show the model 2-3 completed examples of good output before asking your question
  - The model learns the format, tone, and structure from the examples
  - Improves accuracy by **5-15%** but costs **3-5× more tokens** because the examples take up space
  - Put the most similar example **last** — the model pays more attention to what it just read
  - Only use when zero-shot accuracy drops below 90%. If you have 500+ labeled examples, fine-tune instead

- **Dynamic Few-Shot**
  - Instead of showing the same 3 examples every time, pick the 3 most relevant ones for each question
  - A billing question gets billing examples. A technical question gets technical examples
  - **10-15% more accurate** than using fixed examples, at similar cost
  - Requires a small search step to find matching examples, but the quality improvement is worth it

- **Chain-of-Thought**
  - Tell the model to think step by step and show its reasoning before giving the final answer
  - On math and logic problems: **+15-25% accuracy** because the model catches mistakes in its own reasoning
  - On simple classification ("is this billing or technical?"): **doubles the cost and adds zero benefit**
  - The rule: route by task type. Use chain-of-thought only where reasoning is genuinely needed

- **Self-Consistency**
  - Ask the same question 5 times and take the most popular answer as the final response
  - Like getting a second opinion from 5 doctors and going with the majority
  - Boosts accuracy by **10-15%** on difficult questions. Costs **5× more**
  - Smart version: start with 1 call. Only add 4 more if the first answer seems uncertain. Average cost drops to 1.8×
  - Only justified for decisions where being wrong has real consequences — medical, legal, financial

- **Tree-of-Thought**
  - Instead of generating one answer, generate 3 completely different approaches
  - Force genuinely different angles — for example: the cheapest option, the fastest option, the highest quality option
  - Then evaluate all 3 and pick the best one
  - Good for **architecture decisions, strategy, and planning** where there is no single right answer
  - Keep to **3-5 paths maximum.** Beyond that, the returns diminish rapidly

### System Prompt

- **4-Section Structure**
  - Every production system prompt should have 4 sections in this order: who the AI is (persona), what it must never do (constraints), how to format answers (format), what to do in edge cases (guardrails)
  - Without this structure, the model follows some instructions and ignores others unpredictably

- **Rule Placement**
  - Put your most important rules at the **start and end** of the prompt
  - The model pays less attention to rules buried in the middle
  - We tested this in project 12 — rules placed in the middle were violated the most often

- **Length Limit**
  - Keep system prompts **under 2,000 words**
  - Longer prompts sound more thorough but the model actually starts forgetting parts of them

- **Security**
  - Never put secrets, internal rules, or discount codes in the system prompt
  - Attackers can extract prompt contents **30-60% of the time** without any defense
  - Treat everything in the prompt as if it will be seen by the public

- **Version Control**
  - Store every prompt in git with code review
  - Treat prompt changes the same way you treat code changes — review, test, deploy carefully
  - Deploy pipeline: development → testing → staging → send to 10% of users → full rollout

### Structured Output

- **XML Tags**
  - Tell the model to wrap its answer in tags like `<name>...</name>`
  - Works with **any model from any provider.** The most portable option
  - Easy to parse with simple code. Claude follows XML particularly well

- **JSON Mode**
  - A setting in the API that guarantees the response is valid JSON
  - The JSON will **always be parseable,** but there is no guarantee it contains the fields you asked for
  - Available on API models only

- **instructor + Pydantic**
  - Define the exact shape of the output you want as a Python class
  - The library automatically retries if the model returns the wrong shape
  - This is the **industry standard** for production systems that need reliable structured data

- **Outlines**
  - Controls which tokens the model is allowed to generate, character by character
  - **Guarantees** the output matches your exact format with zero retries
  - Only works with models running on your own hardware. The fastest method when available

### Chaining

- **Sequential**
  - Break a complex task into steps that run one after another
  - Each step uses the output from the previous one (summarize → extract topics → classify sentiment)
  - Keep to **2-4 steps maximum** because errors build up with each step

- **Parallel**
  - Run independent steps at the same time instead of waiting for each one to finish
  - Same cost as sequential, but **2-3× faster.** Users notice the speed difference
  - Only works when steps do not depend on each other

- **Map-Reduce**
  - For documents too big to process in one call
  - Split the document into pieces, process each piece separately (the map step), then combine all results into one final output (the reduce step)
  - Handles **unlimited document sizes**

- **Mixed-Model**
  - Use the expensive model only for the step that actually needs intelligence
  - Use the cheap model for everything else like formatting, cleaning, or summarizing
  - Saves about **60%** on most multi-step chains. Use this approach every time you chain

### Prompt Optimization

- **Meta-Prompting**
  - Ask a powerful model like GPT-4 to write your prompt for you
  - It often writes better prompts than humans because it thinks of edge cases like sarcasm and ambiguity that we forget
  - You pay **$0.01 once** to generate the prompt, then use a cheap model to run it forever at **$0.0001 per call**

- **Optimize Loops**
  - Start with a draft prompt, see where it fails, tell the model exactly what went wrong, have it rewrite
  - This process works in **3-5 rounds.** If the prompt is still failing after 5 rounds, the problem is the task definition, not the prompt

- **A/B Testing**
  - Run two prompt versions side by side on the same set of test cases
  - Pick the winner based on data, not gut feeling
  - **Re-test every month** because model provider updates can change which prompt works better

### Templates

- **Jinja2 Templates**
  - Write one prompt with blanks that get filled in differently for each customer
  - Use variables (`{{ customer_name }}`), conditions (`{% if priority == "high" %}`), and loops (`{% for item in context %}`)
  - One template can generate **10,000 unique prompts** by filling in different values
  - Store templates in git like code

- **Template Inheritance**
  - Create a base template with your safety rules. All other templates inherit from it automatically
  - This means **nobody can accidentally delete the safety rules** when editing a specific use-case template

- **Deploy Pipeline**
  - Roll out template changes the same way you roll out code
  - Test environment → staging → send to 10% of users first → watch the metrics → full rollout if everything looks good
  - If metrics drop, roll back instantly

### Injection Defense — 4 Layers

- **Layer 1: Delimiters**
  - Wrap the user's message inside special tags so the model knows "everything between these tags is user input, not my instructions"
  - This alone stops about **70% of injection attacks**

- **Layer 2: Sanitize**
  - Before the user's message reaches the model, scan it with pattern matching and remove known attack phrases like "ignore all previous instructions"
  - Combined with layer 1, blocks about **90% of attacks**

- **Layer 3: Instruction Hierarchy**
  - Mark certain rules as Level 1 (unbreakable) that the model can never override no matter what the user says
  - Combined with layers 1 and 2, blocks about **98% of attacks**

- **Layer 4: Output Scan**
  - Before sending the response to the user, check if it accidentally contains anything from the system prompt or internal rules
  - If it does, block the response and return a safe default
  - All 4 layers together block **99.9% of attacks**

We tested all 4 layers with 12 real attack types in project 15. Without defenses: **30-60% breach rate.** With all 4: **under 5%.** Takes about 30 minutes to implement. Rate limit users to 20 messages per minute.

---

## Retrieval Augmented Generation

### Pipeline

- **How It Works**
  - Take your documents, break them into small pieces, convert each piece into numbers (embeddings), and store them in a database
  - When a user asks a question, convert the question into numbers too, find the most similar pieces, and give them to the LLM along with the question
  - The LLM answers using your documents instead of making things up

- **What Matters Most**
  - The way you break documents into pieces (chunking) has **20-30% impact** on accuracy. Fix this first
  - The search method is the second priority
  - The LLM prompt is the last thing to optimize — it barely matters if you feed the model the wrong documents

- **Cost**
  - About **$0.01-0.05 per question.** Takes about 3 seconds end-to-end

### Chunking — How You Break Documents into Pieces

- **Fixed-Size**
  - Cut every 200 characters regardless of content
  - **Never use this.** It splits sentences in half and puts the two halves in different pieces
  - The model sees half an answer and gives the wrong response

- **Recursive**
  - Try to split at paragraph boundaries first, then sentence boundaries, then word boundaries
  - Keeps natural text units together
  - This is the **right default for 90% of cases**

- **Semantic**
  - Use AI to detect where the topic changes within a document and split there
  - Best quality because each piece covers exactly one topic
  - But **100× more expensive** than recursive ($0.10 versus $0.001 per document)

- **Parent-Child**
  - Create small precise pieces for searching AND keep the original large sections for giving to the LLM
  - You search the small pieces to find the right spot, then hand the LLM the large section so it has full context
  - This is the **production standard.** Small pieces: 512 tokens. Large sections: 1,024 tokens

- **Overlap**
  - Make adjacent pieces share 10-20% of their text at the boundaries
  - Prevents important information from falling through the cracks where one piece ends and the next begins

We proved this matters in project 54: same document, same question. Bad chunking gave the wrong answer. Good chunking gave the right answer. The only thing that changed was how we split the document.

### Embeddings — Converting Text to Numbers

- **text-embedding-3-small**
  - The most popular embedding model. Produces 1,536 numbers per piece of text
  - **Good enough for 90% of use cases.** This is where you start

- **text-embedding-3-large**
  - Produces 3,072 numbers per piece of text. More precise but costs **6× more** for only **2-5% better** accuracy
  - We tested both in project 20. Rarely worth the extra cost

- **Matryoshka Trick**
  - Take the 1,536 numbers and keep only the first 256
  - You save **6× on storage** and still retain **95% of the quality**
  - Very useful when you have millions of documents

- **Important Warning**
  - If you change your embedding model later, you have to reprocess every single document in your database
  - Choose your embedding model carefully at the start

### Vector Databases — Where You Store the Numbers

- **ChromaDB** — simplest to set up. Good for building prototypes. Not strong enough for production traffic
- **pgvector** — an extension for PostgreSQL. If you already run PostgreSQL, you can add vector search without a new database. Good up to about **10 million documents**
- **Qdrant** — purpose-built for vector search. Handles **100 million+ documents** at production scale
- **Pinecone** — fully managed service. You do not run any infrastructure. They handle everything

### Search — How You Find the Right Pieces

- **Dense Search (Embeddings)**
  - Finds pieces that mean the same thing even if they use different words
  - "How do I get my money back?" finds a document about "refund policy"
  - But it **completely misses** exact keyword matches like "error code 403"

- **BM25 (Keyword Search)**
  - Finds exact word matches. "Error 403" finds documents containing "403"
  - It is **free** and needs no embeddings
  - But it misses synonyms — searching for "car" will not find documents about "automobile"

- **Hybrid Search**
  - Runs both dense and keyword search at the same time, then merges the results
  - **Catches everything** — meaning matches and keyword matches
  - This is what every production system should use. No exceptions

- **Reranking**
  - After finding the top 20 results, use a smarter model to re-score them and pick the best 5
  - Adds about 200 milliseconds of latency
  - But improves precision by **10-20%.** Worth it when accuracy matters

### Advanced Retrieval

- **Multi-Query**
  - Instead of searching once, rephrase the question 3 different ways and search each version
  - Combine all results. Finds **15-25% more relevant documents** that the original wording missed
  - Only 10 lines of code. Always worth doing

- **HyDE (Hypothetical Document Embeddings)**
  - Generate a hypothetical answer to the question first, then search using that answer instead of the question
  - Works **10-20% better** on abstract or complex questions where the question itself does not resemble the document text

- **Self-RAG**
  - Check if the question even needs document retrieval at all
  - Simple questions like "what is 2+2" do not need it
  - Skipping retrieval when not needed saves **30-50% of cost**

- **CRAG (Corrective RAG)**
  - After retrieving documents, grade each one for relevance
  - Throw away the irrelevant ones before giving the rest to the LLM
  - Reduces hallucination by **20-40%** because the model is not distracted by irrelevant information

- **GraphRAG**
  - Build a knowledge graph (a map of entities and their relationships) from your documents
  - Lets you answer questions that require following a chain across multiple documents
  - For example: "Who does Dave ultimately report to?" requires following Dave → Carol → Bob → Alice across 4 documents
  - Regular search cannot do this. Graph traversal can

### Multimodal Documents

- **Tables** — convert to markdown format. LLMs understand markdown tables surprisingly well
- **Images** — send to GPT-4o and ask it to describe what it sees. Costs about **$0.01 per image.** The text description becomes searchable
- **Audio** — transcribe with Whisper. Costs **$0.006 per minute.** Podcasts, meetings, and calls become searchable text
- **Best practice** — convert everything to text first. This gets **90% of the value** with zero infrastructure changes. Build complex multimodal pipelines only when that last 10% matters

### RAGAS Evaluation — How to Know If Your System Works

- **Precision (target above 80%)**
  - Are you retrieving the right documents?
  - If low: you are feeding the LLM irrelevant information that confuses it
  - Fix with better chunking or add reranking

- **Recall (target above 75%)**
  - Are you retrieving all the relevant documents?
  - If low: you are missing documents that contain the answer
  - Fix with hybrid search or multi-query retrieval

- **Faithfulness (target above 90%)**
  - Is the answer based only on the documents you provided? Or did the model make things up?
  - If low: **your system is presenting fabricated information as facts. This is the most dangerous metric to fail**
  - Fix with a grounding instruction and require citations

- **Relevance (target above 85%)**
  - Does the answer address what the user actually asked?
  - If low: the model is going off-topic
  - Fix with a better prompt or a more capable model

One grounding instruction — "answer ONLY from the provided context. If the answer is not there, say I do not have that information" — drops hallucination from **50-80% to 5-15%.** Always include questions that have no answer in your test suite. If the model never says "I don't know," it is guessing on everything.

---

## Agents

### Patterns

- **ReAct (Reason and Act)**
  - The agent thinks about what to do, takes one action (like searching or calling an API), looks at the result, then decides what to do next
  - Repeats until the task is done
  - The right choice for **80% of agent tasks.** Simple to build, simple to debug
  - About **$0.15 per task**

- **Plan-Execute**
  - The agent writes a complete plan of all the steps before doing anything, then executes the plan step by step
  - Better for complex tasks that need **5 or more coordinated steps**
  - The upfront planning prevents the agent from going in circles
  - About **$0.30 per task**

- **Reflexion**
  - The agent does the task, evaluates its own work, and improves it
  - Like writing a draft, reviewing it, and rewriting
  - **Maximum 3 rounds.** If the output is still bad after 3, the task description needs to change

The biggest finding from testing both patterns: **how you describe your tools matters 10× more** than whether you use ReAct or Plan-Execute.

### Tool Use

- **Tool Descriptions Are the Most Important Thing**
  - A vague description like "gets order info" causes the agent to pick the wrong tool **15-30% of the time**
  - A specific description like "Look up order status, total, and shipping details. Use when a customer asks about their order. Returns JSON with id, status, and total" makes it pick correctly almost every time
  - This is the **cheapest quality improvement** for any agent system

- **Tool Limit**
  - Keep to a maximum of **15 tools per agent**
  - Beyond that, similar-sounding tools confuse the model
  - If you need more, create multiple specialized agents that each handle a specific domain

- **Safety Boundary**
  - The LLM decides which tool to use and what inputs to send
  - **Your code executes the actual tool.** The LLM never runs anything directly
  - Always validate inputs on your server before executing

- **Sensitive Actions**
  - Require human approval for actions like processing refunds, deleting data, or deploying code
  - Never let the agent auto-execute high-stakes operations

### Frameworks

- **LangGraph**
  - Build your agent as a flowchart with states, conditions, and loops
  - Can save progress and resume after a crash. Can pause and wait for human approval
  - The **production standard for 90% of agent use cases**

- **CrewAI**
  - Create multiple AI agents with specific roles (researcher, writer, reviewer) that work together
  - Good for quick prototypes. Less control over edge cases

- **AutoGen**
  - Agents that discuss and debate with each other
  - Good for reducing AI bias through structured disagreement

- Pick one framework and commit to it. **Mixing frameworks creates debugging nightmares**

### Multi-Agent

- **Orchestrator-Worker** — one boss agent delegates tasks to specialist agents. The **most practical pattern** for production
- **Debate** — two agents argue opposite sides, a judge agent decides. **Surprisingly effective** at reducing AI decision bias
- **Peer Review** — agents review each other's work before submitting. Extra cost but catches mistakes that a single agent misses
- Keep teams to **2-4 agents maximum.** Each agent needs 3-5 LLM calls. A team of 4 agents uses about **15-20 API calls per task**

### Memory

- **Short-Term**
  - Keep the last 10 messages in the conversation window
  - **Always use this.** Without it, the agent forgets what the user said 5 messages ago
  - When the limit is reached, the oldest messages drop off

- **Long-Term**
  - Summarize past conversations and store them. When the user returns, the agent knows their history
  - 50 messages compressed into 3 sentences saves **50× the token space**
  - Add when personalization matters

- **Entity Memory**
  - Remember specific facts about people or things
  - "This customer prefers email, is on the Pro plan, had a billing issue in March"
  - Like an automatic customer database that builds itself from conversations

- **Token Budget**
  - Plan how much space each part gets in the context window
  - System instructions (1,000 tokens) + tool descriptions (1,000) + memory (3,000) + user question (1,000) + answer (2,000) = **8,000 total**

### Safety

- **Step Limits**
  - Without a limit, an agent given an impossible task will retry the same action over and over forever
  - Set a maximum of **5-10 steps per task.** This is non-negotiable
  - We tested this — the difference is between a $0.15 task and a **$50 runaway bill**

- **Stuck Detection**
  - If the agent gets the exact same result 3 times in a row, force it to try something different or stop gracefully
  - Catches loops that a simple step limit might miss

- **Risk Tiers**
  - Searching a database = execute automatically
  - Processing a refund = wait for human approval
  - Deploying to production = always blocked without explicit authorization

- **Sandboxed Code Execution**
  - Never run AI-generated code on your own server
  - Use an isolated environment that auto-destroys after each use
  - About $0.10 per hour for a cloud sandbox

---

## Fine-Tuning

### Methods — Try in This Order

- **QLoRA (Quantized Low-Rank Adaptation)**
  - Compress the model to 4-bit precision first, then add small trainable layers on top
  - A 70 billion parameter model that normally needs **4 GPUs (140 gigabytes)** fits on **1 GPU (35 gigabytes)**
  - Quality stays at **97%** of the full model
  - This is **always where you should start.** Try this before anything else

- **LoRA (Low-Rank Adaptation)**
  - Add small trainable layers without compressing the model first
  - Reaches **95-99% quality.** Needs more hardware than QLoRA
  - Try this only if QLoRA has a quality gap larger than 2%

- **Full Fine-Tuning**
  - Update every single parameter in the model
  - Maximum quality but a 70 billion parameter model needs **4 GPUs (280 gigabytes)**
  - Rarely justified unless you have a specific quality requirement that nothing else meets

**The golden rule:** a large model compressed to 97% quality always produces better output than a small model at 100% quality. Always pick the bigger model and compress it.

### Data

- **Quality Over Quantity**
  - Research showed that 1,000 carefully written examples beat 52,000 automatically generated ones (the LIMA paper)
  - Every example must be correct, consistent, and representative of real usage

- **Learn from Production Failures**
  - Every bug your model makes in the real world becomes a new training example
  - Over time, your training data grows from real experience and covers the exact edge cases your users hit

- **Data Formats**
  - Alpaca format: single question and answer pairs
  - ShareGPT format: multi-turn conversations
  - ChatML format: the production standard. Match whatever format your API uses

- **Quality Checks**
  - Remove near-duplicate examples that waste training time
  - Balance your categories evenly so the model does not over-learn one type
  - Have humans manually check **5%** of your data for errors

### Alignment — Teaching the Model to Behave

- **Step 1: Supervised Fine-Tuning (SFT)**
  - Train the model on examples of good instruction-following behavior
  - You need **1,000-5,000 examples** of [instruction, ideal response]
  - This teaches the model to actually follow your instructions instead of ignoring them
  - **Never skip this step.** Everything else builds on top of this foundation

- **Step 2: Direct Preference Optimization (DPO)**
  - Show the model pairs of responses and tell it which one humans prefer
  - The model learns to produce output more like the preferred response
  - The modern standard for alignment. Needs **5,000-10,000 pairs** of [prompt, good response, bad response]

- **Alternative: KTO**
  - Instead of full preference pairs, just needs thumbs up or thumbs down on individual responses
  - Much easier to collect this kind of feedback from real users

- **Alternative: RLAIF**
  - Instead of human judges, use GPT-4 to decide which response is better
  - Gets **80% of human quality at 10% of the cost**
  - $10 for 5,000 judgments instead of $2,000 for human annotators

- Doing preference optimization on a model that has not been through supervised fine-tuning first is like **polishing a brick** — the surface looks nice but the foundation is broken

### Synthetic Data — Creating Training Data Cheaply

- Start with **5 perfect examples** written by hand. These set the quality standard for everything generated afterward
- Ask GPT-4 to generate hundreds more examples in the same style
- Use an LLM judge to **score each generated example from 1 to 10.** Keep only those scoring 7 or above
- Have humans spot-check **5%** of the kept examples as a final quality gate
- Generate twice as many as you need and keep the top half
- Cost: **$0.01 per example** versus $2.00 per example from human writers

### Quantization — Making Big Models Fit on Small Hardware

- **Full Precision (FP16)** — no compression. A 70 billion parameter model needs 140 gigabytes across 4 GPUs. **Almost never used** in production because it is too expensive
- **8-bit (INT8)** — light compression. 99% quality retained. 70 gigabytes. Use when 4-bit has a measurable quality problem
- **4-bit (INT4)** — the **production sweet spot.** 97% quality. 35 gigabytes on a single GPU. This is where most teams end up
- **AWQ** — a smarter version of 4-bit compression that preserves the most important weights. Best quality at the same size. Use for GPU-based serving
- **GGUF Q4_K_M** — a 4-bit format designed for CPUs and Ollama. Best balance for running models on laptops and edge devices
- **Never go below 4-bit.** Quality drops sharply at 3-bit — the storage savings are not worth the quality loss

### Platforms

- **OpenAI Fine-Tuning** — upload your data, they handle everything. The simplest option. About $25 per million tokens
- **Together AI** — fine-tune open-source models for $5-10 per million tokens. You can download and own the resulting model
- **Self-Hosted (Axolotl + Unsloth)** — run everything on your own hardware. Your data never leaves your servers. Full control
- Managed platforms are cheaper when you process **under 1 million tokens per day.** Self-hosting is cheaper above that

---

## Orchestration

### Frameworks

- **Raw API Calls** — call the LLM directly with no framework. Best for simple applications and learning. Maximum control, no extra dependencies
- **LangChain LCEL** — connect components with a pipe operator (prompt | model | parser). Gives you streaming, batching, retries, and fallbacks automatically. The older Chain classes are deprecated
- **LangGraph** — build agents as state machines with conditions, loops, and checkpoints. Can save progress and resume after crashes. Can pause for human approval. The **production standard for 90% of agent use cases**
- **LlamaIndex** — specialized for search and retrieval. 150+ built-in connectors. What takes 800 lines in LangChain often takes **50 lines in LlamaIndex**
- **Semantic Kernel** — Microsoft's framework. Works in Python, C#, and Java. Makes sense if your stack is Azure and .NET
- **Haystack** — checks your pipeline connections at build time and catches errors before runtime

### Anti-Patterns

- **Adding a framework before you need one** — build the simplest version first with raw API calls. Add a framework only when you hit a specific problem it solves
- **Calling framework functions directly everywhere** — wrap them in your own interfaces. When you need to switch, you change one file instead of hundreds
- **Using multiple frameworks together** — pick one and commit. Mixing creates debugging problems that are not worth the marginal benefits
- **Chasing version updates** — pin your framework version. Test upgrades deliberately instead of updating blindly

---

## Evaluation and Testing

### Metrics

- **BERTScore** — compares the meaning of two texts using embeddings, not exact word matching. The best metric when you have a correct reference answer to compare against
- **LLM-as-Judge (score 1-10)** — ask a powerful model to rate the quality of a response. Agrees with human raters **80-90%** of the time. Costs **$0.002 per evaluation** versus $0.20 for a human
- **LLM-as-Judge (A versus B)** — show a powerful model two responses and ask which is better. Good for comparing prompts or models. **Always randomize** which response is shown first — the model has a bias toward the first one
- **RAGAS** — four metrics specifically for Retrieval Augmented Generation: precision, recall, faithfulness, and relevance. Each one diagnoses a different problem and points to a specific fix

### Testing

- **Golden Test Suite** — 200+ questions with known correct answers. Every time you change a prompt, run the full suite. If any test fails, the deploy is blocked. **Every bug from production becomes a new test case**
- **Adversarial Testing** — tools like garak (runs **100+ automated attack patterns**) and promptfoo (assertion-based tests). Run before every launch to find vulnerabilities
- **Impossible Questions** — always include questions that have no correct answer. If the model never says "I do not know," it is guessing on everything
- **A/B Testing** — send 10% of traffic to the new version, monitor for 24 hours, then roll out or roll back. Need at least **1,000 samples** for meaningful results

### Observability

- **Log Every LLM Call** — the input, the output, which model, how many tokens, how long it took, how much it cost. **Start on day one.** Adding observability later is 10× harder
- **Platforms** — LangSmith (built for LangChain) or LangFuse (open-source, self-hosted, works with any framework)
- **Dashboards** — track the 50th, 95th, and 99th percentile of latency, the error rate, and the daily cost
- **Alerts** — page the on-call engineer when errors exceed 2%, latency exceeds 5 seconds at the 95th percentile, or cost exceeds 80% of the daily budget
- **Per-User Tracking** — monitor token usage per user. Set rate limits and daily budgets to prevent one user from consuming the entire quota

---

## Infrastructure

### Serving — What Runs the Model

- **vLLM** — the **production standard** for self-hosted models. Uses PagedAttention to handle **2-4× more concurrent users** on the same hardware. Also includes continuous batching (GPU never sits idle) and speculative decoding (a small model guesses ahead, the big model verifies)
- **TGI** — a Docker-friendly engine from HuggingFace. Simpler to set up than vLLM
- **TensorRT-LLM** — NVIDIA's maximum-performance engine. **30-50% faster** but more complex and locked to NVIDIA
- **Ollama** — run models locally with one command. Great for development. **Not suitable for production**
- **llama.cpp** — run models on CPU without a GPU. Useful for edge devices and laptops

### Gateway and Routing

- **LiteLLM Gateway** — a universal proxy that sits in front of **100+ LLM providers.** Switch providers by changing one configuration string. Handles fallbacks, load balancing, and budget tracking. Every production application should have this
- **Fallback Chain** — primary provider → secondary → local backup → graceful error. Health check every **30 seconds** to detect outages automatically
- **Model Routing** — 70% of production queries are simple. Route those to the cheap model. Only complex queries go to the expensive model. Saves **60-70%.** At 100,000 queries per day: **over $1,000 per day saved**
- **Cascading** — try the cheap model first. If its response seems uncertain, automatically escalate to the expensive model
- **Domain Override** — medical and legal queries always go to the best available model. Some domains cannot tolerate quality compromises

### Deployment

- **Streaming** — push each word to the user as the model generates it. First word in **under 500 milliseconds** versus a 2-3 second blank screen. Users perceive **3-5× faster** even though total time is the same
- **Docker** — use the nvidia/cuda base image. Mount model weights as a volume instead of putting them in the image (model files are too large)
- **Kubernetes** — autoscale based on **queue length,** not CPU utilization. LLM workloads are GPU-bound

### Cloud Platforms

- **AWS Bedrock** — for teams on AWS. Enterprise compliance built in
- **Azure OpenAI** — for teams on Azure. Data stays in your chosen region
- **Google Cloud Vertex** — for teams on Google Cloud. Gemini and open-source models
- **Groq** — the fastest API. **10-50× faster** than standard providers. Limited model selection
- **Together AI** — cheapest for open-source models. You can download the fine-tuned result
- Managed platforms are cheaper **under 1 million tokens per day.** Self-hosting is cheaper above that

---

## Safety and Governance

### Protection

- **PII Pipeline** — use Microsoft Presidio (detects **30+ types** of personal information) to replace every email, phone, SSN, and credit card with a placeholder before the LLM sees it. After the response, swap real values back. The LLM **never touches real personal data**
- **Moderation API** — OpenAI offers a **free** tool that checks text for toxicity, violence, and harmful content. Enable as the first checkpoint on every application
- **Canary Tokens** — plant a secret string in your system prompt and scan every response for it. If it appears, your prompt has been extracted. **Zero cost** early warning
- **Dual-LLM** — one model holds rules and makes decisions (privileged). A separate model generates text (quarantined). The generator never accesses the rules. **Most secure.** Banking and healthcare. 2× cost

### Hallucination Defense

- **Grounding** — "answer ONLY from the provided context." **Number one defense.** Drops fabrication from 50%+ to under 10%
- **Citations** — require the model to cite source and page number. Users can verify. Model becomes more careful when it has to show its sources
- **Confidence Scoring** — ask the model to rate certainty 1-10. Low confidence → add a disclaimer or route to a human
- **Abstention** — teach the model that saying "I do not know" is better than guessing. **If your model never abstains, it is guessing on everything**

### Guardrails

- **Guardrails AI** — validates output against rules and automatically retries if it violates them
- **NeMo Guardrails** — defines what topics the bot can and cannot discuss
- **LLM Guard** — drop-in security scanners for injection, personal information, and toxicity
- Combine LLM Guard for security and NeMo for conversation control. All add **50-200 milliseconds** of latency

### Compliance

- **EU AI Act** — risk assessment, bias testing, transparency. **Mandatory** for high-risk AI in Europe
- **GDPR** — minimize personal data. Right to deletion. Informed consent. Auto-delete logs after **30 days**
- **HIPAA** — protected health information rules. Self-hosting typically required
- **Model cards** — document what every model can do, its limitations, and ethical considerations

---

## Multimodal

- **GPT-4o Vision** — the model can analyze images. Low detail uses **85 tokens** per image. High detail uses **1,000+ tokens.** That is **10× cost difference.** Always start with low
- **Claude Vision** — particularly strong on dense text documents and long screenshots
- **Gemini Vision** — processes multiple images and has the largest context window
- **LLaVA** — open-source vision model. Run on your own hardware. Nothing leaves your server
- **Whisper** — speech to text in **100+ languages.** API: $0.006 per minute. Self-hosted: free
- **Text-to-Speech** — OpenAI TTS ($15 per million characters). ElevenLabs (best quality, voice cloning from 30 seconds of audio)
- **CLIP and Jina-CLIP** — search images with text and text with images by putting both in the same number space
- **Voice Agent** — user speaks → Whisper → LLM → text-to-speech → user hears answer. Target: **under 1 second total**
- **Production Rule** — convert everything to text first (tables to markdown, images to descriptions, audio to transcripts). Gets **90% of the value with zero infrastructure changes**

---

## Architecture

### Patterns

- **Gateway (LiteLLM)** — single entry point for all providers. Switch providers by changing **one configuration string**
- **Semantic Cache** — "refund policy?" and "how do returns work?" mean the same thing. Cache recognizes this. Hit rate: **30-40%.** Each hit: zero cost, 10 milliseconds
- **Model Routing** — simple queries → cheap model. 70% of traffic. Saves **60-70%**
- **Compound AI** — classifier + retriever + generator + guardrails + cache as separate components. Each independently testable. **80-90% cheaper** than one big model
- **MapReduce** — cheap model processes pieces in parallel, smart model combines once. **Unlimited document size**
- **Iterative Refinement** — generate → critique → rewrite. **+2 quality points per round.** Three rounds is the sweet spot
- **Fallback Chain** — primary → secondary → local → error. Timeout **2-3 seconds** before switching

### Design Rules

- **Async Everywhere** — LLM calls take 1-3 seconds. Blocking code serves about 5 users. Non-blocking serves **500.** This is non-negotiable
- **Circuit Breaker** — 5 failures in a row → stop trying → route to fallback → periodically test if the provider recovered
- **Token Budget** — plan how much context space each component gets. When history grows too long, summarize older messages
- **Idempotency** — if a network timeout causes a retry, the action should not execute twice. Use idempotency keys on every write

### Data Architecture

- **Embedding Pipeline** — extract → chunk → deduplicate (hash-based, saves **10-30%**) → embed → store with metadata
- **Metadata** — attach source, date, and type to every chunk. Filtering by metadata **before** vector search improves results dramatically
- **Incremental Updates** — when a document changes, only reprocess that document. Track the last modified timestamp
- **Zero-Downtime Re-Index** — when changing embedding models, build the new index alongside the old one and swap atomically. Users never see downtime

---

## Advanced and Emerging

- **Model Context Protocol (MCP)** — a standard way to connect any tool to any LLM, like USB-C replaced different charging cables. Build one server and it works with Claude, GPT, Gemini, and local models. FastMCP: **20 lines of code**
- **Compound AI** — specialized components working together instead of one model doing everything. **80-90% cheaper.** Each component independently testable and replaceable
- **GraphRAG** — build a knowledge graph from documents. Answer questions that require following chains across multiple documents. Worth building when **20%+ of queries** need cross-document connections
- **Distillation** — powerful model labels data (teacher), small model learns from those labels (student). Student achieves **85-95% quality at 1/30th cost.** Combined with quantization: **100× cheaper**
- **Mixture of Experts** — models like Mixtral have 8 expert sub-networks but only 2 are active per word. Total knowledge of 47 billion parameters, speed of 13 billion
- **Context Compression** — automatically removes filler words before feeding text to the LLM. Shrinks 10,000 words to 3,000 while keeping **90% quality**
- **Local Inference** — Ollama (one command), llama.cpp (CPU), MLX (Apple Silicon). Good for development and privacy. Deploy to cloud for production
- **LLMOps** — version prompts in git → golden tests → deploy to 10% → monitor → roll out or roll back. **Every bug becomes a test case.** Treat prompts like code

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
