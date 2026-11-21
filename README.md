# testRaspberryPi — Bilgi Ekranı

Raspberry Pi'ye bağlı 1920x1080 TV için Python (Flask) ile çalışan bilgi panosu.

![Ekran görüntüsü](docs/ekran.png)

## Gösterilenler
- Hacettepe Üniversitesi arması, bölüm adı, saat ve tarih
- Hava durumu (Open-Meteo, varsayılan: Ankara)
- USD/TL, EUR/TL, Bitcoin/TL, Ethereum/TL, BIST 100, Nasdaq (hepsinde günlük % değişim; ▲ artı, ▼ eksi)
- İki aylık takvim (mevcut ve sonraki ay, yan yana kare)
- Günlük öğle yemeği listesi (beslenme.hacettepe.edu.tr)
- Hacettepe haberleri (gazete.hacettepe.edu.tr) ve haberler sayfasına karekod
- Yaklaşan etkinlikler (etkinlikler.hacettepe.edu.tr) ve etkinlikler sayfasına karekod

## Çalıştırma
```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m bilgiekrani.app      # http://<adres>:8080
```

Ayarlar ortam değişkenleriyle yapılır: `PORT`, `BE_CITY`, `BE_LAT`, `BE_LON`,
`BE_LUNCH_LOCATION` (1 = Beytepe, 2 = Sıhhiye).

## Raspberry Pi'de TV'de açma (kiosk)
```bash
chromium-browser --kiosk --noerrdialogs --disable-infobars http://localhost:8080
```
Sayfa 1920x1080 tasarımı ekrana ölçekler. Kenarlarda 48 px boşluk vardır (TV overscan payı).

## Geliştirme
```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest
.venv/bin/python scripts/screenshot.py docs/ekran.png   # 1920x1080 görüntü
```
Playwright'ın tarayıcısı yoksa `CHROMIUM_PATH=/yol/chromium` verilebilir.

## Notlar
- Veri kaynakları önbelleğe alınır; bir kaynak erişilemezse son başarılı veri gösterilir ve köşede uyarı çıkar.
- USD/EUR günlük değişimi Yahoo Finance'ten gelir; erişilemezse open.er-api.com yedeği kullanılır (yüzde gösterilmez).
- Karekodları yeniden üretmek için: `python scripts/make_qr.py` (adresler o dosyada).
- Logo, www.hacettepe.edu.tr'deki resmî arma SVG'sinden kırpılmıştır (`bilgiekrani/static/logo.svg`).
- Siteler yapısını değiştirirse `bilgiekrani/providers.py` içindeki `parse_*` fonksiyonları ve `tests/fixtures` güncellenmelidir.
