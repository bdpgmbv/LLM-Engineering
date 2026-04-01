# Agent Loop Detection

## The Problem
Give agents impossible tasks. Do they loop forever or stop gracefully? Max steps is essential.

## How to Run
```
export OPENAI_API_KEY=sk-your-key
pip install -r requirements.txt
python main.py
```
http://localhost:8000/metrics | docker-compose up --build | pytest main.py -v
