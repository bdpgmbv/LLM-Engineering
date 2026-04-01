FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY 30-rag-in-30-lines.py .
EXPOSE 8000
CMD ["python", "30-rag-in-30-lines.py"]
