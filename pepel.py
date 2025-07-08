import logging
import sqlite3
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)
from apscheduler.schedulers.background import BackgroundScheduler

# Логгинг
logging.basicConfig(level=logging.INFO)

# Ответы по шкале
responses = {
    "0": "💡 Ты светишь! Ты заряжаешь! Не забудь поделиться этим светом с коллегами ✨",
    "1": "✨ Ты ещё в игре, но искры утекают. Найди 30 минут на чай и тишину.",
    "2": "🔦 Свет есть, но только по просьбе. Сделай одну задачу и больше ничего.",
    "3": "🔥 Эй. Не геройствуй. Отдохни, убери часть задач.",
    "4": "🪨 Всё сгорело, но ты ещё шевелишься. Уйди в плед, без встреч.",
    "5": "⚰️ Ты — мёртвый уголь. День без всего. ПепелВасилич принес конфету.",
}

keyboard = [["0", "1", "2"], ["3", "4", "5"]]
markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

# Инициализация БД
conn = sqlite3.connect("pepel.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    level INTEGER,
    timestamp TEXT
)
""")
conn.commit()

# Сохраняем ID пользователей
user_ids = set()

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    user_ids.add(user_id)
    await update.message.reply_text(
        "🔥 Привет, смертные! Я — ПепелВасилич.\n"
        "Укажи свой уровень по шкале выгорания:\n\n"
        "0 — 💡 Светлячок\n"
        "1 — ✨ Искрящийся\n"
        "2 — 🔦 Фонарик\n"
        "3 — 🔥 Углём дышу\n"
        "4 — 🪨 Горячий пепел\n"
        "5 — ⚰️ Мёртвый уголь\n\n"
        "Просто нажми нужную цифру:",
        reply_markup=markup
    )

# Обработка ответа (цифры 0–5)
async def handle_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    username = update.message.from_user.username or "Без ника"
    text = update.message.text.strip()
    timestamp = datetime.utcnow().isoformat()

    if text in responses:
        level = int(text)
        # Сохраняем в БД
        cursor.execute(
            "INSERT INTO responses (user_id, username, level, timestamp) VALUES (?, ?, ?, ?)",
            (user_id, username, level, timestamp)
        )
        conn.commit()
        await update.message.reply_text(responses[text])
    else:
        await update.message.reply_text("Не понимаю тебя, смертный. Введи число от 0 до 5.")

# Команда /отчёт
async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.chat_id
    cursor.execute("SELECT level, timestamp FROM responses WHERE user_id = ? ORDER BY timestamp DESC LIMIT 10", (user_id,))
    rows = cursor.fetchall()
    if not rows:
        await update.message.reply_text("У тебя пока нет данных, смертный.")
    else:
        text = "🧾 Твой недавний путь по пеплу:\n"
        for level, ts in rows:
            emoji = list(responses.keys())[level]
            time = datetime.fromisoformat(ts).strftime("%d.%m.%Y %H:%M")
            text += f"{time} — {level} {responses[str(level)][:2]}\n"
        await update.message.reply_text(text)

# Команда /отчёт_команды
async def team_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cursor.execute("SELECT level, COUNT(*) FROM responses GROUP BY level")
    rows = cursor.fetchall()
    total = sum(count for _, count in rows)
    if total == 0:
        await update.message.reply_text("Нет данных по команде. Все живы?")
        return

    text = "📊 Статистика команды:\n"
    for level, count in sorted(rows):
        percent = round(count / total * 100, 1)
        emoji = responses[str(level)][:2]
        text += f"{emoji} Уровень {level}: {count} ответов ({percent}%)\n"

    await update.message.reply_text(text)

# Авторассылка по понедельникам
async def monday_broadcast(context: ContextTypes.DEFAULT_TYPE):
    for user_id in user_ids:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "🔥 Пора замерить уровень выгорания, смертный:\n\n"
                    "0 — 💡 Светлячок\n"
                    "1 — ✨ Искрящийся\n"
                    "2 — 🔦 Фонарик\n"
                    "3 — 🔥 Углём дышу\n"
                    "4 — 🪨 Горячий пепел\n"
                    "5 — ⚰️ Мёртвый уголь\n\n"
                    "Ответь цифрой:",
                ),
                reply_markup=markup
            )
        except Exception as e:
            logging.warning(f"Не удалось отправить {user_id}: {e}")

# Запуск
def main():
    TOKEN = "YOUR TOKEN HERE"
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("report", report))
    app.add_handler(CommandHandler("team_report", team_report))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_response))

    # Планировщик
    scheduler = BackgroundScheduler(timezone="UTC")
    scheduler.add_job(
        lambda: app.create_task(monday_broadcast(app.bot)),
        trigger='cron',
        day_of_week='mon',
        hour=9,
        minute=0
    )
    scheduler.start()

    print("🤖 ПепелВасилич запущен. Статистика пылает.")
    app.run_polling()

if __name__ == "__main__":
    main()
    
