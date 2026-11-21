"""Karekod SVG'lerini üretir (bir kez çalıştırılır, çıktılar depoya eklenir).

Kullanım: python scripts/make_qr.py
"""
from pathlib import Path

import segno

OUT = Path(__file__).resolve().parent.parent / "bilgiekrani" / "static"
CODES = {
    "qr_etkinlik.svg": "https://etkinlikler.hacettepe.edu.tr/",
    "qr_haber.svg": "https://gazete.hacettepe.edu.tr/tr/haberler",
}

for name, url in CODES.items():
    qr = segno.make(url, error="m")
    qr.save(OUT / name, kind="svg", scale=8, border=2, dark="#0b1220", light="#ffffff")
    print(name, "->", url)
