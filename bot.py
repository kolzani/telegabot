import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
import logging

TOKEN = "8648186725:AAG8LqXwmsyEevpBDmi08wf6FCXXAOQq9pU"
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

logging.basicConfig(level=logging.INFO)


async def init_bot():
    # Удаляем webhook перед стартом polling
    await bot.delete_webhook()
    logging.info("Webhook deleted, polling is safe now")


@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    await msg.answer("Бот запущен, webhook сброшен, polling работает!")


async def main():
    await init_bot()  # удаляем вебхук
    # запуск бота через polling
    await dp.start_polling()


if __name__ == "__main__":
    asyncio.run(main())
