# Injection Firewall

## The Problem
10 attacks through 4 defense layers. Pass/fail report for each.

## How to Run
```
export OPENAI_API_KEY=sk-your-key
pip install -r requirements.txt
python main.py
```
http://localhost:8000/metrics | docker-compose up --build | pytest main.py -v
