# Stale Data Problem

## The Problem
RAG returns outdated info if old documents are still in your index. Fix with freshness metadata filtering.

## How to Run
```
export OPENAI_API_KEY=sk-your-key
pip install -r requirements.txt
python main.py
```
http://localhost:8000/metrics | docker-compose up --build | pytest main.py -v
