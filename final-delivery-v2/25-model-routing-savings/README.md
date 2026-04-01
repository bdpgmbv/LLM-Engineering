# Model Routing: 60-70% Cost Savings

## The Problem
Simple queries go to cheap model. Complex queries go to expensive model. 70% of real traffic is simple. This measures the exact savings.

## How to Run
```
export OPENAI_API_KEY=sk-your-key
pip install -r requirements.txt
python main.py
```
http://localhost:8000/metrics | docker-compose up --build | pytest main.py -v
