import requests
import feedparser
import telebot
import threading
import time
import os
from telebot import types
from dotenv import load_dotenv
from db import (
    init_db,
    get_user_keywords,
    add_keywords_to_db,
    delete_keywords_from_db,
    clear_keywords_from_db,
    get_all_users_with_keywords,
    get_sent_news_ids,
    add_sent_news_to_db,
    clear_sent_news_from_db
)

load_dotenv()

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("ОШИБКА: Переменная BOT_TOKEN не найдена в окружении! Проверь файл .env")
url = os.environ.get("RSS_URL", "https://default-rss.com")
bot = telebot.TeleBot(BOT_TOKEN)


# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====

def get_main_menu_keyboard():
    """Создаёт клавиатуру главного меню"""
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("📰 Новости", callback_data="menu_news"),
        types.InlineKeyboardButton("📋 Мои подписки", callback_data="menu_list")
    )
    keyboard.add(
        types.InlineKeyboardButton("➕ Добавить", callback_data="menu_add"),
        types.InlineKeyboardButton("🗑️ Очистить всё", callback_data="menu_clear")
    )
    return keyboard


def get_back_to_menu_keyboard():
    """Создаёт клавиатуру с кнопкой возврата в меню"""
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(types.InlineKeyboardButton("🔙 В главное меню", callback_data="back_to_menu"))
    return keyboard


# ===== КОМАНДЫ БОТА =====

@bot.message_handler(commands=['start'])
def send_welcome(message):
    """Реакция на команду /start — показываем главное меню"""
    welcome_text = (
        "👋 Привет! Я бот для мониторинга статей на Хабре.\n\n"
        "Выберите действие:"
    )
    bot.send_message(
        message.chat.id,
        welcome_text,
        reply_markup=get_main_menu_keyboard()
    )


@bot.message_handler(commands=['news'])
def send_news(message):
    """Показать новости по ключевым словам"""
    response = requests.get(url)

    if response.status_code != 200:
        bot.send_message(
            message.chat.id, "❌ Не удалось получить новости. Попробуйте позже.")
        return

    v = feedparser.parse(response.text)

    if not v.entries:
        bot.send_message(message.chat.id, "❌ Лента новостей пуста")
        return

    user_kws = get_user_keywords(message.chat.id)

    if not user_kws:
        bot.send_message(
            message.chat.id,
            "❌ У вас нет ключевых слов. Используйте ➕ Добавить",
            reply_markup=get_main_menu_keyboard()
        )
        return

    found_count = 0
    for entry in v.entries:
        title = str(entry.title).lower()
        summary = str(entry.summary).lower()

        for keyword in user_kws:
            if keyword in title or keyword in summary:
                news_text = (
                    f"✅ Найдено совпадение: {keyword}\n"
                    f"📰 {entry.title}"
                )
                
                # Создаём клавиатуру с кнопкой-ссылкой
                keyboard = types.InlineKeyboardMarkup()
                keyboard.add(
                    types.InlineKeyboardButton("📖 Читать на Хабре", url=str(entry.link))
                )
                
                bot.send_message(message.chat.id, news_text, reply_markup=keyboard)
                found_count += 1
                break

    if found_count == 0:
        bot.send_message(
            message.chat.id,
            "❌ Новостей с вашими ключевыми словами не найдено",
            reply_markup=get_main_menu_keyboard()
        )
    else:
        bot.send_message(
            message.chat.id,
            f"📊 Всего найдено: {found_count} новостей",
            reply_markup=get_main_menu_keyboard()
        )


