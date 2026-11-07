import pytest

from korean_job_mcp.utils import cache as cache_module
from korean_job_mcp.utils.cache import TTLCache


@pytest.fixture
def clock(monkeypatch):
    """time.time() 을 고정값으로 바꾸고, now["t"] 를 바꿔 시간을 흘린다."""
    now = {"t": 1000.0}
    monkeypatch.setattr(cache_module.time, "time", lambda: now["t"])
    return now


def test_get_missing_key_returns_none():
    assert TTLCache().get("missing") is None


def test_set_then_get_returns_value(clock):
    c = TTLCache(ttl_seconds=10)
    c.set("k", {"a": 1})
    assert c.get("k") == {"a": 1}


def test_set_overwrites_value_and_resets_ttl(clock):
    c = TTLCache(ttl_seconds=10)
    c.set("k", "old")
    clock["t"] += 8
    c.set("k", "new")
    clock["t"] += 8  # 첫 set 기준이면 만료, 두 번째 set 기준이면 유효
    assert c.get("k") == "new"


def test_value_alive_exactly_at_expiry(clock):
    c = TTLCache(ttl_seconds=10)
    c.set("k", "v")
    clock["t"] += 10
    assert c.get("k") == "v"


def test_expired_value_returns_none_and_is_removed(clock):
    c = TTLCache(ttl_seconds=10)
    c.set("k", "v")
    clock["t"] += 10.001
    assert c.get("k") is None
    assert "k" not in c._store


def test_clear_removes_all(clock):
    c = TTLCache(ttl_seconds=10)
    c.set("a", 1)
    c.set("b", 2)
    c.clear()
    assert c.get("a") is None
    assert c.get("b") is None
