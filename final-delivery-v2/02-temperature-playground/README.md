# Temperature Playground

## The Problem
Temperature controls how random the AI answers are.
temp=0: same answer every time (robotic). temp=1.5: creative but sometimes nonsense.
Set it wrong and your chatbot sounds robotic or says crazy things.

## What We Find Out
1. Does temp=0 really give the exact same answer every time?
2. At what temperature does the AI start saying weird things?
3. Best setting for customer support vs creative writing?
4. What does top_p actually do?

## Why It Matters
Your team deploys a customer support bot. You need the right temperature.
Too low = robotic. Too high = crazy. This finds the sweet spot.

## How to Run
```
export OPENAI_API_KEY=sk-your-key-here
pip install -r requirements.txt
python main.py
```
Open http://localhost:8000/metrics

Full stack: `docker-compose up --build` then http://localhost:3000 (admin/admin)

Tests: `pytest main.py -v`
