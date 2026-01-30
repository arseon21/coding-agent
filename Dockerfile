# Используем официальный образ Python 3.11 slim
FROM python:3.11-slim

# Установка системных зависимостей (git нужен обязательно)
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Настройка рабочей директории
WORKDIR /app

# Сначала копируем requirements, чтобы кэшировать слои
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь исходный код
COPY . .

# Настройка git (обязательно для работы внутри контейнера)
RUN git config --global --add safe.directory /app

# Настройка PYTHONPATH, чтобы Python видел пакеты в src
ENV PYTHONPATH="/app:/app/src"

# Точка входа
ENTRYPOINT ["python", "main.py"]