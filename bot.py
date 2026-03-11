import random
import string
import json
import time
import logging
import os
import asyncio

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.error import BadRequest

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

BOT_TOKEN = os.getenv("8717987578:AAF1i8ycyaOrSlFlDS727OUcfqXLcAv7v9k")  # Токен из переменных окружения
ADMIN_ID = 6228421196  # Заменить на свой Telegram ID
DB_FILE = "subscriptions.json"

# ======== Работа с подписками (файл JSON) ========
def load_db():
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)

db = load_db()

def has_subscription(user_id):
    user_id = str(user_id)
    return user_id in db and db[user_id] > time.time()

def add_subscription(user_id, days):
    expire = int(time.time()) + days * 86400
    db[str(user_id)] = expire
    save_db(db)

# ======== Генерация и проверка username ========
def generate_username(length=5):
    return ''.join(random.choice(string.ascii_lowercase) for _ in range(length))

async def check_username_availability(bot, username: str) -> bool:
    try:
        await bot.get_chat(f"@{username}")
        # Если чат с таким username найден — значит занят
        return False
    except BadRequest as e:
        if "Username not found" in str(e):
            # Свободен
            return True
        return False

# ======== Кнопки меню ========
def menu():
    keyboard = [
        [InlineKeyboardButton("🎲 Сгенерировать", callback_data="gen")],
        [InlineKeyboardButton("💎 Купить подписку", callback_data="buy")],
        [InlineKeyboardButton("📅 Статус подписки", callback_data="status")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ======== Обработчики команд ========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Бот генерации 5-буквенных юзернеймов\n"
        "Нажми кнопку для генерации или покупки подписки.",
        reply_markup=menu()
    )

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "buy":
        await query.message.edit_text(
            "Напишите @wvmmy для покупки подписки на месяц, цена 50 руб.",
            reply_markup=menu()
        )

    elif query.data == "status":
        if has_subscription(user_id):
            days = int((db[str(user_id)] - time.time()) / 86400)
            await query.message.edit_text(
                f"💎 Подписка активна\nОсталось дней: {days}",
                reply_markup=menu()
            )
        else:
            await query.message.edit_text(
                "❌ Подписки нет",
                reply_markup=menu()
            )

    elif query.data == "gen":
        if not has_subscription(user_id):
            await query.message.edit_text(
                "❌ Генерация доступна только по подписке",
                reply_markup=menu()
            )
            return

        available_usernames = []
        attempts = 0
        max_attempts = 500

        while len(available_usernames) < 5 and attempts < max_attempts:
            username = generate_username()
            if username not in available_usernames and await check_username_availability(context.bot, username):
                available_usernames.append(username)
            attempts += 1

        if available_usernames:
            text = "🎯 Свободные юзернеймы:\n\n" + "\n".join(f"@{u}" for u in available_usernames)
        else:
            text = "Не удалось найти свободные юзернеймы. Попробуйте позже."

        await query.message.edit_text(text, reply_markup=menu())

# ======== Админская команда выдачи подписки ========
async def givesub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if len(context.args) != 2:
        await update.message.reply_text("Использование: /givesub USER_ID DAYS")
        return

    try:
        user_id = int(context.args[0])
        days = int(context.args[1])
    except ValueError:
        await update.message.reply_text("USER_ID и DAYS должны быть числами")
        return

    add_subscription(user_id, days)
    await update.message.reply_text(f"✅ Подписка выдана пользователю {user_id} на {days} дней")

# ======== Запуск бота ========
def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("givesub", givesub))
    application.add_handler(CallbackQueryHandler(buttons))

    print("Бот запущен")
    application.run_polling()

if __name__ == "__main__":
    main()

