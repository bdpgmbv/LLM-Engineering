# Compound AI vs Monolith

## The Problem
One big GPT-4o call for everything vs a system of small specialized components. The compound system saves 70-90% and is easier to debug.

## How to Run
```
export OPENAI_API_KEY=sk-your-key
pip install -r requirements.txt
python main.py
```
http://localhost:8000/metrics | docker-compose up --build | pytest main.py -v
