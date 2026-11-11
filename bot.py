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
        cur.execute("""
            ALTER TABLE users ADD COLUMN IF NOT EXISTS name TEXT DEFAULT NULL
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
def set_name(user_id, name):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO users (user_id, name)
            VALUES (%s, %s)
            ON CONFLICT (user_id) DO UPDATE SET name = %s
        """, (user_id, name, name))
        conn.commit()
        cur.close()
    finally:
        conn.close()
async def setname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Напиши имя после команды. Пример: /name Ичиго")
        return
    name = " ".join(context.args)
    user_id = update.effective_user.id
    set_name(user_id, name)
    await update.message.reply_text(f"Имя установлено: {name}")
def get_top_players(limit=10):
    conn = get_db()
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT user_id, name, collection
            FROM users
            ORDER BY (SELECT SUM((card->>'points')::int) FROM jsonb_array_elements(collection) AS card) DESC
            LIMIT %s
        """, (limit,))
        rows = cur.fetchall()
        cur.close()
        return rows
    finally:
        conn.close()
async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    players = get_top_players(10)
    if not players:
        await update.message.reply_text("Пока нет игроков в топе.")
        return
    text = "🏆 Топ игроков:\n\n"
    for i, player in enumerate(players, 1):
        collection = player["collection"]
        total_points = sum(card.get("points", 0) for card in collection)
        total_cards = len(collection)
    display_name = player["name"] or f"ID {player['user_id']}"
    text += f"{i}. {display_name} — {total_points} очков ({total_cards} карт)\n"
    await update.message.reply_text(text)    
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
        BotCommand("top", "Топ игроков"),
        BotCommand("name", "Установить имя"),
    ])

def main():
    app = Application.builder().token(TOKEN).post_init(post_init).build()
    app.add_handler(CommandHandler("name", setname))
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("top", top))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cardsearch", cardsearch))
    print("Bleach Cards запущен!")
    init_db()
    app.run_polling()

if __name__ == "__main__":
    main()