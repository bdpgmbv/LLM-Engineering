# LLM-as-Judge

## The Problem
Instead of paying humans $2000 to grade 10K responses, use GPT-4 to grade them for $20. Agrees with humans 80-90% of the time.

## How to Run
```
export OPENAI_API_KEY=sk-your-key
pip install -r requirements.txt
python main.py
```
http://localhost:8000/metrics | docker-compose up --build | pytest main.py -v
