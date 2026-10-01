from data_fetchers import (
    get_key_rate,
    get_ofz_short,
    get_sample_deposit_rates,
    get_currency_rates,
    net_yield,
)

class FinanceAgent:
    def __init__(self, amount: float = 100000):
        self.amount = amount

    def set_amount(self, amount: float):
        self.amount = amount

    async def get_market_snapshot(self):
        return {
            "key_rate": await get_key_rate(),
            "ofz": await get_ofz_short(),
            "deposits": await get_sample_deposit_rates(),
            "currencies": await get_currency_rates(),
        }

    def format_snapshot(self, data) -> str:
        kr = data["key_rate"]
        cur = data["currencies"]

        lines = [
            "СНИМОК РЫНКА",
            f"Ключевая ставка ЦБ: {kr['rate']}%",
            f"Текущая сумма: {self.amount:,.0f} руб.",
            "",
            "Курсы валют ЦБ:",
            f"USD: {cur['USD']} руб.",
            f"EUR: {cur['EUR']} руб.",
            f"CNY: {cur['CNY']} руб.",
            f"(на {cur['date']})",
            "",
            "Короткие ОФЗ:",
        ]

        for i, b in enumerate(data["ofz"][:5], 1):
            ny = net_yield(b["ytm"])
            lines.append(
                f"{i}. {b['name']} - {b['ytm']}% (после налога {ny}%), погашение {b['matdate']}"
            )

        lines.append("")
        lines.append("Примеры вкладов (крупные банки):")
        for i, d in enumerate(data["deposits"][:12], 1):
            income = self.amount * (d["rate"] / 100) * (d["term_months"] / 12) * 0.87
            note = f" ({d['note']})" if d.get("note") else ""
            lines.append(
                f"{i}. {d['bank']} {d['rate']}% на {d['term_months']} мес. "
                f"({income:,.0f} руб. чистыми){note}"
            )

        return "\n".join(lines)

    async def recommend(self, months: int = 6) -> str:
        data = await self.get_market_snapshot()
        text = self.format_snapshot(data)

        if months <= 3:
            advice = (
                "\n\nРЕКОМЕНДАЦИЯ НА 1-3 МЕСЯЦА:\n"
                "Лучше короткий вклад под максимальную ставку.\n"
                "ОФЗ тоже подходят, если нужна возможность продать раньше."
            )
        elif months <= 6:
            advice = (
                "\n\nРЕКОМЕНДАЦИЯ НА 3-6 МЕСЯЦЕВ:\n"
                "1. Вклад 3-6 месяцев в надёжном банке.\n"
                "2. Короткие ОФЗ с погашением в 2027.\n"
                "Вся сумма в пределах АСВ (до 1.4 млн)."
            )
        else:
            advice = (
                "\n\nРЕКОМЕНДАЦИЯ НА 6-12 МЕСЯЦЕВ:\n"
                "Можно часть в ОФЗ, часть во вклад.\n"
                "Не ставь всё на максимальный срок."
            )

        return text + advice

    async def answer(self, question: str) -> str:
        q = question.lower()
        if any(w in q for w in ["куда", "вложить", "рекоменд", "совет"]):
            return await self.recommend(6)
        if "курс" in q or "доллар" in q or "евро" in q or "юань" in q:
            data = await self.get_market_snapshot()
            cur = data["currencies"]
            return (
                f"Курсы ЦБ на {cur['date']}:\n"
                f"Доллар (USD): {cur['USD']} руб.\n"
                f"Евро (EUR): {cur['EUR']} руб.\n"
                f"Юань (CNY): {cur['CNY']} руб."
            )
        if "3 месяц" in q or "три месяц" in q:
            return await self.recommend(3)
        if "12" in q or "год" in q:
            return await self.recommend(12)
        if "офз" in q or "облигац" in q or "вклад" in q or "депозит" in q:
            data = await self.get_market_snapshot()
            return self.format_snapshot(data)
        return "Напиши: куда вложить, курс доллара, /recommend, /rates, /amount 150000"
