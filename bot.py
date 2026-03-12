import random
import string
import json
import time
import logging
import os
import asyncio

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters
from telegram.error import RetryAfter, TimedOut, NetworkError, BadRequest

logging.basicConfig(level=logging.INFO)

# ================== TOKEN ==================
BOT_TOKEN = os.environ.get("BOT_TOKEN")  # через Railway Shared Variable / REF

ADMIN_ID = 6228421196
DB_FILE = "subscriptions.json"

# ================= АНТИ-БАН =================
semaphore = asyncio.Semaphore(3)

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
def generate_username():
    letters = string.ascii_lowercase
    mode = random.randint(1, 10)
    if mode <= 6:
        return ''.join(random.choice(letters) for _ in range(5))
    elif mode <= 8:
        a = random.choice(letters)
        b = random.choice(letters)
        return a + b + a + b + a
    elif mode == 9:
        c = random.choice(letters)
        return c * 5
    else:
        rare = "qxzjkv"
        return ''.join(random.choice(rare) for _ in range(5))

# ================= ПРОВЕРКА USERNAME =================
async def check_username(bot, username):
    global checked_usernames_count
    async with semaphore:
        try:
            await bot.get_chat(f"@{username}")
            return False
        except RetryAfter as e:
            await asyncio.sleep(e.retry_after)
            return False
        except (TimedOut, NetworkError):
            await asyncio.sleep(1)
            return False
        except Exception:
            checked_usernames_count += 1
            return True

async def check_batch(bot, usernames):
    tasks = [check_username(bot, u) for u in usernames]
    results = await asyncio.gather(*tasks)
    free = [usernames[i] for i, res in enumerate(results) if res]
    return free

async def find_usernames(bot, amount=10):
    found = []
    while len(found) < amount:
        batch = [generate_username() for _ in range(10)]
        free = await check_batch(bot, batch)
        for u in free:
            if u not in found:
                found.append(u)
        await asyncio.sleep(random.uniform(0.5, 1.0))
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
        [InlineKeyboardButton("🎲 Сгенерировать", callback_data="gen")],
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
            InlineKeyboardButton("💎 Подписки", callback_data="subs"),
            InlineKeyboardButton("📈 Лог username", callback_data="log")
        ],
        [
            InlineKeyboardButton("➕ Добавить подписку", callback_data="addsub"),
            InlineKeyboardButton("➖ Убрать подписку", callback_data="remsub")
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
        "🤖 Бот генерации 5-буквенных username",
        reply_markup=menu(user_id)
    )

# ================= КНОПКИ =================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    try:
        if query.data == "gen":
            if not has_subscription(user_id):
                await query.message.edit_text(
                    "❌ Генерация доступна только по подписке",
                    reply_markup=menu(user_id)
                )
                return
            await query.message.edit_text("🔍 Ищу свободные username...")
            usernames = await find_usernames(context.bot, 10)
            text = "🎯 Свободные username:\n\n" + "\n".join(f"@{u}" for u in usernames) if usernames else "❌ Не удалось найти свободные username"
            try:
                await query.message.edit_text(text, reply_markup=menu(user_id))
            except BadRequest as e:
                if "Message is not modified" in str(e):
                    pass
                else:
                    raise

        elif query.data == "buy":
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

        elif query.data == "log" and user_id == ADMIN_ID:
            await query.message.edit_text(f"🔍 Проверено username: {checked_usernames_count}", reply_markup=admin_menu())

        elif query.data == "addsub" and user_id == ADMIN_ID:
            await query.message.reply_text("Введите USER_ID DAYS\nНапример: 6228421196 30")
            context.user_data["action"] = "addsub"

        elif query.data == "remsub" and user_id == ADMIN_ID:
            await query.message.reply_text("Введите USER_ID для удаления подписки\nНапример: 6228421196")
            context.user_data["action"] = "remsub"

        elif query.data == "back":
            await query.message.edit_text("Главное меню", reply_markup=menu(user_id))

    except BadRequest as e:
        if "Message is not modified" in str(e):
            pass
        else:
            raise

# ================= АДМИН ВВОД =================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return

    if "action" not in context.user_data:
        return

    text = update.message.text.strip()

    if context.user_data["action"] == "addsub":
        try:
            parts = text.split()
            uid = int(parts[0])
            days = int(parts[1])
            add_subscription(uid, days)
            await update.message.reply_text(f"✅ Подписка на {days} дн. выдана пользователю {uid}")
        except:
            await update.message.reply_text("❌ Ошибка! Введите USER_ID и DAYS через пробел.")
        context.user_data.pop("action")

    elif context.user_data["action"] == "remsub":
        try:
            uid = int(text)
            remove_subscription(uid)
            await update.message.reply_text(f"❌ Подписка удалена у пользователя {uid}")
        except:
            await update.message.reply_text("❌ Ошибка! Введите правильный USER_ID.")
        context.user_data.pop("action")

# ================= ЗАПУСК =================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))  # ловим текст админа

    print("Бот запущен")
    app.run_polling()  # без while True, polling сам перезапускается

if __name__ == "__main__":
    main()
