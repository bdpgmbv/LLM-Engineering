# Voice of Customer Analyzer

## The Problem
10 reviews -> sentiment + topics + actions in one API call. Structured JSON output.

## How to Run
```
export OPENAI_API_KEY=sk-your-key
pip install -r requirements.txt
python main.py
```
http://localhost:8000/metrics | docker-compose up --build | pytest main.py -v
