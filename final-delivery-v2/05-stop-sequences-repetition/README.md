# Stop Sequences + Repetition Penalty

## The Problem
Without stop sequences, models ramble past where you want them to stop.
Without repetition handling, they loop the same phrases over and over.
Both waste tokens (money) and annoy users.

## How to Run
```
export OPENAI_API_KEY=sk-your-key
pip install -r requirements.txt
python main.py
```
