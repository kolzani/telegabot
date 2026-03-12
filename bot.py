from aiogram import Bot
TOKEN = "8648186725:AAG8LqXwmsyEevpBDmi08wf6FCXXAOQq9pU"
bot = Bot(token=TOKEN)
await bot.delete_webhook()
await bot.session.close()
