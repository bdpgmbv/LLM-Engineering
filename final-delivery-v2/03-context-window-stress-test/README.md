# Context Window Stress Test

## The Problem
LLMs pay more attention to the START and END of text, and forget the MIDDLE.
This is called "lost in the middle." If your important info is buried in
the middle of 20 documents, the LLM might ignore it completely.

## What We Find Out
1. Does the model really lose info in the middle?
2. At what context size does quality drop?
3. Where should you put important info?
4. How much does latency increase with context size?

## How to Run
```
export OPENAI_API_KEY=sk-your-key
pip install -r requirements.txt
python main.py
```
http://localhost:8000/metrics | docker-compose up --build | pytest main.py -v
