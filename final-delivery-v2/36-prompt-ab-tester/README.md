# Prompt A/B Tester

## The Problem
Two prompt variants, 15 test cases, LLM judges. Statistical winner. A tool nobody else has — reusable for any prompt comparison.

## How to Run
```
export OPENAI_API_KEY=sk-your-key
pip install -r requirements.txt
python main.py
```
http://localhost:8000/metrics | docker-compose up --build | pytest main.py -v
