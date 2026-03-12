import random
import string
import json
import time
import logging
import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.error import BadRequest

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

BOT_TOKEN = "8525866998:AAEYebntrTi01nBgeoFkSRq6oHLcW-lGPw4"
ADMIN_ID = 6228421196
DB_FILE = "subscriptions.json"

# ================= БАЗА =================

def load_db():
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)

db = load_db()

def has_subscription(user_id):
    user_id = str(user_id)
    return user_id in db and db[user_id] > time.time()

def add_subscription(user_id, days):
    expire = int(time.time()) + days * 86400
    db[str(user_id)] = expire
    save_db(db)

def remove_subscription(user_id):
    if str(user_id) in db:
        db[str(user_id)] = 0
        save_db(db)

# ================= USERNAME =================

def generate_username(length=5):
    return ''.join(random.choice(string.ascii_lowercase) for _ in range(length))

async def check_username_availability(bot, username: str) -> bool:
    try:
        await bot.get_chat(f"@{username}")
        return False
    except BadRequest as e:
        if "Username not found" in str(e):
            return True
        return False

# ================= МЕНЮ =================

def menu(user_id=None):

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
        [InlineKeyboardButton("👥 Пользователи", callback_data="admin_users")],
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("💎 Как выдать подписку", callback_data="admin_give")],
        [InlineKeyboardButton("❌ Как удалить подписку", callback_data="admin_remove")],
        [InlineKeyboardButton("⬅ Назад", callback_data="back")]
    ]

    return InlineKeyboardMarkup(keyboard)

# ================= START =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    user_id = update.effective_user.id

    if str(user_id) not in db:
        db[str(user_id)] = 0
        save_db(db)

    await update.message.reply_text(
        "🤖 Бот генерации 5-буквенных юзернеймов",
        reply_markup=menu(user_id)
    )

# ================= КНОПКИ =================

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    # купить
    if query.data == "buy":

        await query.message.edit_text(
            "Напишите @wvmmy для покупки подписки\nЦена: 50 руб / месяц",
            reply_markup=menu(user_id)
        )

    # статус
    elif query.data == "status":

        if has_subscription(user_id):

            days = int((db[str(user_id)] - time.time()) / 86400)

            await query.message.edit_text(
                f"💎 Подписка активна\nОсталось дней: {days}",
                reply_markup=menu(user_id)
            )

        else:

            await query.message.edit_text(
                "❌ Подписки нет",
                reply_markup=menu(user_id)
            )

    # генерация
    elif query.data == "gen":

        if not has_subscription(user_id):

            await query.message.edit_text(
                "❌ Генерация доступна только по подписке",
                reply_markup=menu(user_id)
            )
            return

        available = []
        checked = set()

        while len(available) < 5 and len(checked) < 2000:

            username = generate_username()

            if username in checked:
                continue

            checked.add(username)

            free = await check_username_availability(context.bot, username)

            if free:
                available.append(username)

        if available:

            text = "🎯 Свободные username:\n\n"

            for u in available:
                text += f"@{u}\n"

        else:

            text = "Не удалось найти свободные username"

        await query.message.edit_text(
            text,
            reply_markup=menu(user_id)
        )

    # ================= АДМИН =================

    elif query.data == "admin":

        if user_id != ADMIN_ID:
            return

        await query.message.edit_text(
            "⚙️ Админ панель",
            reply_markup=admin_menu()
        )

    elif query.data == "admin_users":

        if user_id != ADMIN_ID:
            return

        total = len(db)

        await query.message.edit_text(
            f"👥 Пользователей: {total}",
            reply_markup=admin_menu()
        )

    elif query.data == "admin_stats":

        if user_id != ADMIN_ID:
            return

        active = sum(1 for u in db if db[u] > time.time())

        await query.message.edit_text(
            f"📊 Статистика\n\n"
            f"Всего пользователей: {len(db)}\n"
            f"Активных подписок: {active}",
            reply_markup=admin_menu()
        )

    elif query.data == "admin_give":

        await query.message.edit_text(
            "Команда выдачи подписки:\n\n"
            "/givesub USER_ID DAYS",
            reply_markup=admin_menu()
        )

    elif query.data == "admin_remove":

        await query.message.edit_text(
            "Команда удаления подписки:\n\n"
            "/removesub USER_ID",
            reply_markup=admin_menu()
        )

    elif query.data == "back":

        await query.message.edit_text(
            "Главное меню",
            reply_markup=menu(user_id)
        )

# ================= АДМИН КОМАНДЫ =================

async def givesub(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    if len(context.args) != 2:
        await update.message.reply_text("Использование: /givesub USER_ID DAYS")
        return

    user_id = int(context.args[0])
    days = int(context.args[1])

    add_subscription(user_id, days)

    await update.message.reply_text(
        f"✅ Подписка выдана {user_id} на {days} дней"
    )

async def removesub(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    if len(context.args) != 1:
        await update.message.reply_text("Использование: /removesub USER_ID")
        return

    user_id = int(context.args[0])

    remove_subscription(user_id)

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

