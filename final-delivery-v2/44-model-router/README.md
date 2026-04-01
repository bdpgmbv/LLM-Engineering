# Model Router

## The Problem
Auto-classify queries and route to cheap vs expensive model. Simple rule: length + keywords. Saves 60-70%.

## How to Run
```
export OPENAI_API_KEY=sk-your-key
pip install -r requirements.txt
python main.py
```
http://localhost:8000/metrics | docker-compose up --build | pytest main.py -v
