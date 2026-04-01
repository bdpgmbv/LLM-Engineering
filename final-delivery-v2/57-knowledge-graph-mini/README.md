# Knowledge Graph Mini

## The Problem
Extract entities and relationships from text. Answer multi-hop questions that regular RAG cant.

## How to Run
```
export OPENAI_API_KEY=sk-your-key
pip install -r requirements.txt
python main.py
```
http://localhost:8000/metrics | docker-compose up --build | pytest main.py -v
