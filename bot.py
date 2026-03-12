import asyncio
import datetime
import aiosqlite
import random
import string
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor

# Токен и ID админа
TOKEN = '8648186725:AAG8LqXwmsyEevpBDmi08wf6FCXXAOQq9pU'  # Вставь свой токен
ADMIN_ID = 6228421196  # Вставь свой ID (можно узнать через @userinfobot)

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# Инициализация базы данных
async def init_db():
    async with aiosqlite.connect("database.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                sub_until TEXT
            )
        """)
        await db.commit()
    print("Database initialized successfully.")

# Генерация случайных 5-значных username
def generate_usernames(count=5):
    return [''.join(random.choice(string.ascii_lowercase) for _ in range(5)) for _ in range(count)]

# Проверка доступности username
async def is_username_available(username):
    try:
        # Попробуем получить информацию о пользователе по username
        await bot.get_chat(username)
        return False
    except:
        return True

# Добавление подписки (сохранение даты окончания подписки)
async def add_subscription(user_id, months=1):
    sub_end = datetime.datetime.now() + datetime.timedelta(days=30 * months)
    async with aiosqlite.connect("database.db") as db:
        await db.execute("INSERT OR REPLACE INTO users (id, sub_until) VALUES (?, ?)", (user_id, sub_end.strftime("%Y-%m-%d %H:%M:%S")))
        await db.commit()

# Проверка подписки
async def check_subscription(user_id):
    async with aiosqlite.connect("database.db") as db:
        async with db.execute("SELECT sub_until FROM users WHERE id=?", (user_id,)) as cur:
            data = await cur.fetchone()
    if not data or not data[0]:
        return False
    sub_end = datetime.datetime.strptime(data[0], "%Y-%m-%d %H:%M:%S")  # Используем точный формат
    return datetime.datetime.now() < sub_end  # Проверка с точным временем

# Статус подписки
async def get_subscription_status(user_id):
    async with aiosqlite.connect("database.db") as db:
        async with db.execute("SELECT sub_until FROM users WHERE id=?", (user_id,)) as cur:
            data = await cur.fetchone()
    if data:
        try:
            sub_end = datetime.datetime.strptime(data[0], "%Y-%m-%d %H:%M:%S")
            return f"Подписка активна до {sub_end.strftime('%Y-%m-%d %H:%M:%S')}"
        except ValueError:
            return "❌ Подписка имеет неверный формат."
    return "Подписка отсутствует."

# Основной обработчик команды /start
@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    # Главное меню с кнопками
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🔎 Найти username", callback_data="find_usernames"),
        InlineKeyboardButton("💎 Купить подписку", callback_data="buy_subscription"),
        InlineKeyboardButton("📊 Статус подписки", callback_data="check_subscription")
    )
    
    # Если администратор, добавляем кнопку для статистики
    if msg.from_user.id == ADMIN_ID:
        keyboard.add(
            InlineKeyboardButton("📊 Статистика", callback_data="view_stats"),
            InlineKeyboardButton("🔒 Админ Панель", callback_data="admin_panel")
        )

    await msg.answer("Привет! Я бот для поиска свободных username. Выбери команду из меню.", reply_markup=keyboard)

# Обработчик кнопки "Найти username"
@dp.callback_query_handler(lambda c: c.data == "find_usernames")
async def find_username(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    if not await check_subscription(user_id):
        await bot.answer_callback_query(callback_query.id, "❌ У вас нет подписки. Пожалуйста, купите подписку, чтобы искать username.")
        await bot.send_message(user_id, "❌ Подписка отсутствует. Пожалуйста, купите подписку.")
        return

    usernames = []
    attempts = 0

    while len(usernames) < 5 and attempts < 100:
        username = generate_usernames(count=1)[0]
        available = await is_username_available(f"@{username}")
        if available:
            usernames.append(username)
        attempts += 1

    if len(usernames) > 0:
        await bot.answer_callback_query(callback_query.id, f"Вот 5 доступных username:\n@{', @'.join(usernames)}")
        await bot.send_message(callback_query.from_user.id, f"Вот 5 доступных username:\n@{', @'.join(usernames)}")
    else:
        await bot.answer_callback_query(callback_query.id, "❌ Не удалось найти свободные username после 100 попыток. Попробуйте позже.")
        await bot.send_message(callback_query.from_user.id, "❌ Не удалось найти свободные username после 100 попыток. Попробуйте позже.")

# Обработчик кнопки "Купить подписку"
@dp.callback_query_handler(lambda c: c.data == "buy_subscription")
async def buy_subscription(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id, "💎 Купить подписку можно у @wvmmy.\n1 покупка — 100₽\n2 покупка — 75₽\n3+ — 50₽/мес.")
    await bot.send_message(callback_query.from_user.id, "💎 Купить подписку можно у @wvmmy.\n1 покупка — 100₽\n2 покупка — 75₽\n3+ — 50₽/мес.")

# Статус подписки
@dp.callback_query_handler(lambda c: c.data == "check_subscription")
async def subscription_status(callback_query: types.CallbackQuery):
    status = await get_subscription_status(callback_query.from_user.id)
    await bot.answer_callback_query(callback_query.id, status)
    await bot.send_message(callback_query.from_user.id, status)

# Статистика
@dp.callback_query_handler(lambda c: c.data == "view_stats")
async def stats(callback_query: types.CallbackQuery):
    if callback_query.from_user.id != ADMIN_ID:
        await bot.answer_callback_query(callback_query.id, "❌ Вы не администратор.")
        await bot.send_message(callback_query.from_user.id, "❌ Вы не администратор.")
        return

    async with aiosqlite.connect("database.db") as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            total_users = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM users WHERE sub_until IS NOT NULL") as cur:
            subscribed_users = (await cur.fetchone())[0]
    
    await bot.answer_callback_query(callback_query.id, f"Общее количество пользователей: {total_users}\nПользователей с подпиской: {subscribed_users}")
    await bot.send_message(callback_query.from_user.id, f"Общее количество пользователей: {total_users}\nПользователей с подпиской: {subscribed_users}")

# Админ панель для управления подписками
@dp.callback_query_handler(lambda c: c.data == "admin_panel")
async def admin_panel(callback_query: types.CallbackQuery):
    if callback_query.from_user.id != ADMIN_ID:
        await bot.answer_callback_query(callback_query.id, "❌ Вы не администратор.")
        await bot.send_message(callback_query.from_user.id, "❌ Вы не администратор.")
        return
    
    # Кнопки для админа
    admin_keyboard = InlineKeyboardMarkup(row_width=2)
    admin_keyboard.add(
        InlineKeyboardButton("🔑 Выдать подписку", callback_data="give_subscription"),
        InlineKeyboardButton("❌ Убрать подписку", callback_data="remove_subscription"),
        InlineKeyboardButton("🔙 Назад в меню", callback_data="back_to_menu")
    )
    
    await bot.answer_callback_query(callback_query.id, "Админ панель: выберите действие", reply_markup=admin_keyboard)
    await bot.send_message(callback_query.from_user.id, "Админ панель: выберите действие")

# Выдача подписки
@dp.callback_query_handler(lambda c: c.data == "give_subscription")
async def give_subscription(callback_query: types.CallbackQuery):
    if callback_query.from_user.id != ADMIN_ID:
        await bot.answer_callback_query(callback_query.id, "❌ Вы не администратор.")
        await bot.send_message(callback_query.from_user.id, "❌ Вы не администратор.")
        return

    await bot.answer_callback_query(callback_query.id, "Введите ID пользователя и срок подписки в месяцах (например: 123456789 3
