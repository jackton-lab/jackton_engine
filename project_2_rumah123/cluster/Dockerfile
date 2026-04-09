FROM mcr.microsoft.com/playwright/python:v1.43.0-jammy

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN python -m playwright install --with-deps chromium

COPY . .

# Set environment variables for Scrapy Project
ENV PYTHONPATH=/app
ENV SCRAPY_SETTINGS_MODULE=core.settings
