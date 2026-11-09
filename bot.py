import time
import random
from telegram import BotCommand
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from cards import CARDS

import os
TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚔️ Добро пожаловать в Bleach Cards!\n\n"
        "🎴 /cardsearch — получить карточку"
    )

async def cardsearch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    card = random.choice(CARDS)
    now = time.time()
    last_card = context.user_data.get("last_card", 0)

    if now - last_card < 43200:
        await update.message.reply_text(
            "⏳ Новую карточку можно получить через 12 часов!"
        )
        return
    text = (
        f"🎴 {card['name']}\n\n"
        f"💎 Редкость: {card['rarity']}\n"
        f"⭐ Очки: {card['points']:,}\n"
        f"🎲 Шанс выпадения: {card['chance']}%\n"
 
    )

    await update.message.reply_photo(
        photo=card["image"],
        caption=text)
    context.user_data["last_card"] = now

async def post_init(application):
    await application.bot.set_my_commands([
        BotCommand("start", "Запуск бота"),
        BotCommand("cardsearch", "Получить карточку"),
    ])

def main():
    app = Application.builder().token(TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cards", cardsearch))
    print("Bleach Cards запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()