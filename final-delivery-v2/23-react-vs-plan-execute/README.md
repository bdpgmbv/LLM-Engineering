# ReAct vs Plan-Execute Agent Patterns

## The Problem
Two ways to build AI agents. ReAct: think-act-observe loop. Plan-Execute: plan all steps first, then run them. This tests both on 5 tasks.

## How to Run
```
export OPENAI_API_KEY=sk-your-key
pip install -r requirements.txt
python main.py
```
http://localhost:8000/metrics | docker-compose up --build | pytest main.py -v
