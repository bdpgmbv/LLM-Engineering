# Streaming: First Token vs Total Latency

## The Problem
One flag (stream=True) changes user experience dramatically. First word appears in 200ms instead of waiting 2-3 seconds for the full response.

## How to Run
```
export OPENAI_API_KEY=sk-your-key
pip install -r requirements.txt
python main.py
```
http://localhost:8000/metrics | docker-compose up --build | pytest main.py -v
