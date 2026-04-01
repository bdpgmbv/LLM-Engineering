# DPO Preference Data Pipeline

## The Problem
Generate chosen/rejected pairs for alignment training. GPT-4 judges which response is better (RLAIF). 5K pairs for $10 instead of $2K human annotators.

## How to Run
```
export OPENAI_API_KEY=sk-your-key
pip install -r requirements.txt
python main.py
```
http://localhost:8000/metrics | docker-compose up --build | pytest main.py -v
