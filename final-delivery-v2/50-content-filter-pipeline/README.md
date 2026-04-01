# Content Filtering Pipeline

## The Problem
15 inputs through 3 layers: PII regex, injection regex, LLM safety check. Ordered fast->slow.

## How to Run
```
export OPENAI_API_KEY=sk-your-key
pip install -r requirements.txt
python main.py
```
http://localhost:8000/metrics | docker-compose up --build | pytest main.py -v
