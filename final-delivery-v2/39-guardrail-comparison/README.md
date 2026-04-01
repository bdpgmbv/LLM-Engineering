# Guardrail Framework Comparison

## The Problem
3 guardrail patterns tested on 10 inputs: output validation, topic control, input scanning. Each catches different threats.

## How to Run
```
export OPENAI_API_KEY=sk-your-key
pip install -r requirements.txt
python main.py
```
http://localhost:8000/metrics | docker-compose up --build | pytest main.py -v
