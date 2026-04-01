# Multi-Query RAG

## The Problem
Rephrase the user question 3 different ways, search for each, combine results. This finds 15-25% more relevant documents than a single search.

## How to Run
```
export OPENAI_API_KEY=sk-your-key
pip install -r requirements.txt
python main.py
```
http://localhost:8000/metrics | docker-compose up --build | pytest main.py -v
