# Базовый образ
FROM python:3.10-slim

# Создадим рабочую директорию внутри контейнера
WORKDIR /app

# Скопируем только requirements.txt, чтобы сначала установить зависимости
COPY requirements.txt .

# Установим зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Скопируем всё остальное в контейнер
COPY . .

# Запуск приложения
CMD ["uvicorn", "solution.main:app", "--host", "0.0.0.0", "--port", "8000"]