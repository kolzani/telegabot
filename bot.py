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

BOT_TOKEN = os.getenv("8717987578:AAF1i8ycyaOrSlFlDS727OUcfqXLcAv7v9k")  # токен берём из переменной среды
ADMIN_ID = 6228421196                 # замени на свой ID
DB_FILE = "subscriptions.json"

# ================= БАЗА =================
def load_db():
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f)

db = load_db()

def has_subscription(user_id):
    user_id = str(user_id)
    return user_id in db and db[user_id] > time.time()

def add_subscription(user_id, days):
    expire = int(time.time()) + days * 86400
    db[str(user_id)] = expire
    save_db(db)

# ================= ЮЗЕРНЕЙМ =================
def generate_username(length=5):
    return ''.join(random.choice(string.ascii_lowercase) for _ in range(length))

async def check_username(bot, username):
    try:
        await bot.get_chat(f"@{username}")
        return False
    except BadRequest as e:
        if "Username not found" in str(e):
            return True
        return False

# ================= КНОПКИ =================
def menu():
    keyboard = [
        [InlineKeyboardButton("🎲 Сгенерировать", callback_data="gen")],
        [InlineKeyboardButton("💎 Купить подписку", callback_data="buy")],
        [InlineKeyboardButton("📅 Статус подписки", callback_data="status")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ================= КОМАНДЫ =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 Бот генерации 5-буквенных юзернеймов", reply_markup=menu())

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "buy":
        await query.message.edit_text("Напишите @wvmmy для покупки подписки на месяц, цена 50 руб.", reply_markup=menu())

    elif query.data == "status":
        if has_subscription(user_id):
            days = int((db[str(user_id)] - time.time()) / 86400)
            text = f"💎 Подписка активна\nОсталось дней: {days}"
        else:
            text = "❌ Подписки нет"
        await query.message.edit_text(text, reply_markup=menu())

    elif query.data == "gen":
        if not has_subscription(user_id):
            await query.message.edit_text("❌ Генерация доступна только по подписке", reply_markup=menu())
            return

        # Асинхронная генерация 20 юзернеймов сразу
        usernames = []
        attempts = 0
        while len(usernames) < 5 and attempts < 500:
            tasks = [check_username(context.bot, generate_username()) for _ in range(20)]
            results = await asyncio.gather(*tasks)
            for i, available in enumerate(results):
                if available:
                    usernames.append(generate_username())
                    if len(usernames) >= 5:
                        break
            attempts += 1

        text = "🎯 Свободные юзернеймы:\n\n" + "\n".join(f"@{u}" for u in usernames)
        await query.message.edit_text(text, reply_markup=menu())

# ================= АДМИН =================
async def givesub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        user_id = int(context.args[0])
        days = int(context.args[1])
        add_subscription(user_id, days)
        await update.message.reply_text("✅ Подписка выдана")
    except:
        await update.message.reply_text("Использование: /givesub USER_ID DAYS")

# ================= ЗАПУСК =================
def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("givesub", givesub))
    application.add_handler(CallbackQueryHandler(buttons))
    print("Bot started")
    application.run_polling()

if __name__ == "__main__":
    main()

