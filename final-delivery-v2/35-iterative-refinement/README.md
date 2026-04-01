# Iterative Refinement: Generate → Critique → Improve

## The Problem
Write something, get feedback, rewrite. 3 rounds. Quality improves ~2 points per round on a 1-10 scale. Costs 3x but worth it for client-facing content.

## How to Run
```
export OPENAI_API_KEY=sk-your-key
pip install -r requirements.txt
python main.py
```
http://localhost:8000/metrics | docker-compose up --build | pytest main.py -v
