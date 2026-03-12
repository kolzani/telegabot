import asyncio
import random
import string
import aiohttp
import aiosqlite
import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup
from aiogram.utils import executor

TOKEN = "8648186725:AAG8LqXwmsyEevpBDmi08wf6FCXXAOQq9pU"
ADMIN_ID = 6228421196  # Заменить на свой ID

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

letters = string.ascii_lowercase
WORKERS = 5

menu = ReplyKeyboardMarkup(resize_keyboard=True)
menu.add("🔎 Найти username")
menu.add("🔤 Фильтр")
menu.add("📊 Подписка")
menu.add("💎 Купить")
menu.add("♻️ Сбросить фильтр")
menu.add("⚙️ Админ панель")

admin_menu = ReplyKeyboardMarkup(resize_keyboard=True)
admin_menu.add("📊 Статистика")
admin_menu.add("🔒 Выдать подписку")
admin_menu.add("🚫 Удалить пользователя")
admin_menu.add("❌ Завершить админ панель")


def generate_username(filter_letters=None):
    chars = filter_letters if filter_letters else letters
    return ''.join(random.choice(chars) for _ in range(5))


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


async def username_used(username):

    async with aiosqlite.connect("database.db") as db:

        async with db.execute(
            "SELECT username FROM usernames WHERE username=?",
            (username,)
        ) as cur:

            return await cur.fetchone()


async def save_username(username):

    async with aiosqlite.connect("database.db") as db:

        try:
            await db.execute(
                "INSERT INTO usernames VALUES(?)",
                (username,)
            )
            await db.commit()
        except:
            pass

    with open("found_usernames.txt", "a") as f:
        f.write(username + "\n")


async def check_username(session, username):

    url = f"https://t.me/{username}"

    try:

        async with session.get(url) as r:

            text = await r.text()

            if "If you have Telegram" in text:
                return True

    except:
        pass

    return False


async def has_sub(user_id):

    async with aiosqlite.connect("database.db") as db:

        async with db.execute(
            "SELECT sub_until FROM users WHERE id=?",
            (user_id,)
        ) as cur:

            data = await cur.fetchone()

    if not data:
        return False

    date = datetime.datetime.strptime(data[0], "%Y-%m-%d")

    return datetime.datetime.now() < date


async def get_filter(user_id):

    async with aiosqlite.connect("database.db") as db:

        async with db.execute(
            "SELECT filter FROM users WHERE id=?",
            (user_id,)
        ) as cur:

            data = await cur.fetchone()

    if data:
        return data[0]

    return None


async def worker(user_id, filter_letters):

    conn = aiohttp.TCPConnector(limit=50)

    async with aiohttp.ClientSession(connector=conn) as session:

        while True:

            username = generate_username(filter_letters)

            if await username_used(username):
                continue

            free = await check_username(session, username)

            await asyncio.sleep(0.7)

            if free:

                await save_username(username)

                try:

                    await bot.send_message(
                        user_id,
                        f"🔥 Найден свободный username\n@{username}"
                    )

                except:
                    pass

                return


@dp.message_handler(commands=["start"])
async def start(msg: types.Message):

    await msg.answer(
        "🚀 Бот ищет свободные **5‑буквенные username**",
        parse_mode="Markdown",
        reply_markup=menu
    )


@dp.message_handler(lambda m: m.text == "🔎 Найти username")
async def search(msg: types.Message):

    if not await has_sub(msg.from_user.id):

        await msg.answer("❌ Нет активной подписки")
        return

    filter_letters = await get_filter(msg.from_user.id)

    await msg.answer("🚀 Начинаю поиск...")

    tasks = []

    for _ in range(WORKERS):

        tasks.append(
            asyncio.create_task(
                worker(msg.from_user.id, filter_letters)
            )
        )

    await asyncio.gather(*tasks)


@dp.message_handler(lambda m: m.text == "🔤 Фильтр")
async def filter_cmd(msg: types.Message):

    await msg.answer(
        "Введите буквы для генерации\n\nпример:\nabc"
    )


