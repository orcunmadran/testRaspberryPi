"""Panonun 1920x1080 ekran görüntüsünü alır.

Kullanım: python scripts/screenshot.py [çıktı.png] [--url http://127.0.0.1:8080]
Sunucu çalışmıyorsa kendisi başlatır.
"""
import argparse
import os
import sys
import threading
import time
from pathlib import Path

from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from bilgiekrani.app import create_app  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out", nargs="?", default="docs/ekran.png")
    ap.add_argument("--url")
    args = ap.parse_args()

    server = None
    url = args.url
    if not url:
        server = make_server("127.0.0.1", 0, create_app(), threaded=True)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        url = f"http://127.0.0.1:{server.server_port}"

    with sync_playwright() as p:
        exe = os.environ.get("CHROMIUM_PATH")
        browser = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
        page = browser.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
        page.goto(url)
        page.wait_for_function("document.querySelector('#markets .value') && document.querySelector('#newsBody .item') && document.querySelector('#eventsBody .item')", timeout=90000)
        time.sleep(1)
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=args.out)
        browser.close()
    if server:
        server.shutdown()
    print("kaydedildi:", args.out)


if __name__ == "__main__":
    main()
