import requests
import feedparser
import telebot
import threading
import time

BOT_TOKEN = "ВСТАВЬ_СВОЙ_ТЕЛЕГРАМ_ТОКЕН"
url = "https://habr.com/ru/rss/all/all/?fl=ru"
bot = telebot.TeleBot(BOT_TOKEN)
user_keywords = {}  # {chat_id: [list of keywords]}


@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Реакция на команду /start"""
    welcome_text = (
        "👋 Привет! Я бот для мониторинга статей на хабре по ключевым словам.\n\n"
        "Доступные команды:\n"
        "/news — показать статьи которые нашли по твоим ключевым словам \n"
        "/list — список твоих ключевых слов по которым мы ищем нужные статьи\n"
        "/add - добавить ключевые слова в список\n"
        "/delete - удалить ключевые слова из списка\n"
        "/clear - удалить очистить список ключевых слов"
    )
    bot.send_message(message.chat.id, welcome_text)


@bot.message_handler(commands=['news'])
def send_news(message):
    response = requests.get(url)

    if response.status_code != 200:
        bot.send_message(
            message.chat.id, "❌ Не удалось получить новости. Попробуйте позже.")
        return

    v = feedparser.parse(response.text)

    if not v.entries:
        bot.send_message(message.chat.id, "❌ Лента новостей пуста")
        return

    # Получаем ключевые слова конкретного пользователя
    user_kws = user_keywords.get(message.chat.id, [])

    if not user_kws:
        bot.send_message(
            message.chat.id, "❌ У вас нет ключевых слов. Используйте /add для добавления")
        return

    found_count = 0
    for entry in v.entries:
        title = str(entry.title).lower()
        summary = str(entry.summary).lower()

        for keyword in user_kws:  # ← Итерируем по ключевым словам пользователя
            if keyword in title or keyword in summary:
                news_text = (
                    f"✅ Найдено совпадение: {keyword}\n"
                    f"📰 {entry.title}\n"
                    f"🔗 {entry.link}"
                )
                bot.send_message(message.chat.id, news_text)
                found_count += 1
                break

    if found_count == 0:
        bot.send_message(
            message.chat.id, "❌ Новостей с вашими ключевыми словами не найдено")
    else:
        bot.send_message(
            message.chat.id, f"📊 Всего найдено: {found_count} новостей")


@bot.message_handler(commands=['list'])
def send_list(message):
    keywords = user_keywords.get(message.chat.id, [])
    if not keywords:
        bot.send_message(message.chat.id, "❌ Ваш список ключевых слов пуст")
        return
    else:
        text = ", ".join(keywords)
        bot.send_message(
            message.chat.id, f"📋 Ваш список ключевых слов:\n{text}")


@bot.message_handler(commands=['add'])
def add_key_word(message):
    # 1. Получаем текущие ключевые слова
    keywords = user_keywords.get(message.chat.id, [])

    # 2. Разбираем команду (пропускаем саму команду /add)
    # ['/add', 'python', 'fastapi'] → ['python', 'fastapi']
    parts = [word.lower() for word in message.text.split()[1:]]

    # 3. Проверяем, есть ли слова для добавления
    if not parts:
        bot.send_message(
            message.chat.id, "❌ Укажите ключевые слова. Пример: /add python fastapi")
        return

    new_words = [word for word in parts if word not in keywords]
    if not new_words:
        bot.send_message(
            message.chat.id, "ℹ️ Все эти слова уже есть в вашем списке")
        return
    # 4. Добавляем новые слова (set удаляет дубликаты)
    user_keywords[message.chat.id] = list(set(keywords + parts))

    # 5. Отправляем подтверждение
    bot.send_message(
        message.chat.id, f"✅ Слова добавлены: {', '.join(new_words)}")


@bot.message_handler(commands=['delete'])
def delete_key_word(message):
    # 1. Получаем текущие ключевые слова
    keywords = user_keywords.get(message.chat.id, [])

    # 2. Разбираем команду (пропускаем саму команду /delete)
    parts = [word.lower() for word in message.text.split()[1:]]

    # 3. Проверяем, есть ли слова для удаления
    if not parts:
        bot.send_message(
            message.chat.id, "❌ Укажите ключевые слова. Пример: /delete python fastapi")
        return

    # 4. Проверяем, есть ли хоть одно слово в списке
    if any(word in keywords for word in parts):
        result = [x for x in keywords if x not in parts]
        user_keywords[message.chat.id] = result
        bot.send_message(
            message.chat.id, f"✅ Слова удалены: {', '.join(parts)}")
    else:
        bot.send_message(
            message.chat.id, "❌ Таких слов нет в вашем списке ключевых слов")


@bot.message_handler(commands=['clear'])
def clear_keywords(message):
    if not user_keywords.get(message.chat.id, []):
        bot.send_message(message.chat.id, "ℹ️ Список уже пуст")
        return
    user_keywords[message.chat.id] = []
    bot.send_message(message.chat.id, "🗑️ Все ключевые слова удалены")


def check_rss_background():
    while True:
        try:
            # 1. Скачиваем RSS один раз
            response = requests.get(url)
            
            if response.status_code != 200:
                print(f"❌ Не удалось получить RSS. Код: {response.status_code}")
                time.sleep(1800)
                continue  # Пропускаем этот цикл проверки
            
            v = feedparser.parse(response.text)
            
            if not v.entries:
                print("❌ Лента новостей пуста")
                time.sleep(1800)
                continue
            
            # 2. Проходим по всем пользователям
            for chat_id, keywords in list(user_keywords.items()):
                # Пропускаем пользователей без ключевых слов
                if not keywords:
                    continue
                
                # 3. Проверяем новости для этого пользователя
                found_count = 0
                for entry in v.entries:
                    title = str(entry.title).lower() 
                    summary = str(entry.summary).lower()
                    
                    for keyword in keywords:
                        if keyword in title or keyword in summary:
                            news_text = (
                                f"✅ Найдено совпадение: {keyword}\n"
                                f"📰 {entry.title}\n"
                                f"🔗 {entry.link}"
                            )
                            bot.send_message(chat_id, news_text)
                            found_count += 1
                            break
                
                # 4. Отправляем итог только если что-то нашли
                if found_count > 0:
                    bot.send_message(chat_id, f"📊 Всего найдено: {found_count} новостей")
            
            # 5. Спим 30 минут
            time.sleep(1800)
        
        except Exception as e:
            print(f"❌ Ошибка в фоновой проверке: {e}")
            time.sleep(1800)  # Даже при ошибке продолжаем работу


# Запускаем фоновую проверку
background_thread = threading.Thread(target=check_rss_background, daemon=True)
background_thread.start()
print("🤖 Бот запущен и ожидает сообщений...")
# Запускаем бота в режиме постоянного опроса серверов Telegram
bot.polling(none_stop=True)




