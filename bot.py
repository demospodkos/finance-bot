import os
import sys

print("=== BOT STARTING ===")

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
print("TOKEN exists:", bool(TOKEN))

if not TOKEN:
    print("ERROR: TELEGRAM_BOT_TOKEN is missing")
    sys.exit(1)

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

from agent import FinanceAgent

AMOUNT = float(os.getenv("USER_AMOUNT", "300000"))
agent = FinanceAgent(amount=AMOUNT)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Снимок рынка", callback_data="snapshot"),
         InlineKeyboardButton("Рекомендация", callback_data="recommend")],
        [InlineKeyboardButton("Вклады", callback_data="deposits"),
         InlineKeyboardButton("ОФЗ", callback_data="ofz")]
    ]
    text = "Привет! Я финансовый агент.\nКапитал: 300000 руб.\nНажми кнопку или напиши /recommend"
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Команды: /start /recommend /rates /help")

async def recommend_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Собираю данные...")
    text = await agent.recommend()
    await update.message.reply_text(text[:4000])

async def rates_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Загружаю...")
    snapshot = await agent.get_market_snapshot()
    text = agent.format_snapshot(snapshot)
    await update.message.reply_text(text[:4000])

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "recommend":
        text = await agent.recommend()
    else:
        snapshot = await agent.get_market_snapshot()
        text = agent.format_snapshot(snapshot)
    await query.edit_message_text(text[:4000])

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = await agent.answer(update.message.text)
    await update.message.reply_text(answer[:4000])

def main():
    print("Creating application...")
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("recommend", recommend_cmd))
    app.add_handler(CommandHandler("rates", rates_cmd))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT, text_handler))

    print("=== BOT STARTED SUCCESSFULLY ===")
    app.run_polling()

if __name__ == "__main__":
    main()
