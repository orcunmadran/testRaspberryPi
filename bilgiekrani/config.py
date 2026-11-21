"""Ayarlar. Ortam değişkenleriyle değiştirilebilir."""
import os

# Hava durumu konumu (varsayılan: Ankara / Hacettepe Beytepe civarı)
LAT = float(os.environ.get("BE_LAT", "39.93"))
LON = float(os.environ.get("BE_LON", "32.86"))
CITY = os.environ.get("BE_CITY", "Ankara")

# Yemek listesi konumu: 1 = Beytepe, 2 = Sıhhiye
LUNCH_LOCATION_ID = int(os.environ.get("BE_LUNCH_LOCATION", "1"))

REQUEST_TIMEOUT = 15
USER_AGENT = "Mozilla/5.0 (compatible; BilgiEkrani/1.0)"

# Önbellek süreleri (saniye)
TTL = {
    "weather": 15 * 60,
    "fx": 30 * 60,
    "crypto": 2 * 60,
    "indices": 5 * 60,
    "lunch": 60 * 60,
    "news": 30 * 60,
    "events": 60 * 60,
}
