#!/usr/bin/env bash
# Raspberry Pi'de bir kez çalıştırılır:  bash deploy/install.sh
# - Python ortamını kurar
# - Sunucuyu systemd servisi yapar (Pi açılınca otomatik başlar, çökerse yeniden başlar)
# - Masaüstü açılınca tarayıcıyı tam ekran açar
# - Ekranın kararmasını kapatır
set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
USER_NAME="$(id -un)"
HOME_DIR="$HOME"

echo "==> Python ortamı"
python3 -m venv "$DIR/.venv"
"$DIR/.venv/bin/pip" install -q -r "$DIR/requirements.txt"

echo "==> systemd servisi"
sed -e "s|__USER__|$USER_NAME|g" -e "s|__DIR__|$DIR|g" "$DIR/deploy/bilgiekrani.service" \
  | sudo tee /etc/systemd/system/bilgiekrani.service >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable --now bilgiekrani.service

echo "==> Tarayıcı (kiosk) otomatik başlatma"
chmod +x "$DIR/deploy/kiosk.sh"
mkdir -p "$HOME_DIR/.config/autostart"
cat > "$HOME_DIR/.config/autostart/bilgiekrani-kiosk.desktop" <<EOT
[Desktop Entry]
Type=Application
Name=Bilgi Ekrani
Exec=$DIR/deploy/kiosk.sh
X-GNOME-Autostart-enabled=true
EOT
# labwc (Raspberry Pi OS Bookworm varsayılanı) için de ekle; kiosk.sh kilitli olduğu için çift açılmaz.
if [ -d "$HOME_DIR/.config/labwc" ] || command -v labwc >/dev/null 2>&1; then
  mkdir -p "$HOME_DIR/.config/labwc"
  touch "$HOME_DIR/.config/labwc/autostart"
  grep -qF "deploy/kiosk.sh" "$HOME_DIR/.config/labwc/autostart" \
    || echo "$DIR/deploy/kiosk.sh &" >> "$HOME_DIR/.config/labwc/autostart"
fi

echo "==> Ekran kararmasını kapat"
sudo raspi-config nonint do_blanking 1 || echo "(raspi-config ile kapatılamadı; elle kapat: Ayarlar > Ekran)"

echo
echo "Tamam. Yeniden başlat:  sudo reboot"
echo "Servis durumu:          systemctl status bilgiekrani"
echo "Günlük:                 journalctl -u bilgiekrani -f"
