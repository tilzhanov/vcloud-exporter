FROM python:3.10-slim

WORKDIR /app

# Устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем скрипт
COPY exporter.py .

# Открываем порт для Prometheus
EXPOSE 8000

CMD ["python", "exporter.py"]

