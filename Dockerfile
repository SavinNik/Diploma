FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .
  CMD ["gunicorn", "backend.wsgi:application", "--bind", "0:8000", "--workers", "4", "--threads", "4"]


