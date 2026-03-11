# Используем официальный Python 3.11
FROM python:3.11-slim

# Рабочая директория
WORKDIR /app

# Копируем requirements и ставим зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальной код
COPY . .

# Точка входа
CMD ["python", "bot.py"]
