FROM python:3.11-slim

WORKDIR /app

# Копируем зависимости
COPY requirements.txt .

# Устанавливаем чётко указанные версии
RUN pip install --no-cache-dir python-telegram-bot==20.7 google-generativeai==0.8.4

# Копируем код
COPY bot.py .

# Запускаем
CMD ["python", "bot.py"]
