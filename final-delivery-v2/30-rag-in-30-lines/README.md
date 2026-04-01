# RAG in 30 Lines

## The Problem
The entire RAG pipeline in 30 lines of code. Embed docs, search, generate answer with grounding. This is the foundation everything else builds on.

## How to Run
```
export OPENAI_API_KEY=sk-your-key
pip install -r requirements.txt
python main.py
```
http://localhost:8000/metrics | docker-compose up --build | pytest main.py -v
