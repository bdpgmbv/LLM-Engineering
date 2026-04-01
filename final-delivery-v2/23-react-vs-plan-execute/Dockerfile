FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY 23-react-vs-plan-execute.py .
EXPOSE 8000
CMD ["python", "23-react-vs-plan-execute.py"]
