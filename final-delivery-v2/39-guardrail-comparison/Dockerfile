FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY 39-guardrail-comparison.py .
EXPOSE 8000
CMD ["python", "39-guardrail-comparison.py"]
