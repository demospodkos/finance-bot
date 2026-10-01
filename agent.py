from data_fetchers import get_key_rate, get_ofz_short, get_sample_deposit_rates, net_yield

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
        }

    def format_snapshot(self, data) -> str:
        kr = data["key_rate"]
        lines = [
            "СНИМОК РЫНКА",
            f"Ключевая ставка ЦБ: {kr['rate']}%",
            f"Текущая сумма: {self.amount:,.0f} руб.",
            "",
            "Короткие ОФЗ:",
        ]
        for i, b in enumerate(data["ofz"][:5], 1):
            lines.append(
                f"{i}. {b['name']} - {b['ytm']}% "
                f"(после налога \~{net_yield(b['ytm'])}%), погашение {b['matdate']}"
            )

        lines.append("")
        lines.append("Примеры вкладов:")
        for i, d in enumerate(data["deposits"], 1):
            income = self.amount * (d["rate"] / 100) * (d["term_months"] / 12) * 0.87
            lines.append(
                f"{i}. {d['bank']} {d['rate']}% на {d['term_months']} мес. "
                f"(\~{income:,.0f} руб. чистыми)"
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
        if "3 месяц" in q or "три месяц" in q:
            return await self.recommend(3)
        if "12" in q or "год" in q:
            return await self.recommend(12)
        if "офз" in q or "облигац" in q or "вклад" in q or "депозит" in q:
            data = await self.get_market_snapshot()
            return self.format_snapshot(data)
        return "Напиши: куда вложить, /recommend, /rates, /amount 150000 или /subscribe"
