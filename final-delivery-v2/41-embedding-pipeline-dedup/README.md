# Embedding Pipeline with Dedup

## The Problem
Extract -> chunk -> dedup (hash) -> embed -> metadata. The production pipeline. Dedup saves 10-30% on embedding costs.

## How to Run
```
export OPENAI_API_KEY=sk-your-key
pip install -r requirements.txt
python main.py
```
http://localhost:8000/metrics | docker-compose up --build | pytest main.py -v
