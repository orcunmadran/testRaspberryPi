"""Flask sunucusu: pano sayfasını ve /api/data uç noktasını sunar."""
from __future__ import annotations

import logging
import os
import threading
import time
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
    """Kaynak başına TTL önbellek. Çekme başarısız olursa eski veri korunur."""

    def __init__(self, sources=None, ttl=None, clock=time.monotonic):
        self.sources = sources or SOURCES
        self.ttl = ttl or config.TTL
        self.clock = clock
        self._lock = threading.Lock()
        self._store: dict[str, dict] = {}

    def get(self, name: str) -> dict:
        with self._lock:
            entry = self._store.get(name)
            now = self.clock()
            if entry and now - entry["at"] < self.ttl[name]:
                return entry
            try:
                data = self.sources[name]()
                entry = {"data": data, "at": now, "stale": False}
            except Exception as exc:  # ağ/ayrıştırma hatası: eski veriyle devam et
                log.warning("%s alınamadı: %s", name, exc)
                if entry:
                    entry = {**entry, "stale": True, "at": now - self.ttl[name] + 30}
                else:
                    entry = {"data": None, "at": now - self.ttl[name] + 30, "stale": True}
            self._store[name] = entry
            return entry

    def snapshot(self) -> dict:
        return {name: {"data": (e := self.get(name))["data"], "stale": e["stale"]}
                for name in self.sources}


def create_app(cache: Cache | None = None) -> Flask:
    static = Path(__file__).parent / "static"
    app = Flask(__name__, static_folder=str(static), static_url_path="/static")
    cache = cache or Cache()

    @app.get("/")
    def index():
        return send_from_directory(static, "index.html")

    @app.get("/api/data")
    def data():
        resp = jsonify({"generated": time.time(), "sections": cache.snapshot()})
        resp.headers["Cache-Control"] = "no-store"
        return resp

    return app


def main():
    logging.basicConfig(level=logging.INFO)
    port = int(os.environ.get("PORT", "8080"))
    create_app().run(host="0.0.0.0", port=port, threaded=True)


if __name__ == "__main__":
    main()
