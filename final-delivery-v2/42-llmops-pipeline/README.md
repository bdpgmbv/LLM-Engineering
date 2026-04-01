# LLMOps Pipeline

## The Problem
Version -> golden test -> canary deploy -> monitor -> rollback if bad. The CI/CD pipeline for prompt changes. Every bad prompt caught before users see it.

## How to Run
```
export OPENAI_API_KEY=sk-your-key
pip install -r requirements.txt
python main.py
```
http://localhost:8000/metrics | docker-compose up --build | pytest main.py -v