@bot.message_handler(commands=['list'])
def send_list(message):
    """Показать список ключевых слов с кнопками удаления"""
    keywords = get_user_keywords(message.chat.id)
    
    if not keywords:
        bot.send_message(
            message.chat.id,
            "❌ Ваш список ключевых слов пуст",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    text = "📋 Ваш список ключевых слов:\n\n"
    text += "\n".join([f"• {kw}" for kw in keywords])
    text += "\n\nНажмите на слово, чтобы удалить его:"
    
    # Создаём клавиатуру с кнопками для каждого слова
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    
    for keyword in keywords:
        keyboard.add(
            types.InlineKeyboardButton(
                f"❌ {keyword}",
                callback_data=f"delete_{keyword}"
            )
        )
    
    keyboard.add(types.InlineKeyboardButton("🔙 В главное меню", callback_data="back_to_menu"))
    
    bot.send_message(message.chat.id, text, reply_markup=keyboard)


@bot.message_handler(commands=['add'])
def add_key_word(message):
    """Добавить ключевые слова (текстовая команда)"""
    keywords = get_user_keywords(message.chat.id)
    parts = [word.lower() for word in message.text.split()[1:]]

    if not parts:
        bot.send_message(
            message.chat.id,
            "❌ Укажите ключевые слова. Пример: /add python fastapi",
            reply_markup=get_main_menu_keyboard()
        )
        return

    new_words = [word for word in parts if word not in keywords]
    if not new_words:
        bot.send_message(
            message.chat.id,
            "ℹ️ Все эти слова уже есть в вашем списке",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    add_keywords_to_db(message.chat.id, new_words)
    clear_sent_news_from_db(message.chat.id)  # Очищаем историю при добавлении
    
    bot.send_message(
        message.chat.id,
        f"✅ Слова добавлены: {', '.join(new_words)}",
        reply_markup=get_main_menu_keyboard()
    )


@bot.message_handler(commands=['delete'])
def delete_key_word(message):
    """Удалить ключевые слова (текстовая команда)"""
    keywords = get_user_keywords(message.chat.id)
    parts = [word.lower() for word in message.text.split()[1:]]

    if not parts:
        bot.send_message(
            message.chat.id,
            "❌ Укажите ключевые слова. Пример: /delete python fastapi",
            reply_markup=get_main_menu_keyboard()
        )
        return

    if any(word in keywords for word in parts):
        result = [x for x in keywords if x in parts]
        delete_keywords_from_db(message.chat.id, result)
        
        bot.send_message(
            message.chat.id,
            f"✅ Слова удалены: {', '.join(result)}",
            reply_markup=get_main_menu_keyboard()
        )
    else:
        bot.send_message(
            message.chat.id,
            "❌ Таких слов нет в вашем списке ключевых слов",
            reply_markup=get_main_menu_keyboard()
        )


@bot.message_handler(commands=['clear'])
def clear_keywords(message):
    """Очистить все ключевые слова (текстовая команда)"""
    if not get_user_keywords(message.chat.id):
        bot.send_message(
            message.chat.id,
            "ℹ️ Список уже пуст",
            reply_markup=get_main_menu_keyboard()
        )
        return
    clear_keywords_from_db(message.chat.id)
    clear_sent_news_from_db(message.chat.id)
    bot.send_message(
        message.chat.id,
        "🗑️ Все ключевые слова удалены",
        reply_markup=get_main_menu_keyboard()
    )


# ===== ОБРАБОТЧИКИ INLINE-КНОПОК =====

@bot.callback_query_handler(func=lambda call: call.data.startswith("menu_"))
def handle_menu_callbacks(call):
    """Обработчик кнопок главного меню"""
    
    if call.data == "menu_news":
        send_news(call.message)
        
    elif call.data == "menu_list":
        send_list(call.message)
        
    elif call.data == "menu_add":
        # Просим пользователя ввести слова
        msg = bot.send_message(
            call.message.chat.id,
            "✏️ Напишите ключевые слова через пробел:\n\n"
            "Пример: python docker fastapi\n\n"
            "Или нажмите /cancel для отмены."
        )
        # Регистрируем обработчик следующего сообщения
        bot.register_next_step_handler(msg, process_add_words)
        
    elif call.data == "menu_clear":
        # Показываем подтверждение перед очисткой
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton("✅ Да, очистить", callback_data="confirm_clear"),
            types.InlineKeyboardButton("❌ Отмена", callback_data="back_to_menu")
        )
        bot.send_message(
            call.message.chat.id,
            "⚠️ Вы уверены, что хотите удалить все ключевые слова?",
            reply_markup=keyboard
        )
    
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data == "confirm_clear")
def confirm_clear(call):
    """Подтверждение очистки всех слов"""
    if not get_user_keywords(call.message.chat.id):
        bot.send_message(
            call.message.chat.id,
            "ℹ️ Список уже пуст",
            reply_markup=get_main_menu_keyboard()
        )
    else:
        clear_keywords_from_db(call.message.chat.id)
        clear_sent_news_from_db(call.message.chat.id)
        bot.send_message(
            call.message.chat.id,
            "🗑️ Все ключевые слова удалены",
            reply_markup=get_main_menu_keyboard()
        )
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data == "back_to_menu")
def back_to_menu(call):
    """Возврат в главное меню"""
    send_welcome(call.message)
    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_"))
