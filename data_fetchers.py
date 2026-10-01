import httpx
from datetime import datetime, timedelta
from typing import Any

async def get_key_rate() -> dict[str, Any]:
    return {
        "rate": 14.00,
        "date": "2026-10-01",
        "next_meeting": "октябрь 2026",
    }

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
                    "coupon": item.get("COUPONPERCENT"),
                })
    except Exception as e:
        print("OFZ error:", e)

    results = [r for r in results if r.get("ytm")]
    results.sort(key=lambda x: x["ytm"], reverse=True)
    return results[:10]

async def get_sample_deposit_rates() -> list[dict[str, Any]]:
    return [
        {"bank": "Яндекс Банк", "product": "Сейв", "rate": 14.5, "term_months": 3, "note": "новые клиенты"},
        {"bank": "ДОМ.РФ", "product": "Мой Дом", "rate": 14.4, "term_months": 3, "note": "новые клиенты"},
        {"bank": "ПСБ", "product": "Сильная ставка", "rate": 14.15, "term_months": 6, "note": "новые деньги"},
        {"bank": "ВТБ", "product": "ВТБ-Вклад", "rate": 13.7, "term_months": 12, "note": "новые деньги"},
        {"bank": "Сбербанк", "product": "обычный", "rate": 12.5, "term_months": 6, "note": "без условий"},
    ]

def net_yield(rate: float) -> float:
    return round(rate * 0.87, 2)
