# Meta-Prompting

## The Problem
Can GPT-4 write a better prompt than you? This tests human-written vs AI-written prompts on 10 classification tasks. The AI-generated prompt often wins because it includes edge cases humans forget.

## How to Run
```
export OPENAI_API_KEY=sk-your-key
pip install -r requirements.txt
python main.py
```
http://localhost:8000/metrics | docker-compose up --build | pytest main.py -v
