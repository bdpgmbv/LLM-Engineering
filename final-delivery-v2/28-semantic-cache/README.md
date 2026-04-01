# Semantic Cache

## The Problem
'Refund policy?' and 'how do returns work?' mean the same thing. A semantic cache recognizes this and returns the cached answer instead of calling the API again. Saves 30-40% of API calls.

## How to Run
```
export OPENAI_API_KEY=sk-your-key
pip install -r requirements.txt
python main.py
```
http://localhost:8000/metrics | docker-compose up --build | pytest main.py -v
