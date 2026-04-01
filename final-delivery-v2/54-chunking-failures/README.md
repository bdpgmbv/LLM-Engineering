# Chunking Failure Modes

## The Problem
Same question fails with bad chunks, works with good chunks. Proves chunking is #1 quality lever.

## How to Run
```
pip install -r requirements.txt
python main.py
```
http://localhost:8000/metrics | docker-compose up --build | pytest main.py -v
