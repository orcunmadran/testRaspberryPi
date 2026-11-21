from pathlib import Path

from bilgiekrani import providers as p

FIX = Path(__file__).parent / "fixtures"


def read(name):
    return (FIX / name).read_text(encoding="utf-8")


def test_parse_lunch_only_ogle_section():
    lunch = p.parse_lunch(read("beslenme.html"))
    assert len(lunch["items"]) == 4
    assert lunch["items"][0]["title"] == "Bulgur Çorbası"
    assert lunch["items"][0]["category"] == "ÇORBA"
    assert lunch["kcal"] == sum(i["kcal"] for i in lunch["items"]) == 1018


def test_parse_lunch_empty():
    assert p.parse_lunch("<html></html>") == {"items": [], "kcal": 0}


def test_parse_news():
    news = p.parse_news(read("gazete.html"))
    assert len(news) == 6
    assert news[0]["title"].startswith("Hacettepe Üniversitesinden Türkmenistan")
    assert all(n["url"].startswith("https://gazete.hacettepe.edu.tr") or n["url"].startswith("http") for n in news)


def test_parse_events_sorted_and_dated():
    ev = p.parse_events(read("etkinlikler.html"))
    assert ev, "etkinlik bulunamadı"
    assert ev == sorted(ev, key=lambda e: (e["date"], e["time"]))
    assert all(len(e["date"]) == 10 for e in ev)  # tarihsiz kayıtlar atlanır
    assert ev[0]["date"] == "2026-11-20"
    assert ev[0]["url"].startswith("https://etkinlikler.hacettepe.edu.tr")


def test_parse_fx():
    out = p.parse_fx({"rates": {"TRY": 50.0, "EUR": 0.9}})
    assert out[0]["value"] == 50.0
    assert round(out[1]["value"], 2) == 55.56


def test_parse_crypto():
    out = p.parse_crypto({"bitcoin": {"try": 100, "try_24h_change": -1.5},
                          "ethereum": {"try": 10, "try_24h_change": 2.0}})
    assert [o["key"] for o in out] == ["BTCTRY", "ETHTRY"]
    assert out[0]["change"] == -1.5


def test_parse_index_percent():
    data = {"chart": {"result": [{"meta": {"regularMarketPrice": 90.0, "chartPreviousClose": 100.0}}]}}
    r = p.parse_index(data, "X", "X")
    assert round(r["change"], 2) == -10.0


def test_parse_weather():
    data = {
        "current": {"temperature_2m": 13.6, "apparent_temperature": 11.6,
                    "relative_humidity_2m": 85, "weather_code": 0, "wind_speed_10m": 16.5},
        "daily": {"temperature_2m_max": [16.2], "temperature_2m_min": [9.1],
                  "precipitation_probability_max": [40]},
    }
    w = p.parse_weather(data)
    assert w["temp"] == 14 and w["text"] == "Açık" and w["rain"] == 40
