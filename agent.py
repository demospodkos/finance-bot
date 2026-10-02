from data_fetchers import (
    get_key_rate,
    get_ofz_short,
    get_sample_deposit_rates,
    get_currency_rates,
    get_inflation,
    net_yield,
    real_yield,
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
            "inflation": await get_inflation(),
        }

    def format_snapshot(self, data) -> str:
        kr = data["key_rate"]
        cur = data["currencies"]
        infl = data["inflation"]

        lines = [
            "СНИМОК РЫНКА",
            f"Ключевая ставка ЦБ: {kr['rate']}%",
            f"Инфляция: {infl['rate']}% (на {infl['date']})",
            f"Текущая сумма: {self.amount:,.0f} руб.",
            "",
            "Курсы валют ЦБ:",
            f"USD: {cur['USD']} руб. | EUR: {cur['EUR']} руб. | CNY: {cur['CNY']} руб.",
            f"(на {cur['date']})",
            "",
            "Короткие ОФЗ:",
        ]

        for i, b in enumerate(data["ofz"][:5], 1):
            ny = net_yield(b["ytm"])
            ry = real_yield(b["ytm"], infl["rate"])
            lines.append(
                f"{i}. {b['name']} - {b['ytm']}% "
                f"(после налога {ny}%, реальная {ry}%), погашение {b['matdate']}"
            )

        lines.append("")
        lines.append("Примеры вкладов (топ банки):")
        for i, d in enumerate(data["deposits"][:15], 1):
            income = self.amount * (d["rate"] / 100) * (d["term_months"] / 12) * 0.87
            ry = real_yield(d["rate"], infl["rate"])
            note = f" ({d['note']})" if d.get("note") else ""
            lines.append(
                f"{i}. {d['bank']} {d['rate']}% на {d['term_months']} мес. "
                f"({income:,.0f} руб. чистыми, реальная {ry}%){note}"
            )

        return "\n".join(lines)

    async def top3(self) -> str:
        data = await self.get_market_snapshot()
        infl = data["inflation"]["rate"]
        deps = sorted(data["deposits"], key=lambda x: x["rate"], reverse=True)[:3]
        ofz = data["ofz"][:3] if data["ofz"] else []

        lines = [
            "ТОП-3 ПРЯМО СЕЙЧАС",
            f"Сумма: {self.amount:,.0f} руб. | Инфляция: {infl}%",
            "",
            "Лучшие вклады:",
        ]
        for i, d in enumerate(deps, 1):
            income = self.amount * (d["rate"] / 100) * (d["term_months"] / 12) * 0.87
            ry = real_yield(d["rate"], infl)
            note = f" ({d['note']})" if d.get("note") else ""
            lines.append(
                f"{i}. {d['bank']} {d['rate']}% / {d['term_months']} мес. "
                f"-> {income:,.0f} руб. чистыми (реальная {ry}%){note}"
            )

        if ofz:
            lines.append("")
            lines.append("Лучшие короткие ОФЗ:")
            for i, b in enumerate(ofz, 1):
                income = self.amount * (b["ytm"] / 100) * (6 / 12) * 0.87
                ry = real_yield(b["ytm"], infl)
                lines.append(
                    f"{i}. {b['name']} {b['ytm']}% -> ~{income:,.0f} руб. "
                    f"(реальная {ry}%), погашение {b['matdate']}"
                )

        lines.append("")
        lines.append("АСВ страхует до 1.4 млн в одном банке.")
        return "\n".join(lines)

    async def calc(self, amount: float, months: int) -> str:
        data = await self.get_market_snapshot()
        infl = data["inflation"]["rate"]
        best_dep = max(data["deposits"], key=lambda x: x["rate"])
        best_ofz = data["ofz"][0] if data["ofz"] else None

        lines = [
            f"КАЛЬКУЛЯТОР",
            f"Сумма: {amount:,.0f} руб. на {months} мес.",
            f"Инфляция: {infl}%",
            "",
        ]

        dep_income = amount * (best_dep["rate"] / 100) * (months / 12) * 0.87
        dep_real = real_yield(best_dep["rate"], infl)
        lines.append(
            f"Лучший вклад: {best_dep['bank']} {best_dep['rate']}%\n"
            f"  Чистыми: ~{dep_income:,.0f} руб. (реальная {dep_real}%)"
        )

        if best_ofz:
            ofz_income = amount * (best_ofz["ytm"] / 100) * (months / 12) * 0.87
            ofz_real = real_yield(best_ofz["ytm"], infl)
            lines.append(
                f"Лучшая ОФЗ: {best_ofz['name']} {best_ofz['ytm']}%\n"
                f"  Чистыми: ~{ofz_income:,.0f} руб. (реальная {ofz_real}%)"
            )

        lines.append("")
        lines.append("Формула: сумма x ставка x (мес/12) x 0.87 (после НДФЛ 13%)")
        return "\n".join(lines)

    async def compare(self, months: int = 6) -> str:
        data = await self.get_market_snapshot()
        infl = data["inflation"]["rate"]

        lines = [
            f"СРАВНЕНИЕ НА {months} МЕСЯЦЕВ",
            f"Сумма: {self.amount:,.0f} руб.",
            f"Инфляция: {infl}%",
            "",
        ]

        suitable_deps = [d for d in data["deposits"] if d["term_months"] <= months + 1]
        suitable_deps.sort(key=lambda x: x["rate"], reverse=True)

        lines.append("Лучшие вклады:")
        for i, d in enumerate(suitable_deps[:7], 1):
            income = self.amount * (d["rate"] / 100) * (months / 12) * 0.87
            ry = real_yield(d["rate"], infl)
            lines.append(
                f"{i}. {d['bank']} {d['rate']}% -> ~{income:,.0f} руб. чистыми "
                f"(реальная {ry}%)"
            )

        lines.append("")
        lines.append("Короткие ОФЗ:")
        for i, b in enumerate(data["ofz"][:5], 1):
            income = self.amount * (b["ytm"] / 100) * (months / 12) * 0.87
            ry = real_yield(b["ytm"], infl)
            lines.append(
                f"{i}. {b['name']} {b['ytm']}% -> ~{income:,.0f} руб. "
                f"(реальная {ry}%), погашение {b['matdate']}"
            )

        lines.append("")
        lines.append(
            "Вывод: сравнивай реальную доходность. "
            "Вклады проще и в пределах АСВ, ОФЗ можно продать раньше."
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

    def format_portfolio(self, holdings: list) -> str:
        if not holdings:
            return (
                "Портфель пуст.\n"
                "Добавить: /hold вклад ВТБ 150000 13.7 6\n"
                "Формат: /hold тип банк сумма ставка месяцы"
            )
        lines = ["ТВОЙ ПОРТФЕЛЬ", ""]
        total = 0.0
        total_income = 0.0
        for i, h in enumerate(holdings, 1):
            amount = float(h.get("amount", 0))
            rate = float(h.get("rate", 0))
            months = int(h.get("months", 6))
            income = amount * (rate / 100) * (months / 12) * 0.87
            total += amount
            total_income += income
            lines.append(
                f"{i}. {h.get('type', 'вклад').upper()} {h.get('bank', '?')}\n"
                f"   {amount:,.0f} руб. @ {rate}% / {months} мес. "
                f"-> ~{income:,.0f} руб. чистыми"
            )
        lines.append("")
        lines.append(f"Всего: {total:,.0f} руб.")
        lines.append(f"Ожидаемый доход: ~{total_income:,.0f} руб. чистыми")
        if total > 1400000:
            lines.append("Внимание: сумма выше лимита АСВ (1.4 млн) — разбей по банкам.")
        return "\n".join(lines)

    async def answer(self, question: str) -> str:
        q = question.lower()
        if any(w in q for w in ["куда", "вложить", "рекоменд", "совет"]):
            return await self.recommend(6)
        if "топ" in q or "лучш" in q:
            return await self.top3()
        if "сравн" in q or "compare" in q:
            return await self.compare(6)
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
        return (
            "Команды:\n"
            "/top3 /rates /recommend /compare\n"
            "/calc 150000 6\n"
            "/hold вклад ВТБ 150000 13.7 6\n"
            "/portfolio /amount 150000"
        )
