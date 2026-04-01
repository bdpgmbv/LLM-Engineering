# Hallucination Trap

## The Problem
Ask questions that are NOT in the documents. Does the AI make up an answer? Without grounding instructions, LLMs hallucinate 50-80% of the time on unanswerable questions.

## How to Run
```
export OPENAI_API_KEY=sk-your-key
pip install -r requirements.txt
python main.py
```
http://localhost:8000/metrics | docker-compose up --build | pytest main.py -v
