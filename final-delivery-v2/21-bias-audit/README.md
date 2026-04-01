# Bias Audit Across Demographics

## The Problem
Same prompt, different names. Does the AI recommend different careers for 'James Smith' vs 'Aisha Mohammed'? This measures the disparity.

## How to Run
```
export OPENAI_API_KEY=sk-your-key
pip install -r requirements.txt
python main.py
```
http://localhost:8000/metrics | docker-compose up --build | pytest main.py -v
