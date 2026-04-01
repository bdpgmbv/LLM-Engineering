# Self-Consistency: When is 5x Cost Worth It?

## The Problem
Ask the same question 5 times and take a majority vote. Costs 5x more. This tests when the accuracy boost justifies the expense.

## How to Run
```
export OPENAI_API_KEY=sk-your-key
pip install -r requirements.txt
python main.py
```
http://localhost:8000/metrics | docker-compose up --build | pytest main.py -v
