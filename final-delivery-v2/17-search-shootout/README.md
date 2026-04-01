# Dense vs BM25 vs Hybrid Search

## The Problem
Dense (embedding) search finds meaning. BM25 (keyword) search finds exact words. Hybrid combines both. This tests all 3 on the same queries to prove hybrid wins.

## How to Run
```
export OPENAI_API_KEY=sk-your-key
pip install -r requirements.txt
python main.py
```
http://localhost:8000/metrics | docker-compose up --build | pytest main.py -v
