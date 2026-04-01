# PII Pipeline: Redact -> LLM -> Re-insert

## The Problem
The LLM never sees real personal data. Emails, SSNs, credit cards are replaced with placeholders before sending to the API. After the response, real values are put back.

## How to Run
```
export OPENAI_API_KEY=sk-your-key
pip install -r requirements.txt
python main.py
```
http://localhost:8000/metrics | docker-compose up --build | pytest main.py -v
