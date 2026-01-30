# Ипользуем официальный образ Python 3.11
FROM python:3.11-slim

# Установка системных зависимостей для Git и работы с репозиториями
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN git config --global --add safe.directory /app

# Настройка рабочей директории
WORKDIR /app

# Копируем зависимости и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код
COPY . .

# Настройка PYTHONPATH, чтобы модули в /app/src были доступны
ENV PYTHONPATH="/app:/app/src"

# Точка входа
ENTRYPOINT ["python", "main.py"]