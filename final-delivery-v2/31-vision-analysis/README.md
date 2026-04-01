# Vision: Image to Structured Data

## The Problem
GPT-4o can read screenshots, charts, product photos and extract structured JSON. detail:low = 85 tokens. detail:high = 1000+ tokens. 10x cost difference.

## How to Run
```
export OPENAI_API_KEY=sk-your-key
pip install -r requirements.txt
python main.py
```
http://localhost:8000/metrics | docker-compose up --build | pytest main.py -v
