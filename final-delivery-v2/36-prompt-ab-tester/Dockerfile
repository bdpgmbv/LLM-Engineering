FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY 36-prompt-ab-tester.py .
EXPOSE 8000
CMD ["python", "36-prompt-ab-tester.py"]
