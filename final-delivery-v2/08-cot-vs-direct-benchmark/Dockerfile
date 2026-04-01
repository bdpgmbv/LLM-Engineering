FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY 08-cot-vs-direct-benchmark.py .
EXPOSE 8000
CMD ["python", "08-cot-vs-direct-benchmark.py"]
