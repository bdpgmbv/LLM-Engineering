# RAG Eval Dashboard

## The Problem
Full RAGAS evaluation: precision, recall, faithfulness, relevance. 4 metrics, each catches a different failure. If faithfulness is below 90%, your system is lying to users.

## How to Run
```
export OPENAI_API_KEY=sk-your-key
pip install -r requirements.txt
python main.py
```
http://localhost:8000/metrics | docker-compose up --build | pytest main.py -v
