# Synthetic Data Pipeline

## The Problem
5 seed examples -> GPT generates 20 more -> LLM-as-judge scores quality -> keep only good ones. Creates training data at $5-10 per 1000 examples instead of $2000 manual.

## How to Run
```
export OPENAI_API_KEY=sk-your-key
pip install -r requirements.txt
python main.py
```
http://localhost:8000/metrics | docker-compose up --build | pytest main.py -v
