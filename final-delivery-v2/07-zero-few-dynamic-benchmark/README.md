# Zero-Shot vs Few-Shot vs Dynamic Few-Shot

## The Problem
You can give the AI 0 examples (zero-shot), 3 fixed examples (few-shot), or 3 carefully picked examples (dynamic few-shot). Which one gets the most correct answers? This tests all 3 on 50 real customer queries.

## How to Run
```
export OPENAI_API_KEY=sk-your-key
pip install -r requirements.txt
python main.py
```
http://localhost:8000/metrics | docker-compose up --build | pytest main.py -v
