import asyncio
import random
import string
import aiosqlite
import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils import executor
import logging

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен и ID админа
TOKEN = '8648186725:AAG8LqXwmsyEevpBDmi08wf6FCXXAOQq9pU'  # Вставь свой токен
ADMIN_ID = 6228421196  # Вставь свой ID (можно узнать через @userinfobot)

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# Клавиатуры
menu = ReplyKeyboardMarkup(resize_keyboard=True)
menu.add(KeyboardButton("🔎 Найти username"))
menu.add(KeyboardButton("💎 Купить подписку"))
menu.add(KeyboardButton("📊 Статус подписки"))
menu.add(KeyboardButton("⚙️ Админ панель"))

admin_menu = ReplyKeyboardMarkup(resize_keyboard=True)
admin_menu.add(KeyboardButton("📊 Статистика"))
admin_menu.add(KeyboardButton("🔒 Выдать подписку"))
admin_menu.add(KeyboardButton("❌ Убрать подписку"))
admin_menu.add(KeyboardButton("🚫 Завершить админ панель"))

# Генерация 5-значных username без цифр
def generate_usernames(count=5):
    return [''.join(random.choice(string.ascii_lowercase) for _ in range(5)) for _ in range(count)]

# Проверка доступности username
async def is_username_available(username):
    try:
        # Попробуем получить информацию о пользователе по username
        user = await bot.get_chat(username)
        # Если чат существует, значит username занят
        return False
    except:
        # Ошибка значит, что username свободен
        return True

# Проверка подписки
async def check_subscription(user_id):
    async with aiosqlite.connect("database.db") as db:
        async with db.execute("SELECT sub_until FROM users WHERE id=?", (user_id,)) as cur:
            data = await cur.fetchone()
    if not data or not data[0]:
        return False
    return datetime.datetime.now() < datetime.datetime.strptime(data[0], "%Y-%m-%d")

# Статус подписки
async def get_subscription_status(user_id):
    async with aiosqlite.connect("database.db") as db:
        async with db.execute("SELECT sub_until FROM users WHERE id=?", (user_id,)) as cur:
            data = await cur.fetchone()
    if data:
        return f"Подписка активна до {data[0]}"
    return "Подписка отсутствует"

# Добавление подписки
async def add_subscription(user_id, months=1):
    sub_end = datetime.datetime.now() + datetime.timedelta(days=30 * months)
    async with aiosqlite.connect("database.db") as db:
        await db.execute("INSERT OR REPLACE INTO users (id, sub_until) VALUES (?, ?)", (user_id, sub_end.strftime("%Y-%m-%d")))
        await db.commit()

# Админ панель
async def get_admin_stats():
    async with aiosqlite.connect("database.db") as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            total_users = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM users WHERE sub_until IS NOT NULL") as cur:
            subscribed_users = (await cur.fetchone())[0]
    return total_users, subscribed_users

# Генерация кнопки для ввода ID
def generate_id_button():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(InlineKeyboardButton("Введите ID пользователя", callback_data="enter_id"))
    return keyboard

# Обработчик команды /start
@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    await msg.answer("Привет! Я бот для поиска свободных username. Выбери команду из меню.", reply_markup=menu)

# Обработчик кнопки "Найти username"
@dp.message_handler(lambda message: message.text == "🔎 Найти username")
async def find_username(msg: types.Message):
    if not await check_subscription(msg.from_user.id):
        await msg.answer("❌ У вас нет подписки. Пожалуйста, купите подписку, чтобы искать username.")
        return

    usernames = []
    attempts = 0

    while len(usernames) < 5 and attempts < 100:  # Попробуем 100 раз сгенерировать уникальные юзернеймы
        username = generate_usernames(count=1)[0]  # генерируем один username
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
        "💎 Купить подписку можно у @wvmmy.\n1 покупка — 100₽\n2 покупка — 75₽\n3+ — 50₽/мес.",
        reply_markup=menu
    )

# Статус подписки
@dp.message_handler(lambda message: message.text == "📊 Статус подписки")
async def subscription_status(msg: types.Message):
    status = await get_subscription_status(msg.from_user.id)
    await msg.answer(status)

# Обработчик админ панели
@dp.message_handler(lambda message: message.text == "⚙️ Админ панель")
async def admin_panel(msg: types.Message):
    if msg.from_user.id == ADMIN_ID:
        await msg.answer("Добро пожаловать в админ панель!", reply_markup=admin_menu)
    else:
        await msg.answer("❌ Вы не администратор.")

# Статистика пользователей
@dp.message_handler(lambda message: message.text == "📊 Статистика")
async def stats(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        await msg.answer("❌ Вы не администратор.")
        return
    total_users, subscribed_users = await get_admin_stats()
    await msg.answer(f"Общее количество пользователей: {total_users}\nПользователей с подпиской: {subscribed_users}")

# Выдача подписки
@dp.message_handler(lambda message: message.text == "🔒 Выдать подписку")
async def give_subscription(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        await msg.answer("❌ Вы не администратор.")
        return

    # Попросим администратора ввести ID пользователя для подписки
    await msg.answer("Пожалуйста, введите ID пользователя и на сколько месяцев нужно выдать подписку (например: /id <user_id> 3)", reply_markup=generate_id_button())

# Удаление подписки
@dp.message_handler(lambda message: message.text == "❌ Убрать подписку")
async def remove_subscription(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        await msg.answer("❌ Вы не администратор.")
        return

    # Попросим администратора ввести ID пользователя для удаления подписки
    await msg.answer("Пожалуйста, введите ID пользователя, у которого нужно удалить подписку.", reply_markup=generate_id_button())

# Обработка команды ввода ID пользователя для выдачи подписки
@dp.message_handler(lambda message: message.text.startswith("/id"))
async def input_id_for_subscription(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        await msg.answer("❌ Вы не администратор.")
        return

    # Получаем ID из сообщения
    try:
        user_id, months = int(msg.text.split()[1]), int(msg.text.split()[2])  # получаем ID пользователя и количество месяцев
    except (IndexError, ValueError):
        await msg.answer("❌ Неверный формат. Используйте команду в формате: /id <user_id> <months>")
        return

    # Выдаем подписку пользователю
    await add_subscription(user_id, months)
    await msg.answer(f"✅ Подписка успешно выдана пользователю {user_id} на {months} месяц(ев).")

# Обработчик команды ввода ID пользователя для удаления подписки
@dp.message_handler(lambda message: message.text.startswith("/remove_id"))
async def input_id_for_removal(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        await msg.answer("❌ Вы не администратор.")
        return

    # Получаем ID из сообщения
    try:
        user_id = int(msg.text.split()[1])  # получаем ID пользователя из команды
    except (IndexError, ValueError):
        await msg.answer("❌ Неверный формат ID. Используйте команду в формате: /remove_id <user_id>")
        return

    # Удаляем подписку у пользователя
    async with aiosqlite.connect("database.db") as db:
        await db.execute("UPDATE users SET sub_until=NULL WHERE id=?", (user_id,))
        await db.commit()

    await msg.answer(f"❌ Подписка успешно удалена у пользователя {user_id}.")

# Завершение админ панели
@dp.message_handler(lambda message: message.text == "🚫 Завершить админ панель")
async def end_admin_panel(msg: types.Message):
    if msg.from_user.id == ADMIN_ID:
        await msg.answer("Админ панель завершена.", reply_markup=menu)
    else:
        await msg.answer("❌ Вы не администратор.")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_db())
    executor.start_polling(dp, skip_updates=True)
