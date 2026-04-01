FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY 47-rag-vs-finetune-tco.py .
EXPOSE 8000
CMD ["python", "47-rag-vs-finetune-tco.py"]
