#!/usr/bin/env bash
# Sunucu hazır olunca Chromium'u tam ekran (kiosk) açar; tarayıcı kapanırsa yeniden açar.
# Masaüstü oturumu açılırken otomatik çalıştırılır (bkz. deploy/install.sh).
set -u

URL="${BE_URL:-http://127.0.0.1:8080}"

# Aynı anda ikinci bir kopya çalışmasın (birden fazla autostart yolu olabilir).
exec 9>/tmp/bilgiekrani-kiosk.lock
flock -n 9 || exit 0

BROWSER="$(command -v chromium-browser || command -v chromium || true)"
if [ -z "$BROWSER" ]; then
  echo "Chromium bulunamadı" >&2
  exit 1
fi

# Ekran koruyucu / uyku kapalı (X11 oturumlarında; Wayland'de install.sh ayarlar)
if command -v xset >/dev/null 2>&1 && [ -n "${DISPLAY:-}" ]; then
  xset s off -dpms s noblank 2>/dev/null || true
fi

# Sunucu cevap verene kadar bekle (en fazla 3 dk). İnternet gerekmez, yalnızca yerel sunucu.
for _ in $(seq 1 90); do
  curl -fsS -m 2 "$URL/api/health" >/dev/null 2>&1 && break
  sleep 2
done

while true; do
  # Her açılışta temiz profil: ani elektrik kesintisinden sonra "oturumu geri yükle" çıkmaz.
  rm -rf /tmp/bilgiekrani-chromium
  "$BROWSER" \
    --kiosk \
    --user-data-dir=/tmp/bilgiekrani-chromium \
    --noerrdialogs --disable-infobars --disable-session-crashed-bubble \
    --disable-features=Translate --no-first-run --password-store=basic \
    --overscroll-history-navigation=0 --disable-pinch \
    "$URL"
  sleep 3
done
