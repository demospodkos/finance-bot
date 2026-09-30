"""
Модуль сбора данных для финансового агента (рубли, РФ).
"""

from __future__ import annotations

import httpx
from datetime import datetime, timedelta
from typing import Any

# --- Ключевая ставка ЦБ ---
async def get_key_rate() -> dict[str, Any]:
    """Получает текущую ключевую ставку ЦБ РФ."""
    # Актуальная ставка (обновлять при необходимости)
    return {
        "rate": 14.00,
        "date": "2026-09-29",
        "source": "ЦБ РФ (актуально на момент создания прототипа)",
        "next_meeting": "ориентировочно 23 октября 2026",
    }


async def get_ofz_short() -> list[dict[str, Any]]:
    """
    Получает короткие ОФЗ (погашение в ближайшие 1-2 года) с Московской биржи.
    Использует публичный ISS API.
    """
    url = (
        "https://iss.moex.com/iss/engines/stock/markets/bonds/boards/TQOB/securities.json"
        "?iss.meta=off"
        "&securities.columns=SECID,SHORTNAME,PREVPRICE,YIELDATPREVWAPRICE,MATDATE,COUPONPERCENT,FACEVALUE,CURRENCYID"
        "&limit=200"
    )
    results = []
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()

            columns = data.get("securities", {}).get("columns", [])
            rows = data.get("securities", {}).get("data", [])

            for row in rows:
                item = dict(zip(columns, row))
                # Только рублёвые
                if item.get("CURRENCYID") and item.get("CURRENCYID") != "SUR":
                    continue
                matdate = item.get("MATDATE")
                if not matdate:
                    continue
                # Фильтруем короткие (до \~2 лет)
                try:
                    mat = datetime.strptime(matdate, "%Y-%m-%d")
                    if mat > datetime.now() + timedelta(days=800):
                        continue
                except Exception:
                    continue

                ytm = item.get("YIELDATPREVWAPRICE")
                if ytm is None:
                    continue

                results.append({
                    "secid": item.get("SECID"),
                    "name": item.get("SHORTNAME"),
                    "price": item.get("PREVPRICE"),
                    "ytm": round(float(ytm), 2) if ytm else None,
                    "matdate": matdate,
                    "coupon": item.get("COUPONPERCENT"),
                    "facevalue": item.get("FACEVALUE"),
                })
    except Exception as e:
        results.append({"error": str(e)})

    # Сортируем по доходности убыванию
    results = [r for r in results if r.get("ytm") is not None]
    results.sort(key=lambda x: x["ytm"], reverse=True)
    return results[:15]


async def get_sample_deposit_rates() -> list[dict[str, Any]]:
    """
    Пример ставок по вкладам (в реальном боте — парсинг Банки.ру / Сравни.ру).
    Для 300к ₽ в пределах АСВ.
    """
    return [
        {
            "bank": "Яндекс Банк",
            "product": "Сейв",
            "rate": 14.5,
            "term_months": 3,
            "min_amount": 10000,
            "note": "новые клиенты / онлайн",
        },
        {
            "bank": "ВТБ",
            "product": "ВТБ-Вклад",
            "rate": 13.7,
            "term_months": 12,
            "min_amount": 1000,
            "note": "новые деньги",
        },
        {
            "bank": "ПСБ",
            "product": "Сильная ставка",
            "rate": 14.15,
            "term_months": 6,
            "min_amount": 10000,
            "note": "новые деньги",
        },
        {
            "bank": "ДОМ.РФ",
            "product": "Мой Дом",
            "rate": 14.4,
            "term_months": 3,
            "min_amount": 10000,
            "note": "новые клиенты",
        },
        {
            "bank": "Сбербанк",
            "product": "обычный вклад",
            "rate": 12.5,
            "term_months": 6,
            "min_amount": 1000,
            "note": "без спец.условий",
        },
    ]


def calculate_net_yield(gross_rate: float, is_ofz: bool = False) -> float:
    """
    Примерный расчёт доходности после НДФЛ.
    """
    tax = 0.13
    return round(gross_rate * (1 - tax), 2)
