import os
import sys
import logging

print("=== БОТ ЗАПУСКАЕТСЯ ===")
print("Python version:", sys.version)

try:
    from dotenv import load_dotenv
    load_dotenv()
    print("dotenv загружен")
except Exception as e:
    print("dotenv не загрузился:", e)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
print("TOKEN найден:" , "Да" if TOKEN else "НЕТ")

if not TOKEN:
    print("ОШИБКА: TELEGRAM_BOT_TOKEN не установлен!")
    print("Проверь Variables в Railway")
    sys.exit(1)

print("Токен есть, длина:", len(TOKEN))

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import (
        Application,
        CommandHandler,
        MessageHandler,
        CallbackQueryHandler,
        ContextTypes,
        filters,
    )
    print("telegram библиотека загружена")
except Exception as e:
    print("ОШИБКА загрузки telegram:", e)
    sys.exit(1)

try:
    from agent import FinanceAgent
    print("agent загружен")
except Exception as e:
    print("ОШИБКА загрузки agent:", e)
    sys.exit(1)

AMOUNT = float(os.getenv("USER_AMOUNT", "300000"))
print("Сумма:", amount)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

agent = FinanceAgent(amount=AMOUNT)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [
            InlineKeyboardButton("Снимок рынка", callback_data="snapshot"),
            InlineKeyboardButton("Рекомендация", callback_data="recommend"),
        ],
        [
            InlineKeyboardButton("Вклады", callback_data="deposits"),
            InlineKeyboardButton("Короткие ОФЗ", callback_data="ofz"),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        "Привет! Я твой личный финансовый агент по рублям.\n\n"
        f"Капитал: {AMOUNT:,.0f} руб.\n"
        "Цель: выгодно разместить с минимальным риском.\n\n"
        "Команды:\n"
        "/start - меню\n"
        "/recommend - рекомендация\n"
        "/rates - снимок рынка\n"
        "/help - помощь"
    )
    await update.message.reply_text(text, reply_markup=reply_markup)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Я работаю только с рублёвыми инструментами минимального риска:\n"
        "- Вклады в пределах АСВ\n"
        "- Короткие ОФЗ\n"
        "- Накопительные счета"
    )


async def recommend_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Собираю данные...")
    text = await agent.recommend()
    if len(text) > 4000:
        text = text[:4000] + "\n\n..."
    await update.message.reply_text(text)


async def rates_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Загружаю снимок...")
    snapshot = await agent.get_market_snapshot()
    text = agent.format_snapshot(snapshot)
    if len(text) > 4000:
        text = text[:4000] + "\n\n..."
    await update.message.reply_text(text)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    await query.edit_message_text("Обрабатываю...")

    if data in ("snapshot", "deposits", "ofz"):
        snapshot = await agent.get_market_snapshot()
        text = agent.format_snapshot(snapshot)
    elif data == "recommend":
        text = await agent.recommend()
    else:
        text = "Неизвестная команда"

    if len(text) > 4000:
        text = text[:4000] + "\n\n..."
    await query.edit_message_text(text)


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.chat.send_action("typing")
    answer = await agent.answer(update.message.text)
    if len(answer) > 4000:
        answer = answer[:4000] + "\n\n..."
    await update.message.reply_text(answer)


def main() -> None:
    print("Создаю Application...")
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("recommend", recommend_cmd))
    app.add_handler(CommandHandler("rates", rates_cmd))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & \~filters.COMMAND, text_handler))

    print("=== БОТ УСПЕШНО ЗАПУЩЕН ===")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
