FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY 41-embedding-pipeline-dedup.py .
EXPOSE 8000
CMD ["python", "41-embedding-pipeline-dedup.py"]
