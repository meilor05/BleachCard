import time
import random
from telegram import BotCommand
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from cards import CARDS
import json
import psycopg2
from psycopg2.extras import RealDictCursor

def get_db():
    return psycopg2.connect(os.getenv("DATABASE_URL"), cursor_factory=RealDictCursor)

def init_db():
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id BIGINT PRIMARY KEY,
                collection JSONB DEFAULT '[]'::jsonb
            )
        """)
        conn.commit()
        cur.close()
    finally:
        conn.close()

def save_collection(user_id, collection):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO users (user_id, collection)
            VALUES (%s, %s)
            ON CONFLICT (user_id) DO UPDATE SET collection = %s
        """, (user_id, json.dumps(collection), json.dumps(collection)))
        conn.commit()
        cur.close()
    finally:
        conn.close()

def load_collection(user_id):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("SELECT collection FROM users WHERE user_id = %s", (user_id,))
        row = cur.fetchone()
        cur.close()
        if row:
            return row["collection"]
        return []
    finally:
        conn.close()
import os
TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚔️ Добро пожаловать в Bleach Cards!\n\n"
        "🎴 /cardsearch — получить карточку"
    )

async def cardsearch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    weights = [c["chance"] for c in CARDS]
    card = random.choices(CARDS, weights=weights, k=1)[0]
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
    user_id = update.effective_user.id
    collection = load_collection(user_id)
    collection.append(card)
    context.user_data["collection"] = collection
    save_collection(user_id, collection)
async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    collection = load_collection(update.effective_user.id)
    total_cards = len(collection)
    total_points = sum(card.get("points", 0) for card in collection)

    text = (
        f"👤 Твой профиль\n\n"
        f"🃏 Карточек: {total_cards}\n"
        f"⭐️ Общая сумма очков: {total_points}"
    )
    await update.message.reply_text(text)
async def post_init(application):
    await application.bot.set_my_commands([
        BotCommand("start", "Запуск бота"),
        BotCommand("cardsearch", "Получить карточку"),
        BotCommand("profile", "Мой профиль"),
    ])

def main():
    app = Application.builder().token(TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cardsearch", cardsearch))
    print("Bleach Cards запущен!")
    init_db()
    app.run_polling()

if __name__ == "__main__":
    main()