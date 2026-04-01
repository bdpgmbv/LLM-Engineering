# Cost Anomaly Detector

## The Problem
Track every API call. Alert when cost spikes above 2 standard deviations. Like Datadog for LLM costs in 50 lines.

## How to Run
```
export OPENAI_API_KEY=sk-your-key
pip install -r requirements.txt
python main.py
```
http://localhost:8000/metrics | docker-compose up --build | pytest main.py -v
