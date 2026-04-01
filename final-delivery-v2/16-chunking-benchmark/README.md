# Chunking Strategy Benchmark

## The Problem
RAG quality depends on HOW you split documents into chunks. Fixed-size vs recursive vs sentence vs parent-child. This tests all 4 on the same documents with the same questions.

## How to Run
```
export OPENAI_API_KEY=sk-your-key
pip install -r requirements.txt
python main.py
```
http://localhost:8000/metrics | docker-compose up --build | pytest main.py -v
