# System Prompt Position Test

## The Problem
Rules at the top vs middle vs bottom of a long system prompt.
Which position gets followed most reliably? This tests all three.

## How to Run
```
export OPENAI_API_KEY=sk-your-key
pip install -r requirements.txt
python main.py
```
http://localhost:8000/metrics | docker-compose up --build | pytest main.py -v
