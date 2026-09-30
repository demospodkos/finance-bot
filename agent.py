"""
Финансовый ИИ-агент для рублёвых вложений с минимальным риском.
Сумма по умолчанию: 300 000 ₽.
"""

from __future__ import annotations

import os
from typing import Any
from data_fetchers import (
    get_key_rate,
    get_ofz_short,
    get_sample_deposit_rates,
    calculate_net_yield,
)

# Системный промпт для LLM-агента
SYSTEM_PROMPT = """
Ты — личный финансовый помощник пользователя по рублёвым инструментам с минимальным риском.
Сумма капитала пользователя: примерно 300 000 рублей.

Правила:
1. Рекомендуй ТОЛЬКО инструменты минимального риска:
   - Вклады в банках в пределах страховки АСВ (1,4 млн ₽).
   - Короткие ОФЗ (погашение до 1,5–2 лет).
   - Накопительные счета крупных банков.
2. Никогда не рекомендуй акции, крипту, корпоративные облигации низкого рейтинга, ПИФы с высокой волатильностью.
3. Всегда указывай:
   - Номинальную ставку / YTM
   - Примерную доходность после налога (13%)
   - Срок
   - Ограничения (новые деньги, новые клиенты и т.д.)
4. Учитывай текущую ключевую ставку ЦБ и инфляцию.
5. Если пользователь спрашивает «куда вложить» — дай 2–3 конкретных варианта с расчётом дохода на 300к.
6. Будь честным: полностью безрисковых инвестиций с высокой доходностью не существует.
7. Отвечай на русском языке, кратко, структурировано, с эмодзи для читаемости.
8. Если данных недостаточно — скажи об этом и предложи проверить актуальные ставки на Банки.ру / сайте банка.
"""


class FinanceAgent:
    def __init__(self, amount: float = 300_000):
        self.amount = amount
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    async def get_market_snapshot(self) -> dict[str, Any]:
        """Собирает актуальный снимок рынка."""
        key_rate = await get_key_rate()
        ofz = await get_ofz_short()
        deposits = await get_sample_deposit_rates()

        return {
            "key_rate": key_rate,
            "ofz_short": ofz,
            "deposits": deposits,
            "amount": self.amount,
        }

    def format_snapshot(self, snapshot: dict[str, Any]) -> str:
        """Форматирует снимок в читаемый текст."""
        kr = snapshot["key_rate"]
        lines = [
            f"📊 *Снимок рынка (рубли)*",
            f"",
            f"🔑 Ключевая ставка ЦБ: *{kr['rate']}%* (на {kr['date']})",
            f"📅 Следующее заседание: {kr.get('next_meeting', 'см. сайт ЦБ')}",
            f"",
            f"💰 Капитал пользователя: *{self.amount:,.0f} ₽*",
            f"",
            f"*Лучшие короткие ОФЗ (пример):*",
        ]

        for i, bond in enumerate(snapshot["ofz_short"][:5], 1):
            net = calculate_net_yield(bond["ytm"], is_ofz=True)
            lines.append(
                f"{i}. {bond['name']} ({bond['secid']}) — YTM {bond['ytm']}% "
                f"(\~{net}% после налога), погашение {bond['matdate']}"
            )

        lines.append("")
        lines.append("*Примеры вкладов (проверьте актуальность):*")
        for i, dep in enumerate(snapshot["deposits"][:5], 1):
            net = calculate_net_yield(dep["rate"])
            income = self.amount * (dep["rate"] / 100) * (dep["term_months"] / 12)
            net_income = income * 0.87
            lines.append(
                f"{i}. {dep['bank']} «{dep['product']}» — {dep['rate']}% на {dep['term_months']} мес. "
                f"(\~{net}% net). Примерный доход на 300к: \~{net_income:,.0f} ₽. {dep['note']}"
            )

        lines.append("")
        lines.append(
            "⚠️ Данные по вкладам — ориентировочные. Перед открытием проверяйте на сайте банка и Банки.ру."
        )
        return "\n".join(lines)

    async def recommend(self) -> str:
        """Основная рекомендация для 300к."""
        snapshot = await self.get_market_snapshot()
        text = self.format_snapshot(snapshot)

        recommendation = (
            "\n\n"
            "✅ *Рекомендация агента для 300 000 ₽ (минимальный риск):*\n\n"
            "1. **Основной вариант** — вклад в надёжном банке на 3–6 месяцев под максимальную доступную ставку "
            "(сейчас ориентир 13,5–14,5%). Вся сумма в пределах АСВ.\n"
            "2. **Альтернатива** — короткие ОФЗ с погашением в 2027 году. "
            "Можно купить через брокера (Тинькофф, ВТБ, Сбер и т.д.). Ликвидность выше, чем у вклада.\n"
            "3. **Часть на накопительный счёт** (10–20%) — для гибкости.\n\n"
            "Не кладите все деньги в один банк на максимальный срок, если может понадобиться доступ раньше. "
            "При снижении ключевой ставки ЦБ ставки по вкладам тоже пойдут вниз — фиксируйте сейчас на разумный срок."
        )
        return text + recommendation

    async def answer(self, user_question: str) -> str:
        """
        Ответ с помощью LLM (если есть ключ) или fallback на правила.
        """
        snapshot = await self.get_market_snapshot()
        context = self.format_snapshot(snapshot)

        if not self.api_key:
            q = user_question.lower()
            if any(w in q for w in ["куда", "вложить", "рекоменд", "совет"]):
                return await self.recommend()
            if "офз" in q or "облигац" in q:
                return context
            if "вклад" in q or "депозит" in q:
                return context
            return (
                "Я финансовый агент по рублёвым инструментам минимального риска.\n"
                "Спросите: «куда вложить», «ставки по вкладам», «короткие ОФЗ» или /recommend"
            )

        try:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"Текущие данные рынка:\n{context}\n\nВопрос пользователя: {user_question}",
                },
            ]
            resp = await client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.3,
                max_tokens=800,
            )
            return resp.choices[0].message.content or "Не удалось получить ответ."
        except Exception as e:
            return f"Ошибка LLM: {e}\n\nFallback:\n{await self.recommend()}"
