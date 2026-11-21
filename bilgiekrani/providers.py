"""Veri kaynakları. Her `parse_*` fonksiyonu ağdan bağımsızdır, test edilebilir."""
from __future__ import annotations

import re
import time
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from . import config

HEADERS = {"User-Agent": config.USER_AGENT}


def _get(url: str, retries: int = 3, **kwargs) -> requests.Response:
    """GET isteği; geçici ağ hatalarında kısa bekleyerek yeniden dener."""
    last: Exception | None = None
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=config.REQUEST_TIMEOUT, **kwargs)
            r.raise_for_status()
            return r
        except (requests.ConnectionError, requests.Timeout) as exc:
            last = exc
            time.sleep(1.5 * (attempt + 1))
    raise last  # type: ignore[misc]


# ---------------------------------------------------------------- Hava durumu
# WMO hava kodları -> (Türkçe açıklama, simge)
WMO = {
    0: ("Açık", "☀️"), 1: ("Çoğunlukla açık", "🌤️"), 2: ("Parçalı bulutlu", "⛅"),
    3: ("Kapalı", "☁️"), 45: ("Sisli", "🌫️"), 48: ("Kırağılı sis", "🌫️"),
    51: ("Hafif çise", "🌦️"), 53: ("Çise", "🌦️"), 55: ("Yoğun çise", "🌧️"),
    56: ("Dondurucu çise", "🌧️"), 57: ("Dondurucu çise", "🌧️"),
    61: ("Hafif yağmur", "🌦️"), 63: ("Yağmur", "🌧️"), 65: ("Şiddetli yağmur", "🌧️"),
    66: ("Dondurucu yağmur", "🌧️"), 67: ("Dondurucu yağmur", "🌧️"),
    71: ("Hafif kar", "🌨️"), 73: ("Kar", "🌨️"), 75: ("Yoğun kar", "❄️"),
    77: ("Kar taneleri", "🌨️"), 80: ("Sağanak", "🌦️"), 81: ("Sağanak", "🌧️"),
    82: ("Şiddetli sağanak", "⛈️"), 85: ("Kar sağanağı", "🌨️"),
    86: ("Yoğun kar sağanağı", "❄️"), 95: ("Gök gürültülü fırtına", "⛈️"),
    96: ("Dolulu fırtına", "⛈️"), 99: ("Dolulu fırtına", "⛈️"),
}


def parse_weather(data: dict) -> dict:
    cur = data["current"]
    daily = data["daily"]
    text, icon = WMO.get(cur["weather_code"], ("—", "🌡️"))
    return {
        "city": config.CITY,
        "temp": round(cur["temperature_2m"]),
        "feels": round(cur["apparent_temperature"]),
        "humidity": round(cur["relative_humidity_2m"]),
        "wind": round(cur["wind_speed_10m"]),
        "text": text,
        "icon": icon,
        "max": round(daily["temperature_2m_max"][0]),
        "min": round(daily["temperature_2m_min"][0]),
        "rain": daily["precipitation_probability_max"][0],
    }


def fetch_weather() -> dict:
    r = _get(
        "https://api.open-meteo.com/v1/forecast",
        params={
            "latitude": config.LAT,
            "longitude": config.LON,
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m,"
                       "weather_code,wind_speed_10m",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max",
            "timezone": "Europe/Istanbul",
            "forecast_days": 1,
        },
    )
    return parse_weather(r.json())


# ------------------------------------------------------------- Döviz / kripto
def parse_fx(data: dict) -> list[dict]:
    rates = data["rates"]
    try_per_usd = rates["TRY"]
    return [
        {"key": "USDTRY", "label": "USD/TL", "value": try_per_usd, "change": None},
        {"key": "EURTRY", "label": "EUR/TL", "value": try_per_usd / rates["EUR"], "change": None},
    ]


def _yahoo_chart(symbol: str) -> dict:
    r = _get(
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}",
        params={"range": "1d", "interval": "1d"},
    )
    return r.json()


