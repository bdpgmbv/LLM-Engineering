# Agent Live Reasoning Trace

## The Problem
Watch an agent think -> act -> observe in real time. Full reasoning trace visible.

## How to Run
```
export OPENAI_API_KEY=sk-your-key
pip install -r requirements.txt
python main.py
```
http://localhost:8000/metrics | docker-compose up --build | pytest main.py -v
