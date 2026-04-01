FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY 11-self-consistency-benchmark.py .
EXPOSE 8000
CMD ["python", "11-self-consistency-benchmark.py"]