def fetch_fx() -> list[dict]:
    """Önce Yahoo (günlük % değişimli); olmazsa değişimsiz yedek kaynak."""
    try:
        return [
            parse_index(_yahoo_chart(sym), key, label)
            for sym, key, label in (("TRY=X", "USDTRY", "USD/TL"), ("EURTRY=X", "EURTRY", "EUR/TL"))
        ]
    except Exception:
        return parse_fx(_get("https://open.er-api.com/v6/latest/USD").json())


def parse_crypto(data: dict) -> list[dict]:
    out = []
    for key, cid, label in (("BTCTRY", "bitcoin", "Bitcoin/TL"), ("ETHTRY", "ethereum", "Ethereum/TL")):
        d = data[cid]
        out.append({"key": key, "label": label, "value": d["try"], "change": d.get("try_24h_change")})
    return out


def fetch_crypto() -> list[dict]:
    r = _get(
        "https://api.coingecko.com/api/v3/simple/price",
        params={"ids": "bitcoin,ethereum", "vs_currencies": "try", "include_24hr_change": "true"},
    )
    return parse_crypto(r.json())


def parse_index(data: dict, key: str, label: str) -> dict:
    meta = data["chart"]["result"][0]["meta"]
    price = meta["regularMarketPrice"]
    prev = meta.get("chartPreviousClose") or meta.get("previousClose")
    change = (price / prev - 1) * 100 if prev else None
    return {"key": key, "label": label, "value": price, "change": change}


def fetch_indices() -> list[dict]:
    return [
        parse_index(_yahoo_chart(sym), key, label)
        for sym, key, label in (("XU100.IS", "BIST100", "BIST 100"), ("^IXIC", "NASDAQ", "Nasdaq"))
    ]


# ------------------------------------------------------------------ Yemek
def parse_lunch(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    section = soup.select_one("section#ogle")
    items = []
    if section:
        for card in section.select(".menu-card"):
            items.append({
                "title": card.get("data-title", "").strip(),
                "category": card.get("data-category", "").strip(),
                "kcal": int(card["data-cal"]) if card.get("data-cal", "").isdigit() else None,
            })
    return {"items": items, "kcal": sum(i["kcal"] or 0 for i in items)}


def fetch_lunch() -> dict:
    r = _get("https://beslenme.hacettepe.edu.tr/", params={"location_id": config.LUNCH_LOCATION_ID})
    return parse_lunch(r.text)


# ------------------------------------------------------------------ Haberler
GAZETE = "https://gazete.hacettepe.edu.tr/"


def parse_news(html: str, limit: int = 6) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for box in soup.select(".slide_txt"):
        title = box.select_one(".slide_baslik")
        if not title:
            continue
        summary = box.select_one(".slide_ozet")
        link = box.select_one("a[href]")
        out.append({
            "title": " ".join(title.get_text().split()),
            "summary": " ".join(summary.get_text().split()) if summary else "",
            "url": urljoin(GAZETE, link["href"]) if link else GAZETE,
        })
    return out[:limit]


def fetch_news() -> list[dict]:
    return parse_news(_get(GAZETE).text)


# --------------------------------------------------------------- Etkinlikler
ETKINLIK = "https://etkinlikler.hacettepe.edu.tr/"
_DATE_RE = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})\s*(\d{2}:\d{2})?")


def parse_events(html: str, limit: int = 6) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for card in soup.select(".haber_card"):
        title = card.select_one(".haber_card_baslik")
        foot = card.select_one(".haber_alt")
        if not title or not foot:
            continue
        m = _DATE_RE.search(foot.get_text(" "))
        if not m:
            continue  # tarihsiz (eski) kayıtları atla
        d, mo, y, hm = m.groups()
        kind = foot.get_text(" ").split("|")[-1].strip()
        link = card.select_one("a[href]")
        out.append({
            "title": " ".join(title.get_text().split()),
            "date": f"{y}-{mo}-{d}",
            "time": hm or "",
            "kind": kind,
            "url": urljoin(ETKINLIK, link["href"]) if link else ETKINLIK,
        })
    out.sort(key=lambda e: (e["date"], e["time"]))
    return out[:limit]


def fetch_events() -> list[dict]:
    return parse_events(_get(ETKINLIK).text)
