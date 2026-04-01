# Structured Output Benchmark

## The Problem
When you need JSON from the AI, there are 3 ways: raw text, JSON mode, XML tags. Which one gives parseable output most reliably?

## How to Run
```
export OPENAI_API_KEY=sk-your-key
pip install -r requirements.txt
python main.py
```
http://localhost:8000/metrics | docker-compose up --build | pytest main.py -v
