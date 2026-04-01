# Knowledge Distillation

## The Problem
GPT-4o labels 20 examples (teacher). Fine-tune mini on those labels (student). Student runs at 1/30th the cost.

## How to Run
```
export OPENAI_API_KEY=sk-your-key
pip install -r requirements.txt
python main.py
```
http://localhost:8000/metrics | docker-compose up --build | pytest main.py -v
