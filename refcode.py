import logging  # Бібліотека для налаштування логування, що допомагає відслідковувати роботу програми
from telegram import Update  # Клас Update, який представляє дані про оновлення від користувача
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters  # Інструменти для створення і налаштування бота
import sqlite3  # Бібліотека для роботи з базою даних SQLite
import string  # Бібліотека для обробки рядків, використовується для генерації реферального коду
import random  # Бібліотека для роботи з випадковими числами, також для генерації реферального коду
from datetime import datetime  # Клас для роботи з датою і часом
from typing import List, Tuple  # Типи для покращення читабельності та автопідказок в коді

# Налаштування логування: формат і рівень, які контролюють повідомлення в консолі під час виконання
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Константа з юзернеймом бота
BOT_USERNAME = 'EquaSolveBot'

# Функція для генерації унікального реферального коду
def generate_ref_code(length=8):
    characters = string.ascii_letters + string.digits  # Символи, з яких складатиметься код
    return ''.join(random.choice(characters) for _ in range(length))  # Створення випадкового коду заданої довжини

 # Функція для створення бази даних SQLite для зберігання користувачів, якщо вона ще не існує
def setup_database():
    conn = sqlite3.connect('users.db')  # Підключення до бази даних
    cursor = conn.cursor()  # Створення курсора для виконання SQL-запитів
    cursor.execute('''  # SQL-запит для створення таблиці користувачів
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            ref_code TEXT UNIQUE,
            referred_by TEXT,
            join_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()  # Збереження змін у базі даних
    conn.close()  # Закриття з’єднання з базою даних

# Нові функції для роботи з базою даних
def get_all_users() -> List[Tuple]:
    """
    Отримати всіх користувачів з бази даних
    """
    conn = sqlite3.connect('users.db')  # Підключення до бази даних
    cursor = conn.cursor()  # Створення курсора
    
    cursor.execute('''  # SQL-запит для вибору всіх користувачів з бази
        SELECT user_id, username, ref_code, referred_by, join_date
        FROM users
        ORDER BY join_date DESC
    ''')
    
    users = cursor.fetchall()  # Отримання всіх рядків із запиту
    conn.close()  # Закриття з’єднання
    
    return users  # Повернення списку користувачів

def get_user_referrals(user_id: int) -> dict:
    """
    Отримати детальну інформацію про реферальну систему користувача
    """
    conn = sqlite3.connect('users.db')  # Підключення до бази даних
    cursor = conn.cursor()  # Створення курсора
    
    cursor.execute('''  # Запит для отримання інформації про користувача
        SELECT username, ref_code, referred_by, join_date 
        FROM users 
        WHERE user_id = ?
    ''', (user_id,))
    user_info = cursor.fetchone()  # Отримання інформації про користувача
    
    if not user_info:  # Перевірка, чи користувач існує
        conn.close()
        return {"error": "Користувача не знайдено"}  # Повертає помилку, якщо користувача не знайдено
    
    username, ref_code, referred_by, join_date = user_info  # Розпаковка даних користувача
    
    cursor.execute('''  # Запит для отримання списку рефералів користувача
        SELECT username, user_id, join_date 
        FROM users 
        WHERE referred_by = ?
        ORDER BY join_date DESC
    ''', (ref_code,))
    referrals = cursor.fetchall()  # Отримання рефералів користувача
    
    # Структурування результатів
    result = {
        "user_info": {
            "user_id": user_id,
            "username": username,
            "ref_code": ref_code,
            "referred_by": referred_by,
            "join_date": join_date
        },
        "referrals_count": len(referrals),  # Підрахунок кількості рефералів
        "referrals": [{  # Форматування інформації про кожного реферала
            "username": ref[0],
            "user_id": ref[1],
            "join_date": ref[2]
        } for ref in referrals]
    }
    
    conn.close()  # Закриття з’єднання
    return result  # Повернення даних

# Команди бота
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id  # Отримання ID користувача
    username = update.effective_user.username  # Отримання username користувача
    
    # Отримання реферального коду, якщо він був переданий
    ref_code = None
    if context.args and len(context.args) > 0:
        ref_code = context.args[0]
    
    conn = sqlite3.connect('users.db')  # Підключення до бази даних
    cursor = conn.cursor()  # Створення курсора
    
    cursor.execute('SELECT ref_code FROM users WHERE user_id = ?', (user_id,))  # Перевірка наявності користувача
    existing_user = cursor.fetchone()
    
    if existing_user:  # Якщо користувач вже зареєстрований
        user_ref_code = existing_user[0]  # Отримуємо його реферальний код
        await update.message.reply_text(  # Відповідь користувачу з його реферальним кодом
            f"З поверненням! Ваш реферальний код: {user_ref_code}\n"
            f"Посилання для запрошення: https://t.me/{BOT_USERNAME}?start={user_ref_code}"
        )
    else:  # Якщо користувач не зареєстрований
        new_ref_code = generate_ref_code()  # Генеруємо новий реферальний код
        
        try:
            # Додаємо користувача до бази даних
            cursor.execute(
                'INSERT INTO users (user_id, username, ref_code, referred_by) VALUES (?, ?, ?, ?)',
                (user_id, username, new_ref_code, ref_code)
            )
            conn.commit()  # Збереження змін у базі даних
            
            # Повідомлення користувачу
            welcome_text = (
                f"Вітаємо! Ви успішно зареєстровані.\n"
                f"Ваш реферальний код: {new_ref_code}\n"
                f"Посилання для запрошення: https://t.me/{BOT_USERNAME}?start={new_ref_code}"
            )
            
            if ref_code:  # Якщо користувач був запрошений іншим користувачем
                welcome_text += "\nВи були запрошені користувачем з кодом: " + ref_code
            
            await update.message.reply_text(welcome_text)  # Відправка привітального повідомлення
            
        except sqlite3.IntegrityError:  # Обробка помилки при реєстрації
            await update.message.reply_text("Сталася помилка при реєстрації. Спробуйте ще раз.")
    
    conn.close()  # Закриття з’єднання з базою даних

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id  # Отримання ID користувача
    
    conn = sqlite3.connect('users.db')  # Підключення до бази даних
    cursor = conn.cursor()  # Створення курсора
    
    cursor.execute('''  # Запит для підрахунку рефералів користувача
        SELECT COUNT(*) FROM users 
        WHERE referred_by IN (
            SELECT ref_code FROM users WHERE user_id = ?
        )
    ''', (user_id,))
    
    referral_count = cursor.fetchone()[0]  # Отримання кількості рефералів
    
    await update.message.reply_text(f"Ви запросили {referral_count} користувачів!")  # Відправка статистики користувачу
    conn.close()  # Закриття з’єднання

async def mystats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id  # Отримання ID користувача
    referral_info = get_user_referrals(user_id)  # Отримання реферальної інформації
    
    if "error" in referral_info:  # Якщо користувача не знайдено
        await update.message.reply_text("Ви ще не зареєстровані. Використайте команду /start")
        return
    
    # Форматування повідомлення з інформацією про користувача
    message = f"📊 Ваша реферальна статистика:\n\n"
    message += f"🆔 Ваш ID: {referral_info['user_info']['user_id']}\n"
    message += f"👤 Ваш username: @{referral_info['user_info']['username'] if referral_info['user_info']['username'] else 'Невідомо'}\n"
    message += f"🎯 Ваш реферальний код: {referral_info['user_info']['ref_code']}\n"
    message += f"📅 Дата реєстрації: {referral_info['user_info']['join_date']}\n"
    
    # Перевірка, чи користувача запросив інший користувач
    if referral_info['user_info']['referred_by']:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT username FROM users WHERE ref_code = ?', (referral_info['user_info']['referred_by'],))
        referrer = cursor.fetchone()
        conn.close()
        if referrer and referrer[0]:
            message += f"👥 Вас запросив: @{referrer[0]}\n"
    
    # Додаємо інформацію про рефералів
    message += f"\n📈 Кількість рефералів: {referral_info['referrals_count']}\n"
    
    if referral_info['referrals']:  # Перевірка наявності рефералів
        message += "\n🔍 Список ваших рефералів:\n"
        for i, ref in enumerate(referral_info['referrals'], 1):  # Перерахування рефералів
            message += f"{i}. @{ref['username'] if ref['username'] else f'ID: {ref['user_id']}'} - {ref['join_date']}\n"
    
    await update.message.reply_text(message)  # Відправка повідомлення з статистикою

# Нова команда для адміністраторів для перегляду всіх користувачів
async def allusers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Тут можна додати перевірку на адміністратора
    users = get_all_users()  # Отримання всіх користувачів
    
    if not users:  # Якщо в базі даних немає користувачів
        await update.message.reply_text("База даних порожня")
        return
    
    # Форматування повідомлення з усіма користувачами
    message = "📊 Всі користувачі в базі даних:\n\n"
    for user in users:
        message += f"ID: {user[0]}, @{user[1] if user[1] else 'Невідомо'}\n"
        message += f"Реф.код: {user[2]}, Запрошений: {user[3] if user[3] else 'Немає'}\n"
        message += f"Дата реєстрації: {user[4]}\n\n"
        
        # Telegram має обмеження на довжину повідомлення, тому розбиваємо повідомлення, якщо воно занадто довге
        if len(message) > 3500:
            await update.message.reply_text(message)
            message = "Продовження списку:\n\n"
    
    if message:  # Відправка останньої частини повідомлення
        await update.message.reply_text(message)

def main():
    setup_database()  # Ініціалізація бази даних
    
    # Створення екземпляру бота та передача токену для аутентифікації
    app = ApplicationBuilder().token('7388192040:AAE6ySUHROsj21UOZkSxs4uOmdVnRrKTmC4').build()
    
    # Додаємо обробники команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("mystats", mystats))
    app.add_handler(CommandHandler("allusers", allusers))  # Нова команда
    
    app.run_polling()  # Запуск бота в режимі опитування

if __name__ == '__main__':
    main()  # Виконання основної функції, коли скрипт запускається напряму
