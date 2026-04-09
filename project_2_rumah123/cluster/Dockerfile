FROM mcr.microsoft.com/playwright/python:v1.43.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get update && apt-get install -y netcat-openbsd && rm -rf /var/lib/apt/lists/*
RUN python -m playwright install --with-deps chromium

COPY . .
RUN chmod +x wait-for-it.sh

# Set environment variables for Scrapy Project
ENV PYTHONPATH=/app
ENV SCRAPY_SETTINGS_MODULE=core.settings
