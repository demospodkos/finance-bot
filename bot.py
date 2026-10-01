import os
import sys
import json
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler

print("=== BOT STARTING ===")

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    print("ERROR: TELEGRAM_BOT_TOKEN missing")
    sys.exit(1)

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from agent import FinanceAgent

user_amounts = {}
DEFAULT_AMOUNT = 100000
SUB_FILE = "subscribers.json"

def load_subs():
    try:
        with open(SUB_FILE, "r") as f:
            return set(json.load(f))
    except Exception:
        return set()

def save_subs(s):
    with open(SUB_FILE, "w") as f:
        json.dump(list(s), f)

subscribers = load_subs()

def get_agent(chat_id: int) -> FinanceAgent:
    amount = user_amounts.get(chat_id, DEFAULT_AMOUNT)
    return FinanceAgent(amount=amount)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    amount = user_amounts.get(chat_id, DEFAULT_AMOUNT)
    kb = [
        [
            InlineKeyboardButton("Снимок", callback_data="rates"),
            InlineKeyboardButton("Рекомендация", callback_data="recommend"),
        ],
        [
            InlineKeyboardButton("Подписаться", callback_data="sub"),
            InlineKeyboardButton("Отписаться", callback_data="unsub"),
        ],
    ]
    text = (
        f"Финансовый агент\n"
        f"Текущая сумма: {amount:,.0f} руб.\n\n"
        "Команды:\n"
        "/amount 150000 - установить сумму\n"
        "/recommend - рекомендация\n"
        "/rates - снимок рынка\n"
        "/subscribe - ежедневные уведомления (10:00 МСК)\n"
        "/unsubscribe - отключить"
    )
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))

async def amount_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.args:
        current = user_amounts.get(chat_id, DEFAULT_AMOUNT)
        await update.message.reply_text(
            f"Текущая сумма: {current:,.0f} руб.\n"
            "Чтобы изменить, напиши например:\n/amount 150000"
        )
        return

    try:
        raw = context.args[0].replace(" ", "").replace(",", ".")
        new_amount = float(raw)
        if new_amount < 1000:
            await update.message.reply_text("Слишком маленькая сумма")
            return
        if new_amount > 10000000:
            await update.message.reply_text("Слишком большая сумма")
            return
        user_amounts[chat_id] = new_amount
        await update.message.reply_text(f"Сумма установлена: {new_amount:,.0f} руб.")
    except Exception:
        await update.message.reply_text("Напиши сумму числом. Пример: /amount 150000")

async def recommend_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    agent = get_agent(update.effective_chat.id)
    await update.message.reply_text("Считаю...")
    text = await agent.recommend(6)
    await update.message.reply_text(text[:4000])

async def rates_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    agent = get_agent(update.effective_chat.id)
    await update.message.reply_text("Загружаю...")
    data = await agent.get_market_snapshot()
    text = agent.format_snapshot(data)
    await update.message.reply_text(text[:4000])

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    subscribers.add(chat_id)
    save_subs(subscribers)
    await update.message.reply_text(
        "Подписка включена.\nКаждый день в 10:00 по Москве пришлю сводку."
    )

async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    subscribers.discard(chat_id)
    save_subs(subscribers)
    await update.message.reply_text("Подписка отключена.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    agent = get_agent(chat_id)
    data = query.data

    if data == "recommend":
        text = await agent.recommend(6)
    elif data == "sub":
        subscribers.add(chat_id)
        save_subs(subscribers)
        text = "Подписка включена."
    elif data == "unsub":
        subscribers.discard(chat_id)
        save_subs(subscribers)
        text = "Подписка отключена."
    else:
        snap = await agent.get_market_snapshot()
        text = agent.format_snapshot(snap)

    await query.edit_message_text(text[:4000])

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    agent = get_agent(update.effective_chat.id)
    answer = await agent.answer(update.message.text)
    await update.message.reply_text(answer[:4000])

async def daily_job(context: ContextTypes.DEFAULT_TYPE):
    if not subscribers:
        return
    try:
        for chat_id in list(subscribers):
            agent = get_agent(chat_id)
            data = await agent.get_market_snapshot()
            text = "Ежедневная сводка (10:00 МСК)\n\n" + agent.format_snapshot(data)
            try:
                await context.bot.send_message(chat_id=chat_id, text=text[:4000])
            except Exception as e:
                print("Send error:", e)
    except Exception as e:
        print("Daily error:", e)

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("amount", amount_cmd))
    app.add_handler(CommandHandler("recommend", recommend_cmd))
    app.add_handler(CommandHandler("rates", rates_cmd))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT, text_handler))

    scheduler = AsyncIOScheduler(timezone=pytz.timezone("Europe/Moscow"))
    scheduler.add_job(daily_job, "cron", hour=10, minute=0, args=[app])
    scheduler.start()

    print("=== BOT STARTED ===")
    app.run_polling()

if __name__ == "__main__":
    main()
