import os
import sys

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
        ]
    ]
    text = (
        f"Финансовый агент\n"
        f"Текущая сумма: {amount:,.0f} руб.\n\n"
        "Команды:\n"
        "/amount 150000 - установить сумму\n"
        "/recommend - рекомендация\n"
        "/rates - снимок рынка"
    )
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))

async def amount_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.args:
        current = user_amounts.get(chat_id, DEFAULT_AMOUNT)
        await update.message.reply_text(
            f"Текущая сумма: {current:,.0f} руб.\n"
            "Пример: /amount 150000"
        )
        return
    try:
        raw = context.args[0].replace(" ", "").replace(",", ".")
        new_amount = float(raw)
        if new_amount < 1000 or new_amount > 10000000:
            await update.message.reply_text("Сумма должна быть от 1000 до 10 млн")
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

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    agent = get_agent(query.message.chat_id)
    if query.data == "recommend":
        text = await agent.recommend(6)
    else:
        data = await agent.get_market_snapshot()
        text = agent.format_snapshot(data)
    await query.edit_message_text(text[:4000])

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    agent = get_agent(update.effective_chat.id)
    answer = await agent.answer(update.message.text)
    await update.message.reply_text(answer[:4000])

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("amount", amount_cmd))
    app.add_handler(CommandHandler("recommend", recommend_cmd))
    app.add_handler(CommandHandler("rates", rates_cmd))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT, text_handler))
    print("=== BOT STARTED ===")
    app.run_polling()

if __name__ == "__main__":
    main()
