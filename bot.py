import logging
import asyncio
import aiosqlite
import time
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor

API_TOKEN = '8648186725:AAG8LqXwmsyEevpBDmi08wf6FCXXAOQq9pU'  # Замените на свой токен
ADMIN_ID = 6228421196  # Замените на свой ID администратора
DATABASE_NAME = 'database.db'  # Имя вашей базы данных

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создаем экземпляры бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Инициализация базы данных
async def init_db():
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS subscriptions (
                user_id INTEGER PRIMARY KEY,
                subscription_end_date INTEGER
            )
        ''')
        await db.commit()

# Проверка подписки
async def check_subscription(user_id):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        cursor = await db.execute('SELECT subscription_end_date FROM subscriptions WHERE user_id = ?', (user_id,))
        result = await cursor.fetchone()
        if result:
            return result[0]  # Возвращаем дату окончания подписки
        return None  # Подписка отсутствует

# Обработчик команды "/start"
@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    user_id = message.from_user.id
    subscription_end_date = await check_subscription(user_id)

    if subscription_end_date:
        await message.reply(f"Ваша подписка активна до {subscription_end_date}.")
    else:
        await message.reply("У вас нет активной подписки. Купите подписку через админ-панель.")

# Админ-панель
@dp.message_handler(commands=['admin'])
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.reply("❌ Вы не администратор.")
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Выдать подписку"))
    markup.add(types.KeyboardButton("Удалить подписку"))
    await message.reply("Панель администратора", reply_markup=markup)

# Выдать подписку
@dp.message_handler(lambda message: message.text == "Выдать подписку")
async def give_subscription(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.reply("❌ Вы не администратор.")
        return

    await message.reply("Введите ID пользователя и количество месяцев подписки, например: 123456789 3")

# Удалить подписку
@dp.message_handler(lambda message: message.text == "Удалить подписку")
async def remove_subscription(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.reply("❌ Вы не администратор.")
        return

    await message.reply("Введите ID пользователя для удаления подписки.")

# Обработчик текста с ID и количеством месяцев подписки
@dp.message_handler(lambda message: len(message.text.split()) == 2)
async def handle_subscription(message: types.Message):
    user_id, months = message.text.split()
    user_id = int(user_id)
    months = int(months)

    async with aiosqlite.connect(DATABASE_NAME) as db:
        subscription_end_date = int(time.time()) + months * 30 * 24 * 60 * 60  # Добавляем количество месяцев к текущей дате

        # Вставка или обновление подписки пользователя
        await db.execute('''
            INSERT OR REPLACE INTO subscriptions (user_id, subscription_end_date)
            VALUES (?, ?)
        ''', (user_id, subscription_end_date))

        await db.commit()

    await message.reply(f"Подписка на {months} месяц(ев) выдана пользователю {user_id}.")

# Запуск бота
if __name__ == '__main__':
    # Используем asyncio.run() для корректного запуска бота
    asyncio.run(init_db())  # Инициализация базы данных
    executor.start_polling(dp, skip_updates=True)  # Запуск бота
