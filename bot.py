import random
import string
import json
import time
import logging
import os
import asyncio

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.error import RetryAfter, TimedOut, NetworkError, TelegramError

logging.basicConfig(level=logging.INFO)

# ================== TOKEN ==================
BOT_TOKEN = os.environ.get("BOT_TOKEN")  # токен бота

ADMIN_ID = 6228421196
DB_FILE = "subscriptions.json"

# ================= АНТИ-БАН =================
# задержка между запросами get_chat
REQUEST_DELAY = 0.5

# ================= ЛОГ ПРОВЕРОК =================
checked_usernames_count = 0

# ================= БАЗА =================
def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_db():
    with open(DB_FILE, "w") as f:
        json.dump(db, f)

db = load_db()

# ================= ПОДПИСКА =================
def has_subscription(user_id):
    uid = str(user_id)
    expire = db.get(uid, 0)
    return expire > int(time.time())

def add_subscription(user_id, days):
    uid = str(user_id)
    now = int(time.time())
    current = db.get(uid, 0)
    if current > now:
        db[uid] = current + days * 86400
    else:
        db[uid] = now + days * 86400
    save_db()

def remove_subscription(user_id):
    db[str(user_id)] = 0
    save_db()

# ================= USERNAME =================
def generate_username(length=5):
    letters = string.ascii_lowercase
    if length == 5:
        mode = random.randint(1, 10)
        if mode <= 6:
            return ''.join(random.choice(letters) for _ in range(5))
        elif mode <= 8:
            a, b = random.choice(letters), random.choice(letters)
            return a + b + a + b + a
        elif mode == 9:
            c = random.choice(letters)
            return c * 5
        else:
            rare = "qxzjkv"
            return ''.join(random.choice(rare) for _ in range(5))
    else:  # для 6-буквенных
        return ''.join(random.choice(letters) for _ in range(6))

async def find_usernames(bot, amount=10, length=5, update: Update = None):
    found = []
    attempts = 0
    global checked_usernames_count
    while len(found) < amount and attempts < 2000:
        username = generate_username(length)
        attempts += 1
        try:
            await bot.get_chat(f"@{username}")
            checked_usernames_count += 1
        except TelegramError:
            if username not in found:
                found.append(username)
                checked_usernames_count += 1
        # каждые 5 проверок обновляем сообщение
        if update and attempts % 5 == 0:
            try:
                await update.callback_query.message.edit_text(
                    f"🔍 Проверяю username... Найдено {len(found)}/{amount}"
                )
            except:
                pass
        await asyncio.sleep(REQUEST_DELAY)
    return found[:amount]

# ================= СТАТИСТИКА =================
def get_stats():
    total = len(db)
    active = sum(1 for u in db if db[u] > time.time())
    expired = total - active
    return total, active, expired

# ================= МЕНЮ =================
def menu(user_id):
    keyboard = [
        [InlineKeyboardButton("🎲 5-буквенные", callback_data="gen5")],
        [InlineKeyboardButton("🎯 6-буквенные", callback_data="gen6")],
        [InlineKeyboardButton("💎 Купить подписку", callback_data="buy")],
        [InlineKeyboardButton("📅 Статус подписки", callback_data="status")]
    ]
    if user_id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("⚙️ Админ панель", callback_data="admin")])
    return InlineKeyboardMarkup(keyboard)

def admin_menu():
    keyboard = [
        [
            InlineKeyboardButton("👥 Пользователи", callback_data="users"),
            InlineKeyboardButton("📊 Статистика", callback_data="stats")
        ],
        [
            InlineKeyboardButton("💎 Добавить подписку", callback_data="addsub"),
            InlineKeyboardButton("❌ Убрать подписку", callback_data="removesub")
        ],
        [
            InlineKeyboardButton("⬅ Назад", callback_data="back")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if str(user_id) not in db:
        db[str(user_id)] = 0
        save_db()
    await update.message.reply_text(
        "🤖 Бот генерации username",
        reply_markup=menu(user_id)
    )

# ================= КНОПКИ =================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    # ================= Пользовательские кнопки =================
    if query.data == "buy":
        await query.message.edit_text(
            "Напишите @wvmmy для покупки\nЦена: 100 после 75 а уже после 3 покупки 50 руб / месяц",
            reply_markup=menu(user_id)
        )
    elif query.data == "status":
        expire = db.get(str(user_id), 0)
        if expire > time.time():
            seconds_left = expire - time.time()
            days = int(seconds_left // 86400)
            hours = int((seconds_left % 86400) // 3600)
            text = f"💎 Подписка активна\nОсталось: {days} д. {hours} ч."
        else:
            text = "❌ Подписки нет"
        await query.message.edit_text(text, reply_markup=menu(user_id))
    elif query.data in ["gen5", "gen6"]:
        if not has_subscription(user_id):
            await query.message.edit_text(
                "❌ Генерация доступна только по подписке",
                reply_markup=menu(user_id)
            )
            return
        length = 5 if query.data == "gen5" else 6
        await query.message.edit_text(f"🔍 Ищу свободные {length}-буквенные username...")
        usernames = await find_usernames(context.bot, 10, length, update)
        if usernames:
            text = f"🎯 Свободные {length}-буквенные username:\n\n" + "\n".join(f"@{u}" for u in usernames)
        else:
            text = "❌ Не удалось найти"
        await query.message.edit_text(text, reply_markup=menu(user_id))

    # ================= Админ-панель =================
    elif query.data == "admin" and user_id == ADMIN_ID:
        await query.message.edit_text("⚙️ Админ панель", reply_markup=admin_menu())
    elif query.data == "users" and user_id == ADMIN_ID:
        await query.message.edit_text(f"👥 Пользователей: {len(db)}", reply_markup=admin_menu())
    elif query.data == "stats" and user_id == ADMIN_ID:
        total, active, expired = get_stats()
        text = f"""
📊 СТАТИСТИКА БОТА

👥 Пользователей: {total}
💎 Активных подписок: {active}
❌ Без подписки: {expired}
🔍 Проверено username: {checked_usernames_count}

🕒 {time.strftime("%H:%M:%S")}
"""
        await query.message.edit_text(text, reply_markup=admin_menu())
    elif query.data == "addsub" and user_id == ADMIN_ID:
        await query.message.edit_text("Используйте команду /givesub USER_ID DAYS", reply_markup=admin_menu())
    elif query.data == "removesub" and user_id == ADMIN_ID:
        await query.message.edit_text("Используйте команду /removesub USER_ID", reply_markup=admin_menu())
    elif query.data == "back" and user_id == ADMIN_ID:
        await query.message.edit_text("Главное меню", reply_markup=menu(user_id))

# ================= АДМИН КОМАНДЫ =================
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
