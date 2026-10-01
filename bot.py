
"""
Telegram-бот — личный финансовый агент (рубли, минимальный риск).
Сумма по умолчанию: 300 000 ₽.
"""

from __future__ import annotations

import os
import logging
from dotenv import load_dotenv
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

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
AMOUNT = float(os.getenv("USER_AMOUNT", "300000"))

if not TOKEN:
    raise ValueError("Укажите TELEGRAM_BOT_TOKEN")

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
        "Я мониторю ключевую ставку ЦБ, короткие ОФЗ и ставки по вкладам.\n\n"
        "Команды:\n"
        "/start - это меню\n"
        "/recommend - рекомендация под твои 300к\n"
        "/rates - текущий снимок\n"
        "/help - помощь\n\n"
        "Или просто напиши вопрос: куда вложить на 6 месяцев?"
    )
    await update.message.reply_text(text, reply_markup=reply_markup)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "Финансовый агент - помощь\n\n"
        "Я работаю только с рублёвыми инструментами минимального риска:\n"
        "- Вклады в пределах АСВ (1,4 млн)\n"
        "- Короткие ОФЗ\n"
        "- Накопительные счета\n\n"
        "Не даю советов по акциям, крипте и высокорисковым продуктам.\n\n"
        "Просто пиши вопросы обычным текстом или используй кнопки."
    )
    await update.message.reply_text(text)


async def recommend_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Собираю данные и готовлю рекомендацию...")
    text = await agent.recommend()
    if len(text) > 4000:
        text = text[:4000] + "\n\n... (обрезано)"
    await update.message.reply_text(text)


async def rates_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Загружаю снимок рынка...")
    snapshot = await agent.get_market_snapshot()
    text = agent.format_snapshot
