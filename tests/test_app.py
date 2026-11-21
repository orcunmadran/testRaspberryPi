from bilgiekrani.app import Cache, create_app


def make_cache(fail=False, now=[0.0]):
    calls = {"n": 0}

    def src():
        calls["n"] += 1
        if fail:
            raise RuntimeError("ağ yok")
        return {"v": calls["n"]}

    return Cache(sources={"a": src}, ttl={"a": 60}, clock=lambda: now[0]), calls, now


def test_cache_ttl():
    cache, calls, now = make_cache()
    cache.get("a"); cache.get("a")
    assert calls["n"] == 1
    now[0] = 61
    cache.get("a")
    assert calls["n"] == 2


def test_cache_serves_stale_on_failure():
    now = [0.0]
    state = {"fail": False}

    def src():
        if state["fail"]:
            raise RuntimeError("x")
        return "iyi"

    cache = Cache(sources={"a": src}, ttl={"a": 60}, clock=lambda: now[0])
    assert cache.get("a")["data"] == "iyi"
    state["fail"] = True
    now[0] = 100
    e = cache.get("a")
    assert e["data"] == "iyi" and e["stale"] is True


def test_cache_failure_without_data():
    cache, _, _ = make_cache(fail=True)
    e = cache.get("a")
    assert e["data"] is None and e["stale"] is True


def test_api_and_index():
    cache = Cache(sources={"a": lambda: [1, 2]}, ttl={"a": 60})
    c = create_app(cache).test_client()
    j = c.get("/api/data").get_json()
    assert j["sections"]["a"] == {"data": [1, 2], "stale": False}
    r = c.get("/")
    assert r.status_code == 200 and "Bilgi Ekranı" in r.get_data(as_text=True)


def test_online_flag_and_health():
    def boom():
        raise RuntimeError("internet yok")

    c = create_app(Cache(sources={"a": boom, "b": boom}, ttl={"a": 60, "b": 60})).test_client()
    j = c.get("/api/data").get_json()
    assert j["online"] is False
    assert j["sections"]["a"] == {"data": None, "stale": True}
    assert c.get("/api/health").get_json() == {"ok": True}   # sunucu internetsiz de ayakta


def test_online_when_any_source_ok():
    def boom():
        raise RuntimeError("x")

    cache = Cache(sources={"ok": lambda: 1, "bad": boom}, ttl={"ok": 60, "bad": 60})
    sections, online = cache.snapshot()
    assert online is True and sections["bad"]["stale"] is True


def test_failed_source_retries_after_30s():
    now = [0.0]
    state = {"fail": True, "calls": 0}

    def src():
        state["calls"] += 1
        if state["fail"]:
            raise RuntimeError("x")
        return "geldi"

    cache = Cache(sources={"a": src}, ttl={"a": 600}, clock=lambda: now[0])
    assert cache.get("a")["data"] is None
    now[0] = 10; cache.get("a")                      # 30 sn dolmadı: yeniden denemez
    assert state["calls"] == 1
    state["fail"] = False
    now[0] = 31                                      # WiFi geldi
    e = cache.get("a")
    assert e["data"] == "geldi" and e["stale"] is False
