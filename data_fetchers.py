import httpx
from datetime import datetime, timedelta
from typing import Any

async def get_key_rate() -> dict[str, Any]:
    return {
        "rate": 14.00,
        "date": "2026-10-01",
        "next_meeting": "октябрь 2026",
    }

async def get_currency_rates() -> dict[str, Any]:
    """Официальные курсы ЦБ: доллар, евро, юань"""
    url = "https://www.cbr-xml-daily.ru/daily_json.js"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url)
            data = resp.json()
            valute = data.get("Valute", {})
            return {
                "date": data.get("Date", "")[:10],
                "USD": round(valute.get("USD", {}).get("Value", 0), 2),
                "EUR": round(valute.get("EUR", {}).get("Value", 0), 2),
                "CNY": round(valute.get("CNY", {}).get("Value", 0), 2),
            }
    except Exception as e:
        print("Currency error:", e)
        return {"date": "н/д", "USD": 0, "EUR": 0, "CNY": 0}

async def get_ofz_short() -> list[dict[str, Any]]:
    url = (
        "https://iss.moex.com/iss/engines/stock/markets/bonds/boards/TQOB/securities.json"
        "?iss.meta=off"
        "&securities.columns=SECID,SHORTNAME,PREVPRICE,YIELDATPREVWAPRICE,MATDATE,COUPONPERCENT,CURRENCYID"
        "&limit=200"
    )
    results = []
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url)
            data = resp.json()
            columns = data.get("securities", {}).get("columns", [])
            rows = data.get("securities", {}).get("data", [])

            for row in rows:
                item = dict(zip(columns, row))
                if item.get("CURRENCYID") != "SUR":
                    continue
                matdate = item.get("MATDATE")
                if not matdate:
                    continue
                try:
                    mat = datetime.strptime(matdate, "%Y-%m-%d")
                    if mat > datetime.now() + timedelta(days=750):
                        continue
                except Exception:
                    continue
                ytm = item.get("YIELDATPREVWAPRICE")
                if ytm is None:
                    continue
                results.append({
                    "secid": item.get("SECID"),
                    "name": item.get("SHORTNAME"),
                    "ytm": round(float(ytm), 2),
                    "matdate": matdate,
                })
    except Exception as e:
        print("OFZ error:", e)

    results = [r for r in results if r.get("ytm")]
    results.sort(key=lambda x: x["ytm"], reverse=True)
    return results[:8]

async def get_sample_deposit_rates() -> list[dict[str, Any]]:
    """Примеры ставок крупных банков (топ по активам). Ставки ориентировочные."""
    return [
        {"bank": "Сбербанк", "rate": 12.5, "term_months": 6, "note": "без условий"},
        {"bank": "ВТБ", "rate": 13.7, "term_months": 12, "note": "новые деньги"},
        {"bank": "Газпромбанк", "rate": 13.5, "term_months": 6, "note": "онлайн"},
        {"bank": "Альфа-Банк", "rate": 14.0, "term_months": 3, "note": "новые клиенты"},
        {"bank": "Т-Банк", "rate": 14.2, "term_months": 3, "note": "новые деньги"},
        {"bank": "Россельхозбанк", "rate": 13.3, "term_months": 6, "note": ""},
        {"bank": "ДОМ.РФ", "rate": 14.4, "term_months": 3, "note": "новые клиенты"},
        {"bank": "МКБ", "rate": 14.0, "term_months": 6, "note": ""},
        {"bank": "Совкомбанк", "rate": 13.8, "term_months": 6, "note": "с Халвой"},
        {"bank": "Райффайзенбанк", "rate": 12.0, "term_months": 6, "note": ""},
        {"bank": "ПСБ", "rate": 14.15, "term_months": 6, "note": "новые деньги"},
        {"bank": "БСПБ", "rate": 13.9, "term_months": 3, "note": ""},
        {"bank": "Уралсиб", "rate": 13.5, "term_months": 6, "note": ""},
        {"bank": "МТС Банк", "rate": 13.7, "term_months": 3, "note": ""},
        {"bank": "Яндекс Банк", "rate": 14.5, "term_months": 3, "note": "новые клиенты"},
        {"bank": "Озон Банк", "rate": 13.5, "term_months": 6, "note": ""},
        {"bank": "Абсолют Банк", "rate": 14.0, "term_months": 6, "note": ""},
        {"bank": "Ак Барс", "rate": 13.4, "term_months": 6, "note": ""},
        {"bank": "Экспобанк", "rate": 13.8, "term_months": 3, "note": ""},
        {"bank": "Новикомбанк", "rate": 13.6, "term_months": 6, "note": ""},
    ]

def net_yield(rate: float) -> float:
    return round(rate * 0.87, 2)
