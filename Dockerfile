# 1. Берем легкий официальный образ Python
FROM python:3.12-slim
# 2. Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app
# 3. Копируем файл зависимостей и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# 4. Копируем весь остальной код проекта в контейнер
COPY . .
# 5. Команда запуска Telegram-бота
CMD ["python", "test_rss.py"]