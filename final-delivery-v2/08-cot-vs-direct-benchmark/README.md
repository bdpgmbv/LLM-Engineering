# Chain-of-Thought vs Direct Answer

## The Problem
Chain-of-Thought (CoT) means telling the AI 'think step by step.' It costs 2x more tokens. This project tests when that extra cost actually helps and when it is wasted money.

## How to Run
```
export OPENAI_API_KEY=sk-your-key
pip install -r requirements.txt
python main.py
```
http://localhost:8000/metrics | docker-compose up --build | pytest main.py -v
