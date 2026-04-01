# MapReduce Summarization

## The Problem
Split big doc into chapters -> summarize each in parallel (MAP) -> combine summaries (REDUCE). Handles unlimited document size. Cheap model for MAP, smart model for REDUCE.

## How to Run
```
export OPENAI_API_KEY=sk-your-key
pip install -r requirements.txt
python main.py
```
http://localhost:8000/metrics | docker-compose up --build | pytest main.py -v
