from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update
import random
import string
import logging

# Настройка логирования для отладки
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# === НАСТРОЙКИ ===
BOT_TOKEN = "8717987578:AAF1i8ycyaOrSlFlDS727OUcfqXLcAv7v9k"  # ЗАМЕНИТЕ ЭТОТ ТЕКСТ НА ВАШ ТОКЕН


def generate_username(length=5):
    """Генерирует случайный пятибуквенный юзернейм (только строчные буквы)"""
    chars = string.ascii_lowercase  # только буквы a-z
    return ''.join(random.choice(chars) for _ in range(length))

async def check_username_availability(username: str) -> bool:
    """Проверяет доступность юзернейма"""
    try:
        await application.bot.get_chat(f"@{username}")
        return False  # Юзернейм занят
    except Exception:
        return True  # Юзернейм свободен


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Пользователь {update.effective_user.id} запустил бота")
    await update.message.reply_text(
        "Привет! Я бот для подбора пятибуквенных юзернеймов (только буквы).\n"
        "Напишите /generate, чтобы получить варианты."
    )

async def generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"Пользователь {update.effective_user.id} запросил юзернеймы")
    available_usernames = []
    attempts = 0
    max_attempts = 500

    while len(available_usernames) < 5 and attempts < max_attempts:
        username = generate_username()
        if await check_username_availability(username) and username not in available_usernames:
            available_usernames.append(username)
        attempts += 1

    if available_usernames:
        response = "Вот несколько свободных пятибуквенных юзернеймов:\n"
        for i, username in enumerate(available_usernames, 1):
            response += f"{i}. @{username}\n"
    else:
        response = (
            "Не удалось найти свободные юзернеймы за отведённое количество попыток.\n"
            "Попробуйте позже или напишите /generate ещё раз."
        )

    await update.message.reply_text(response)

# Создаём приложение с настройками таймаутов
application = Application.builder()\
    .token(BOT_TOKEN)\
    .connection_pool_size(10)\
    .read_timeout(30)\
    .write_timeout(30)\
    .connect_timeout(15)\
    .pool_timeout(5)\
    .build()

# Регистрируем обработчики
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("generate", generate))

if __name__ == "__main__":
    print("Бот запускается... Ожидайте сообщения 'Application started'")
    try:
        application.run_polling()
    except Exception as e:
        print(f"Критическая ошибка: {e}")
