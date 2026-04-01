# Injection Attack Lab

## The Problem
15 real attack vectors tested against an unprotected system prompt, then against 4 defense layers. Shows exactly which attacks work and which defenses catch them.

## How to Run
```
export OPENAI_API_KEY=sk-your-key
pip install -r requirements.txt
python main.py
```
http://localhost:8000/metrics | docker-compose up --build | pytest main.py -v
