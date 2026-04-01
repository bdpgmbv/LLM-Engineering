FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY 14-jinja2-templates.py .
EXPOSE 8000
CMD ["python", "14-jinja2-templates.py"]
