import random
import string
import json
import time
import asyncio
import logging
import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.error import BadRequest

logging.basicConfig(level=logging.INFO)

# ================== ЗАГРУЗКА ТОКЕНА ==================
BOT_TOKEN = os.getenv("8525866998:AAEYebntrTi01nBgeoFkSRq6oHLcW-lGPw4")  # имя переменной окружения
if not BOT_TOKEN:
    raise ValueError("❌ Токен не найден! Установите переменную окружения BOT_TOKEN")

ADMIN_ID = 6228421196
DB_FILE = "subscriptions.json"

# ================= БАЗА =================

def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_db():
    with open(DB_FILE, "w") as f:
        json.dump(db, f)

db = load_db()

def has_subscription(user_id):
    uid = str(user_id)
    return uid in db and db[uid] > time.time()

def add_subscription(user_id, days):
    db[str(user_id)] = int(time.time()) + days * 86400
    save_db()

def remove_subscription(user_id):
    db[str(user_id)] = 0
    save_db()

# ================= USERNAME =================

def generate_username():
    return ''.join(random.choice(string.ascii_lowercase) for _ in range(5))

async def check_username(bot, username):
    try:
        await bot.get_chat(f"@{username}")
        return False
    except:
        return True

async def find_usernames(bot, amount=5):
    found = []
    checked = set()
    while len(found) < amount and len(checked) < 5000:
        username = generate_username()
        if username in checked:
            continue
        checked.add(username)
        if await check_username(bot, username):
            found.append(username)
    return found

# ================= МЕНЮ =================

def menu(user_id):
    keyboard = [
        [InlineKeyboardButton("🎲 Сгенерировать", callback_data="gen")],
        [InlineKeyboardButton("💎 Купить подписку", callback_data="buy")],
        [InlineKeyboardButton("📅 Статус подписки", callback_data="status")]
    ]
    if user_id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("⚙️ Админ панель", callback_data="admin")])
    return InlineKeyboardMarkup(keyboard)

def admin_menu():
    keyboard = [
        [InlineKeyboardButton("👥 Пользователи", callback_data="users")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")],
        [InlineKeyboardButton("⬅ Назад", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if str(user_id) not in db:
        db[str(user_id)] = 0
        save_db()
    await update.message.reply_text(
        "🤖 Бот генерации 5-буквенных username",
        reply_markup=menu(user_id)
    )

# ================= КНОПКИ =================

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "buy":
        await query.message.edit_text(
            "Напишите @wvmmy для покупки\nЦена: 50 руб / месяц",
            reply_markup=menu(user_id)
        )
    elif query.data == "status":
        if has_subscription(user_id):
            days = int((db[str(user_id)] - time.time()) / 86400)
            text = f"💎 Подписка активна\nОсталось дней: {days}"
        else:
            text = "❌ Подписки нет"
        await query.message.edit_text(text, reply_markup=menu(user_id))
    elif query.data == "gen":
        if not has_subscription(user_id):
            await query.message.edit_text(
                "❌ Генерация доступна только по подписке",
                reply_markup=menu(user_id)
            )
            return
        await query.message.edit_text("🔍 Ищу свободные username...")
        usernames = await find_usernames(context.bot)
        if usernames:
            text = "🎯 Свободные username:\n\n" + "\n".join(f"@{u}" for u in usernames)
        else:
            text = "❌ Не удалось найти"
        await query.message.edit_text(text, reply_markup=menu(user_id))
    elif query.data == "admin" and user_id == ADMIN_ID:
        await query.message.edit_text("⚙️ Админ панель", reply_markup=admin_menu())
    elif query.data == "users" and user_id == ADMIN_ID:
        await query.message.edit_text(f"👥 Пользователей: {len(db)}", reply_markup=admin_menu())
    elif query.data == "stats" and user_id == ADMIN_ID:
        active = sum(1 for u in db if db[u] > time.time())
        await query.message.edit_text(
            f"📊 Статистика\n\nВсего: {len(db)}\nПодписок: {active}",
            reply_markup=admin_menu()
        )
    elif query.data == "back":
        await query.message.edit_text("Главное меню", reply_markup=menu(user_id))

# ================= АДМИН =================

async def givesub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if len(context.args) != 2:
        await update.message.reply_text("/givesub USER_ID DAYS")
        return
    user = int(context.args[0])
    days = int(context.args[1])
    add_subscription(user, days)
    await update.message.reply_text("✅ Подписка выдана")

async def removesub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if len(context.args) != 1:
        await update.message.reply_text("/removesub USER_ID")
        return
    user = int(context.args[0])
    remove_subscription(user)
    await update.message.reply_text("❌ Подписка удалена")

# ================= ЗАПУСК =================

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("givesub", givesub))
    app.add_handler(CommandHandler("removesub", removesub))
    app.add_handler(CallbackQueryHandler(buttons))
    print("Бот запущен")
    app.run_polling()

if __name__ == "__main__":
    main()
