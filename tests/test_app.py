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
