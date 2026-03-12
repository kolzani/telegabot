import datetime
import aiosqlite
import random
import string
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
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
    await msg.answer("Привет! Я бот для поиска свободных username. Выбери команду из меню.")

# Обработчик кнопки "Найти username"
@dp.message_handler(lambda message: message.text == "🔎 Найти username")
async def find_username(msg: types.Message):
    if not await check_subscription(msg.from_user.id):
        await msg.answer("❌ У вас нет подписки. Пожалуйста, купите подписку, чтобы искать username.")
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
        await msg.answer(f"Вот 5 доступных username:\n@{', @'.join(usernames)}")
    else:
        await msg.answer("❌ Не удалось найти свободные username после 100 попыток. Попробуйте позже.")

# Обработчик кнопки "Купить подписку"
@dp.message_handler(lambda message: message.text == "💎 Купить подписку")
async def buy_subscription(msg: types.Message):
    await msg.answer(
        "💎 Купить подписку можно у @wvmmy.\n1 покупка — 100₽\n2 покупка — 75₽\n3+ — 50₽/мес."
    )

# Статус подписки
@dp.message_handler(lambda message: message.text == "📊 Статус подписки")
async def subscription_status(msg: types.Message):
    status = await get_subscription_status(msg.from_user.id)
    await msg.answer(status)

# Статистика
@dp.message_handler(lambda message: message.text == "📊 Статистика")
async def stats(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        await msg.answer("❌ Вы не администратор.")
        return

    async with aiosqlite.connect("database.db") as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            total_users = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM users WHERE sub_until IS NOT NULL") as cur:
            subscribed_users = (await cur.fetchone())[0]
    
    await msg.answer(f"Общее количество пользователей: {total_users}\nПользователей с подпиской: {subscribed_users}")

# Выдача подписки
@dp.message_handler(lambda message: message.text == "🔒 Выдать подписку")
async def give_subscription(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        await msg.answer("❌ Вы не администратор.")
        return

    # Попросим администратора ввести ID пользователя для подписки
    await msg.answer("Пожалуйста, введите ID пользователя и на сколько месяцев нужно выдать подписку (например: /id <user_id> 3)", reply_markup=generate_id_button())

# Обработчик ввода ID для подписки
@dp.message_handler(lambda message: message.text.startswith("/id"))
async def input_id_for_subscription(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        await msg.answer("❌ Вы не администратор.")
        return

    try:
        user_id, months = int(msg.text.split()[1]), int(msg.text.split()[2])  # получаем ID и месяцы
    except (IndexError, ValueError):
        await msg.answer("❌ Неверный формат. Используйте команду в формате: /id <user_id> <months>")
        return

    await add_subscription(user_id, months)
    await msg.answer(f"✅ Подписка успешно выдана пользователю {user_id} на {months} месяцев.")

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

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_db())  # Инициализация базы данных перед запуском бота
    executor.start_polling(dp, skip_updates=True)
