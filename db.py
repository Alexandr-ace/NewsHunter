import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# Читаем настройки БД из .env
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")


def get_db_connection():
    """Создать соединение с базой данных"""
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )


def init_db():
    """Создать таблицы, если их нет"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_keywords (
            chat_id BIGINT,
            keyword TEXT,
            PRIMARY KEY (chat_id, keyword)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sent_news (
            chat_id BIGINT,
            news_id TEXT,
            PRIMARY KEY (chat_id, news_id)
        )
    """)
    
    conn.commit()
    cursor.close()
    conn.close()
    print("✅ База данных инициализирована")


# ===== Функции для работы с ключевыми словами =====

def get_user_keywords(chat_id):
    """Получить список ключевых слов пользователя из БД"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT keyword FROM user_keywords WHERE chat_id = %s", (chat_id,))
    keywords = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    return keywords


def add_keywords_to_db(chat_id, keywords_list):
    """Добавить ключевые слова в БД"""
    conn = get_db_connection()
    cursor = conn.cursor()
    for keyword in keywords_list:
        cursor.execute(
            "INSERT INTO user_keywords (chat_id, keyword) VALUES (%s, %s) ON CONFLICT DO NOTHING",
            (chat_id, keyword)
        )
    conn.commit()
    cursor.close()
    conn.close()


def delete_keywords_from_db(chat_id, keywords_list):
    """Удалить ключевые слова из БД"""
    conn = get_db_connection()
    cursor = conn.cursor()
    for keyword in keywords_list:
        cursor.execute(
            "DELETE FROM user_keywords WHERE chat_id = %s AND keyword = %s",
            (chat_id, keyword)
        )
    conn.commit()
    cursor.close()
    conn.close()


def clear_keywords_from_db(chat_id):
    """Удалить все ключевые слова пользователя из БД"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM user_keywords WHERE chat_id = %s", (chat_id,))
    conn.commit()
    cursor.close()
    conn.close()


# ===== Функции для работы с отправленными новостями =====
def get_all_users_with_keywords():
    """Получить словарь {chat_id: [keywords]} для всех пользователей из БД"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Получаем все записи из таблицы
    cursor.execute("SELECT chat_id, keyword FROM user_keywords")
    rows = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    # Группируем по chat_id
    users = {}
    for chat_id, keyword in rows:
        if chat_id not in users:
            users[chat_id] = []
        users[chat_id].append(keyword)
    
    return users

def get_sent_news_ids(chat_id):
    """Получить множество ID отправленных новостей"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT news_id FROM sent_news WHERE chat_id = %s", (chat_id,))
    news_ids = set(row[0] for row in cursor.fetchall())
    cursor.close()
    conn.close()
    return news_ids


def add_sent_news_to_db(chat_id, news_id):
    """Добавить ID отправленной новости в БД"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO sent_news (chat_id, news_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
        (chat_id, news_id)
    )
    conn.commit()
    cursor.close()
    conn.close()

def clear_sent_news_from_db(chat_id):
    """Удалить все ключевые слова пользователя из БД"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sent_news WHERE chat_id = %s", (chat_id,))
    conn.commit()
    cursor.close()
    conn.close()