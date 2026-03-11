from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
import random
import string
import logging
import json
import time

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

BOT_TOKEN = "7841222200:AAHzJoRS1p5O_NyI0Px9XT8aW5b0LI9QGjA"
ADMIN_ID = 6228421196  # ID администратора

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
    if user_id in db:
        if db[user_id] > time.time():
            return True
    return False


def add_subscription(user_id, days):
    expire = int(time.time()) + days * 86400
    db[str(user_id)] = expire
    save_db(db)


# ================= ЮЗЕРНЕЙМ =================

def generate_username(length=5):
    chars = string.ascii_lowercase
    return ''.join(random.choice(chars) for _ in range(length))


async def check_username_availability(username):
    try:
        await application.bot.get_chat(f"@{username}")
        return False
    except:
        return True


# ================= КНОПКИ =================

def main_menu():
    keyboard = [
        [InlineKeyboardButton("🎲 Сгенерировать юзернеймы", callback_data="generate")],
        [InlineKeyboardButton("💎 Купить подписку", callback_data="buy")],
        [InlineKeyboardButton("📅 Статус подписки", callback_data="status")]
    ]

    return InlineKeyboardMarkup(keyboard)


# ================= КОМАНДЫ =================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = (
        "🤖 Бот для поиска свободных 5-буквенных юзернеймов\n\n"
        "Выберите действие:"
    )

    if update.message:
        await update.message.reply_text(text, reply_markup=main_menu())
    else:
        await update.callback_query.message.edit_text(text, reply_markup=main_menu())


# ================= КНОПКИ ОБРАБОТКА =================

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id

    if query.data == "buy":

        text = "Напишите @wvmmy для покупки подписки на месяц, цена 50 руб."

        await query.message.edit_text(text, reply_markup=main_menu())

    elif query.data == "status":

        if has_subscription(user_id):

            expire = db[str(user_id)]
            days = int((expire - time.time()) / 86400)

            text = f"💎 У вас есть подписка\nОсталось дней: {days}"

        else:

            text = "❌ У вас нет активной подписки"

        await query.message.edit_text(text, reply_markup=main_menu())

    elif query.data == "generate":

        if not has_subscription(user_id):

            await query.message.edit_text(
                "❌ Генерация доступна только по подписке",
                reply_markup=main_menu()
            )
            return

        available = []
        attempts = 0

        while len(available) < 5 and attempts < 500:

            username = generate_username()

            if await check_username_availability(username):
                if username not in available:
                    available.append(username)

            attempts += 1

        if available:

            text = "🎯 Свободные юзернеймы:\n\n"

            for u in available:
                text += f"@{u}\n"

        else:
            text = "Не удалось найти свободные."

        await query.message.edit_text(text, reply_markup=main_menu())


# ================= АДМИН =================

async def give_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if update.effective_user.id != ADMIN_ID:
        return

    try:

        user_id = int(context.args[0])
        days = int(context.args[1])

        add_subscription(user_id, days)

        await update.message.reply_text("✅ Подписка выдана")

    except:

        await update.message.reply_text(
            "Использование:\n/givesub USER_ID DAYS"
        )


# ================= ЗАПУСК =================

application = Application.builder().token(BOT_TOKEN).build()

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("givesub", give_sub))
application.add_handler(CallbackQueryHandler(buttons))

print("Бот запущен")

application.run_polling()