def handle_delete_keyword(call):
    """Удаление ключевого слова по клику на кнопку"""
    keyword = call.data.replace("delete_", "")
    
    delete_keywords_from_db(call.message.chat.id, [keyword])
    
    # Показываем уведомление и обновлённый список
    bot.answer_callback_query(call.id, f"✅ Слово '{keyword}' удалено")
    send_list(call.message)


@bot.message_handler(commands=['cancel'])
def cancel_action(message):
    """Отмена текущего действия"""
    bot.send_message(
        message.chat.id,
        "❌ Действие отменено",
        reply_markup=get_main_menu_keyboard()
    )


def process_add_words(message):
    """Обработка слов, введённых после нажатия кнопки 'Добавить'"""
    
    # Если пользователь ввёл /cancel
    if message.text and message.text.startswith('/'):
        bot.send_message(
            message.chat.id,
            "❌ Действие отменено",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    parts = [word.lower() for word in message.text.split()]
    
    if not parts:
        bot.send_message(
            message.chat.id,
            "❌ Вы не ввели слова. Попробуйте ещё раз:",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    keywords = get_user_keywords(message.chat.id)
    new_words = [word for word in parts if word not in keywords]
    
    if not new_words:
        bot.send_message(
            message.chat.id,
            "ℹ️ Все эти слова уже есть в вашем списке",
            reply_markup=get_main_menu_keyboard()
        )
        return
    
    add_keywords_to_db(message.chat.id, new_words)
    clear_sent_news_from_db(message.chat.id)  # Очищаем историю при добавлении
    
    bot.send_message(
        message.chat.id,
        f"✅ Слова добавлены: {', '.join(new_words)}",
        reply_markup=get_main_menu_keyboard()
    )


# ===== ФОНОВАЯ ПРОВЕРКА RSS =====

def check_rss_background():
    while True:
        try:
            response = requests.get(url)

            if response.status_code != 200:
                print(f"❌ Не удалось получить RSS. Код: {response.status_code}")
                time.sleep(1800)
                continue

            v = feedparser.parse(response.text)

            if not v.entries:
                print("❌ Лента новостей пуста")
                time.sleep(1800)
                continue

            for chat_id, keywords in get_all_users_with_keywords().items():
                if not keywords:
                    continue

                user_sent = get_sent_news_ids(chat_id)

                found_count = 0
                for entry in v.entries:
                    if entry.id in user_sent:
                        continue
                    title = str(entry.title).lower()
                    summary = str(entry.summary).lower()

                    for keyword in keywords:
                        if keyword in title or keyword in summary:
                            add_sent_news_to_db(chat_id, entry.id)
                            
                            news_text = (
                                f"✅ Найдено совпадение: {keyword}\n"
                                f"📰 {entry.title}"
                            )
                            
                            # Клавиатура с кнопкой-ссылкой
                            keyboard = types.InlineKeyboardMarkup()
                            keyboard.add(
                                types.InlineKeyboardButton("📖 Читать на Хабре", url=str(entry.link))
                            )
                            
                            bot.send_message(chat_id, news_text, reply_markup=keyboard)
                            found_count += 1
                            break

                if found_count > 0:
                    bot.send_message(
                        chat_id, f"📊 Всего найдено: {found_count} новостей")

            time.sleep(1800)

        except Exception as e:
            print(f"❌ Ошибка в фоновой проверке: {e}")
            time.sleep(1800)


# ===== ЗАПУСК БОТА =====

background_thread = threading.Thread(target=check_rss_background, daemon=True)
background_thread.start()
init_db()
print("🤖 Бот запущен и ожидает сообщений...")
bot.polling(none_stop=True)