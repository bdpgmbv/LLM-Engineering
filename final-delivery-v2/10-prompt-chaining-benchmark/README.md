# Prompt Chaining: Sequential vs Parallel

## The Problem
One big prompt vs breaking it into steps. Which gives better results? Which is faster? This tests single prompt vs sequential chain vs parallel chain.

## How to Run
```
export OPENAI_API_KEY=sk-your-key
pip install -r requirements.txt
python main.py
```
http://localhost:8000/metrics | docker-compose up --build | pytest main.py -v
