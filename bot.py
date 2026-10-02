import os
import sys
import json
from datetime import datetime

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
PORTFOLIO_FILE = "portfolio.json"
SUB_FILE = "subscribers.json"

def load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

portfolios = load_json(PORTFOLIO_FILE, {})
subscribers = set(load_json(SUB_FILE, []))

def get_agent(chat_id: int) -> FinanceAgent:
    amount = user_amounts.get(chat_id, DEFAULT_AMOUNT)
    return FinanceAgent(amount=amount)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    amount = user_amounts.get(chat_id, DEFAULT_AMOUNT)
    kb = [
        [
            InlineKeyboardButton("Топ-3", callback_data="top3"),
            InlineKeyboardButton("Снимок", callback_data="rates"),
        ],
        [
            InlineKeyboardButton("Рекомендация", callback_data="recommend"),
            InlineKeyboardButton("Сравнение", callback_data="compare"),
        ],
        [
            InlineKeyboardButton("Портфель", callback_data="portfolio"),
        ],
    ]
    text = (
        f"Финансовый агент\n"
        f"Текущая сумма: {amount:,.0f} руб.\n\n"
        "Команды:\n"
        "/top3 - лучшие варианты сейчас\n"
        "/rates - снимок рынка\n"
        "/recommend - рекомендация\n"
        "/compare [мес] - сравнение\n"
        "/calc 150000 6 - калькулятор\n"
        "/amount 150000 - сумма\n"
        "/hold вклад ВТБ 150000 13.7 6\n"
        "/portfolio - мой портфель\n"
        "/subscribe - еженедельная сводка\n"
        "/unsubscribe - отключить"
    )
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))

async def amount_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not context.args:
        current = user_amounts.get(chat_id, DEFAULT_AMOUNT)
        await update.message.reply_text(
            f"Текущая сумма: {current:,.0f} руб.\nПример: /amount 150000"
        )
        return
    try:
        raw = context.args[0].replace(" ", "").replace(",", ".")
        new_amount = float(raw)
        if new_amount < 1000 or new_amount > 10000000:
            await update.message.reply_text("Сумма от 1000 до 10 млн")
            return
        user_amounts[chat_id] = new_amount
        await update.message.reply_text(f"Сумма: {new_amount:,.0f} руб.")
    except Exception:
        await update.message.reply_text("Пример: /amount 150000")

async def top3_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    agent = get_agent(update.effective_chat.id)
    await update.message.reply_text("Считаю топ...")
    text = await agent.top3()
    await update.message.reply_text(text[:4000])

async def rates_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    agent = get_agent(update.effective_chat.id)
    await update.message.reply_text("Загружаю...")
    data = await agent.get_market_snapshot()
    text = agent.format_snapshot(data)
    await update.message.reply_text(text[:4000])

async def recommend_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    agent = get_agent(update.effective_chat.id)
    await update.message.reply_text("Считаю...")
    text = await agent.recommend(6)
    await update.message.reply_text(text[:4000])

async def compare_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    agent = get_agent(update.effective_chat.id)
    months = 6
    if context.args:
        try:
            months = int(context.args[0])
        except Exception:
            pass
    await update.message.reply_text("Сравниваю...")
    text = await agent.compare(months)
    await update.message.reply_text(text[:4000])

async def calc_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    agent = get_agent(update.effective_chat.id)
    amount = user_amounts.get(update.effective_chat.id, DEFAULT_AMOUNT)
    months = 6
    if context.args:
        try:
            amount = float(context.args[0].replace(" ", "").replace(",", "."))
        except Exception:
            pass
        if len(context.args) > 1:
            try:
                months = int(context.args[1])
            except Exception:
                pass
    await update.message.reply_text("Считаю...")
    text = await agent.calc(amount, months)
    await update.message.reply_text(text[:4000])

