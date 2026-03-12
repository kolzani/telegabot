import asyncio
import random
import string
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ================== ВСТАВЬ СВОЙ ТОКЕН ЗДЕСЬ ==================
TOKEN = "8736467160:AAGQj5tu1N8VQyD6W_GzeRGjP496jH-NYRk"
# =================================================================

# Настройки
SHOW_BEAUTIFUL_CHANCE = 0.1  # шанс писать красивые username
PROGRESS_UPDATE_EVERY = 5     # сколько проверок между обновлением прогресса

# Генерация username
def generate_username(length=5):
    letters = string.ascii_lowercase
    digits = string.digits
    # Иногда генерируем "красивые" комбинации
    if random.random() < SHOW_BEAUTIFUL_CHANCE:
        return random.choice(letters) + ''.join(random.choices(letters + digits, k=length-1))
    else:
        return ''.join(random.choices(letters + digits, k=length))

# Кнопки меню
def menu():
    keyboard = [
        [InlineKeyboardButton("Поиск обычных", callback_data="normal")],
        [InlineKeyboardButton("Поиск 6-значных", callback_data="six_digits")]
    ]
    return InlineKeyboardMarkup(keyboard)

# Старт команды
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Выберите режим поиска username:", reply_markup=menu())

# Поиск username
async def search_usernames(update: Update, context: ContextTypes.DEFAULT_TYPE, length=5):
    query = update.callback_query
    await query.answer()
    msg = await query.message.reply_text("Запуск поиска...")
    
    found = 0
    total = 0
    checked = 0
    
    while True:
        username = generate_username(length)
        total += 1
        try:
            await context.bot.get_chat(username)
            # если get_chat не выдает исключение, значит username занят
        except Exception as e:
            if "400" in str(e) or "not found" in str(e).lower():
                # свободный username
                found += 1
                await msg.reply_text(f"Найден свободный username: @{username}")
        
        checked += 1
        if checked % PROGRESS_UPDATE_EVERY == 0:
            try:
                await msg.edit_text(f"Проверено: {total}\nНайдено свободных: {found}")
            except:
                pass  # если текст не изменился, просто пропускаем

# Обработчик кнопок
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "normal":
        await search_usernames(update, context, length=5)
    elif query.data == "six_digits":
        await search_usernames(update, context, length=6)

# Основной запуск
async def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