@dp.message_handler(lambda m: m.text.isalpha() and len(m.text) <= 26)
async def save_filter(msg: types.Message):

    async with aiosqlite.connect("database.db") as db:

        await db.execute(
            "INSERT OR REPLACE INTO users(id, filter) VALUES (?,?)",
            (msg.from_user.id, msg.text.lower())
        )

        await db.commit()

    await msg.answer("✅ Фильтр сохранён")


@dp.message_handler(lambda m: m.text == "📊 Подписка")
async def sub_status(msg: types.Message):

    async with aiosqlite.connect("database.db") as db:

        async with db.execute(
            "SELECT sub_until FROM users WHERE id=?",
            (msg.from_user.id,)
        ) as cur:

            data = await cur.fetchone()

    if not data:

        await msg.answer("❌ Подписки нет")
        return

    await msg.answer(f"✅ Подписка до {data[0]}")


@dp.message_handler(lambda m: m.text == "💎 Купить")
async def buy(msg: types.Message):

    await msg.answer(
        "💎 Купить подписку можно у @wvmmy\n\n"
        "1 покупка — 100 руб\n"
        "2 покупка — 75 руб\n"
        "3+ покупка — 50 руб / месяц"
    )


@dp.message_handler(lambda m: m.text == "♻️ Сбросить фильтр")
async def reset_filter(msg: types.Message):
    async with aiosqlite.connect("database.db") as db:
        await db.execute(
            "UPDATE users SET filter=NULL WHERE id=?",
            (msg.from_user.id,)
        )
        await db.commit()
    await msg.answer("✅ Фильтр букв сброшен. Генерация теперь будет из всех букв.")


@dp.message_handler(lambda m: m.text == "⚙️ Админ панель")
async def admin_panel(msg: types.Message):
    if msg.from_user.id == ADMIN_ID:
        await msg.answer("⚙️ Админ панель", reply_markup=admin_menu)
    else:
        await msg.answer("❌ У вас нет прав доступа.")


@dp.message_handler(lambda m: m.text == "📊 Статистика")
async def stats(msg: types.Message):

    if msg.from_user.id != ADMIN_ID:
        return

    async with aiosqlite.connect("database.db") as db:

        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            users = (await cur.fetchone())[0]

        async with db.execute("SELECT COUNT(*) FROM usernames") as cur:
            names = (await cur.fetchone())[0]

    await msg.answer(
        f"📊 Статистика\n\n"
        f"👤 Пользователей: {users}\n"
        f"🔥 Найдено username: {names}"
    )


@dp.message_handler(lambda m: m.text == "🔒 Выдать подписку")
async def give_sub(msg: types.Message):

    if msg.from_user.id != ADMIN_ID:
        return

    await msg.answer("Введите ID пользователя и количество дней (например, 123456789 30):")


@dp.message_handler(lambda m: m.text.startswith("123"))
async def give_sub_days(msg: types.Message):

    if msg.from_user.id != ADMIN_ID:
        return

    try:
        user_id, days = map(int, msg.text.split())
        date = datetime.datetime.now() + datetime.timedelta(days=days)

        async with aiosqlite.connect("database.db") as db:
            await db.execute(
                "INSERT OR REPLACE INTO users(id, sub_until) VALUES (?,?)",
                (user_id, date.strftime("%Y-%m-%d"))
            )
            await db.commit()

        await msg.answer(f"✅ Подписка выдана пользователю {user_id} до {date.strftime('%Y-%m-%d')}.")

    except:
        await msg.answer("❌ Неверный формат. Используйте: ID ДНИ.")


@dp.message_handler(lambda m: m.text == "🚫 Удалить пользователя")
async def delete_user(msg: types.Message):

    if msg.from_user.id != ADMIN_ID:
        return

    await msg.answer("Введите ID пользователя, которого хотите удалить:")


@dp.message_handler(lambda m: m.text.startswith("123"))
async def delete_user_from_db(msg: types.Message):

    if msg.from_user.id != ADMIN_ID
