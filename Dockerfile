# Используем официальный легкий образ Python
FROM python:3.11-slim

# Переменные окружения для Python
# PYTHONDONTWRITEBYTECODE 1: Запрещает Python писать файлы .pyc на диск
# PYTHONUNBUFFERED 1: Гарантирует, что логи Python выводятся в консоль без буферизации
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости (git нужен для GitPython)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Копируем исходный код проекта
COPY . .

# Создаем не-root пользователя для безопасности
RUN useradd -m appuser && chown -R appuser /app
USER appuser

# Точка входа (по умолчанию запускает CLI справку)
CMD ["python", "main.py", "--help"]