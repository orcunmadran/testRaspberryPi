"""Flask sunucusu: pano sayfasını ve /api/data uç noktasını sunar."""
from __future__ import annotations

import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from flask import Flask, jsonify, send_from_directory

from . import config, providers

log = logging.getLogger("bilgiekrani")

SOURCES = {
    "weather": providers.fetch_weather,
    "fx": providers.fetch_fx,
    "crypto": providers.fetch_crypto,
    "indices": providers.fetch_indices,
    "lunch": providers.fetch_lunch,
    "news": providers.fetch_news,
    "events": providers.fetch_events,
}


class Cache:
    """Kaynak başına TTL önbellek. Çekme başarısız olursa eski veri korunur.

    Başarısız kaynak 30 sn sonra yeniden denenir (WiFi geç gelirse toparlansın).
    """

    RETRY_AFTER = 30

    def __init__(self, sources=None, ttl=None, clock=time.monotonic):
        self.sources = sources or SOURCES
        self.ttl = ttl or config.TTL
        self.clock = clock
        self._locks = {name: threading.Lock() for name in self.sources}
        self._store: dict[str, dict] = {}

    def get(self, name: str) -> dict:
        with self._locks[name]:
            entry = self._store.get(name)
            now = self.clock()
            if entry and now - entry["at"] < self.ttl[name]:
                return entry
            try:
                data = self.sources[name]()
                entry = {"data": data, "at": now, "stale": False}
            except Exception as exc:  # ağ/ayrıştırma hatası: eski veriyle devam et
                log.warning("%s alınamadı: %s", name, exc)
                retry_at = now - self.ttl[name] + self.RETRY_AFTER
                entry = {"data": entry["data"] if entry else None, "at": retry_at, "stale": True}
            self._store[name] = entry
            return entry

    def snapshot(self) -> tuple[dict, bool]:
        """Tüm kaynakları paralel getirir. (bölümler, online) döner.

        online: en az bir kaynak güncel veriyle alınabildi mi (internet var mı).
        """
        names = list(self.sources)
        with ThreadPoolExecutor(max_workers=len(names)) as pool:
            entries = list(pool.map(self.get, names))
        sections = {n: {"data": e["data"], "stale": e["stale"]} for n, e in zip(names, entries)}
        online = any(e["data"] is not None and not e["stale"] for e in entries)
        return sections, online


def create_app(cache: Cache | None = None) -> Flask:
    static = Path(__file__).parent / "static"
    app = Flask(__name__, static_folder=str(static), static_url_path="/static")
    cache = cache or Cache()

    @app.get("/")
    def index():
        return send_from_directory(static, "index.html")

    @app.get("/api/data")
    def data():
        sections, online = cache.snapshot()
        resp = jsonify({"generated": time.time(), "online": online, "sections": sections})
        resp.headers["Cache-Control"] = "no-store"
        return resp

    @app.get("/api/health")
    def health():
        """Sunucu ayakta mı? (internet gerekmez; kiosk betiği bunu bekler)"""
        return jsonify({"ok": True})

    return app


def main():
    logging.basicConfig(level=logging.INFO)
    port = int(os.environ.get("PORT", "8080"))
    host = os.environ.get("BE_HOST", "0.0.0.0")
    create_app().run(host=host, port=port, threaded=True)


if __name__ == "__main__":
    main()