async def hold_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    # /hold вклад ВТБ 150000 13.7 6
    if len(context.args) < 5:
        await update.message.reply_text(
            "Формат:\n/hold вклад ВТБ 150000 13.7 6\n"
            "тип банк сумма ставка месяцы"
        )
        return
    try:
        h_type = context.args[0]
        bank = context.args[1]
        amount = float(context.args[2].replace(" ", "").replace(",", "."))
        rate = float(context.args[3].replace(",", "."))
        months = int(context.args[4])
        item = {
            "type": h_type,
            "bank": bank,
            "amount": amount,
            "rate": rate,
            "months": months,
            "added": datetime.now().strftime("%Y-%m-%d"),
        }
        if chat_id not in portfolios:
            portfolios[chat_id] = []
        portfolios[chat_id].append(item)
        save_json(PORTFOLIO_FILE, portfolios)
        await update.message.reply_text(
            f"Добавлено: {h_type} {bank} {amount:,.0f} руб. @ {rate}% / {months} мес."
        )
    except Exception:
        await update.message.reply_text(
            "Ошибка. Пример:\n/hold вклад ВТБ 150000 13.7 6"
        )

async def portfolio_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    agent = get_agent(update.effective_chat.id)
    holdings = portfolios.get(chat_id, [])
    text = agent.format_portfolio(holdings)
    await update.message.reply_text(text[:4000])

async def clear_portfolio_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    portfolios[chat_id] = []
    save_json(PORTFOLIO_FILE, portfolios)
    await update.message.reply_text("Портфель очищен.")

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    subscribers.add(chat_id)
    save_json(SUB_FILE, list(subscribers))
    await update.message.reply_text(
        "Подписка включена.\nКаждое воскресенье в 10:00 МСК пришлю сводку."
    )

async def unsubscribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    subscribers.discard(chat_id)
    save_json(SUB_FILE, list(subscribers))
    await update.message.reply_text("Подписка отключена.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    agent = get_agent(query.message.chat_id)
    data = query.data

    if data == "top3":
        text = await agent.top3()
    elif data == "recommend":
        text = await agent.recommend(6)
    elif data == "compare":
        text = await agent.compare(6)
    elif data == "portfolio":
        holdings = portfolios.get(str(query.message.chat_id), [])
        text = agent.format_portfolio(holdings)
    else:
        snap = await agent.get_market_snapshot()
        text = agent.format_snapshot(snap)

    await query.edit_message_text(text[:4000])

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    agent = get_agent(update.effective_chat.id)
    answer = await agent.answer(update.message.text)
    await update.message.reply_text(answer[:4000])

async def weekly_job(context: ContextTypes.DEFAULT_TYPE):
    if not subscribers:
        return
    for chat_id in list(subscribers):
        try:
            agent = get_agent(chat_id)
            text = "Еженедельная сводка\n\n" + await agent.top3()
            await context.bot.send_message(chat_id=chat_id, text=text[:4000])
        except Exception as e:
            print("Weekly send error:", e)

async def post_init(application: Application):
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        import pytz

        scheduler = AsyncIOScheduler(timezone=pytz.timezone("Europe/Moscow"))
        scheduler.add_job(
            weekly_job,
            "cron",
            day_of_week="sun",
            hour=10,
            minute=0,
            args=[application],
        )
        scheduler.start()
        print("Scheduler started: weekly Sunday 10:00 MSK")
    except Exception as e:
        print("Scheduler not started:", e)

def main():
    app = (
        Application.builder()
        .token(TOKEN)
        .post_init(post_init)
        .build()
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("amount", amount_cmd))
    app.add_handler(CommandHandler("top3", top3_cmd))
    app.add_handler(CommandHandler("rates", rates_cmd))
    app.add_handler(CommandHandler("recommend", recommend_cmd))
    app.add_handler(CommandHandler("compare", compare_cmd))
    app.add_handler(CommandHandler("calc", calc_cmd))
    app.add_handler(CommandHandler("hold", hold_cmd))
    app.add_handler(CommandHandler("portfolio", portfolio_cmd))
    app.add_handler(CommandHandler("clearportfolio", clear_portfolio_cmd))
    app.add_handler(CommandHandler("subscribe", subscribe))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT, text_handler))
    print("=== BOT STARTED ===")
    app.run_polling()

if __name__ == "__main__":
    main()
