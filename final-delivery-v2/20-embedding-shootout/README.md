# Embedding Model Shootout

## The Problem
OpenAI text-embedding-3-small vs large. The large model costs 6x more. Is it 6x better? This tests both on the same queries.

## How to Run
```
export OPENAI_API_KEY=sk-your-key
pip install -r requirements.txt
python main.py
```
http://localhost:8000/metrics | docker-compose up --build | pytest main.py -v
