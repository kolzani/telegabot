import asyncio
import random
import string
import aiosqlite
import datetime
import logging

from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup
from aiogram.utils import executor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = "8648186725:AAG8LqXwmsyEevpBDmi08wf6FCXXAOQq9pU"  # <-- замените на токен
ADMIN_ID = 6228421196      # <-- замените на свой ID

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

letters = string.ascii_lowercase
WORKERS = 5

# Меню
menu = ReplyKeyboardMarkup(resize_keyboard=True)
menu.add("🔎 Найти username", "🔤 Фильтр")
menu.add("📊 Подписка", "💎 Купить")
menu.add("♻️ Сбросить фильтр", "⚙️ Админ панель")

admin_menu = ReplyKeyboardMarkup(resize_keyboard=True)
admin_menu.add("📊 Статистика", "🔒 Выдать подписку")
admin_menu.add("❌ Завершить админ панель")


async def init_db():
    async with aiosqlite.connect("database.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY,
                sub_until TEXT,
                filter TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS usernames(
                username TEXT UNIQUE
            )
        """)
        await db.commit()
    logger.info("Database initialized")


def generate_username(filter_letters=None):
    chars = filter_letters if filter_letters else letters
    return ''.join(random.choice(chars) for _ in range(5))


async def has_sub(user_id):
    async with aiosqlite.connect("database.db") as db:
        async with db.execute("SELECT sub_until FROM users WHERE id=?", (user_id,)) as cur:
            data = await cur.fetchone()
    if not data or not data[0]:
        return False
    return datetime.datetime.now() < datetime.datetime.strptime(data[0], "%Y-%m-%d")


async def get_filter(user_id):
    async with aiosqlite.connect("database.db") as db:
        async with db.execute("SELECT filter FROM users WHERE id=?", (user_id,)) as cur:
            data = await cur.fetchone()
    return data[0] if data else None


async def save_username(username):
    async with aiosqlite.connect("database.db") as db:
        try:
            await db.execute("INSERT INTO usernames(username) VALUES(?)", (username,))
            await db.commit()
            with open("found_usernames.txt", "a") as f:
                f.write(username + "\n")
        except:
            pass  # если уже есть, игнорируем


async def worker(user_id, filter_letters):
    while True:
        username = generate_username(filter_letters)
        # проверка "свободного" username (здесь имитация)
        free = random.choice([True, False, False])
        if free:
            await save_username(username)
            await bot.send_message(user_id, f"🔥 Найден username: @{username}")
            break
        await asyncio.sleep(0.5)


@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    await msg.answer("🚀 Бот ищет свободные 5-буквенные username", reply_markup=menu)


@dp.message_handler(lambda m: m.text == "🔎 Найти username")
async def search(msg: types.Message):
    if not await has_sub(msg.from_user.id):
        await msg.answer("❌ Нет подписки")
        return
    filter_letters = await get_filter(msg.from_user.id)
    await msg.answer("🔍 Поиск запущен...")
    tasks = [asyncio.create_task(worker(msg.from_user.id, filter_letters)) for _ in range(WORKERS)]
    await asyncio.gather(*tasks)


@dp.message_handler(lambda m: m.text == "🔤 Фильтр")
async def filter_cmd(msg: types.Message):
    await msg.answer("Введите буквы для генерации (например: abc)")


@dp.message_handler(lambda m: m.text.isalpha() and len(m.text) <= 26)
async def save_filter(msg: types.Message):
    async with aiosqlite.connect("database.db") as db:
        await db.execute("INSERT OR REPLACE INTO users(id, filter) VALUES (?,?)",
                         (msg.from_user.id, msg.text.lower()))
        await db.commit()
    await msg.answer("✅ Фильтр сохранён")


@dp.message_handler(lambda m: m.text == "♻️ Сбросить фильтр")
async def reset_filter(msg: types.Message):
    async with aiosqlite.connect("database.db") as db:
        await db.execute("UPDATE users SET filter=NULL WHERE id=?", (msg.from_user.id,))
        await db.commit()
    await msg.answer("✅ Фильтр сброшен")


@dp.message_handler(lambda m: m.text == "📊 Подписка")
async def sub_status(msg: types.Message):
    async with aiosqlite.connect("database.db") as db:
        async with db.execute("SELECT sub_until FROM users WHERE id=?", (msg.from_user.id,)) as cur:
            data = await cur.fetchone()
    if not data or not data[0]:
        await msg.answer("❌ Подписки нет")
    else:
        await msg.answer(f"✅ Подписка до {data[0]}")


@dp.message_handler(lambda m: m.text == "💎 Купить")
async def buy(msg: types.Message):
    await msg.answer("💎 Купить подписку у @wvmmy\n1 покупка — 100₽\n2 покупка — 75₽\n3+ — 50₽/мес")


@dp.message_handler(lambda m: m.text == "⚙️ Админ панель")
async def admin_panel(msg: types.Message):
    if msg.from_user.id == ADMIN_ID:
        await msg.answer("⚙️ Админ панель", reply_markup=admin_menu)
    else:
        await msg.answer("❌ Нет доступа")


@dp.message_handler(lambda m: m.text == "📊 Статистика")
async def stats(msg: types.Message):
    if msg.from_user.id != ADMIN_ID:
        return
    async with aiosqlite.connect("database.db") as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            users = (await cur.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM usernames") as cur:
            names = (await cur.fetchone())[0]
    await msg.answer(f"👤 Пользователей: {users}\n🔥 Найдено username: {names}")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_db())
    executor.start_polling(dp)
