"""가격 소스 어댑터 + 유틸 순수 유닛 테스트."""
from datetime import datetime, timezone

from app.services.price_source import MockPriceSource, ProductResult, cheapest
from app.utils import utcnow


def test_mock_source_returns_one_result():
    results = MockPriceSource().search("에어팟")
    assert len(results) == 1
    r = results[0]
    assert r.title.startswith("[MOCK]")
    assert "에어팟" in r.title
    assert r.price > 0
    assert r.mall_name


def test_cheapest_picks_minimum():
    products = [
        ProductResult(title="a", price=100),
        ProductResult(title="b", price=50),
        ProductResult(title="c", price=80),
    ]
    assert cheapest(products).price == 50


def test_cheapest_empty_is_none():
    assert cheapest([]) is None


def test_product_result_defaults():
    p = ProductResult(title="x", price=1000)
    assert p.link == ""
    assert p.mall_name == ""


def test_utcnow_is_naive_utc():
    now = utcnow()
    assert now.tzinfo is None                                   # naive
    # 실제 UTC 와 몇 초 이내
    delta = abs((now - datetime.now(timezone.utc).replace(tzinfo=None)).total_seconds())
    assert delta < 5


# ---------------- 네이버 어댑터 (httpx 를 가짜로 바꿔 네트워크 없이 검증) ----------------
import httpx  # noqa: E402

from app.services.price_source import NaverShoppingSource  # noqa: E402


class _FakeResp:
    def __init__(self, data, status=200):
        self._data = data
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("err", request=None, response=None)

    def json(self):
        return self._data


def test_naver_parses_items_and_strips_tags(monkeypatch):
    data = {"items": [
        {"title": "<b>에어팟</b> 프로", "lprice": "250000", "link": "http://a", "mallName": "몰A"},
        {"title": "가격없음", "link": "http://b"},                      # lprice 없음 → 건너뜀
        {"title": "이상한가격", "lprice": "abc"},                        # 숫자 아님 → 건너뜀
    ]}
    monkeypatch.setattr(httpx, "get", lambda *a, **kw: _FakeResp(data))
    results = NaverShoppingSource("id", "secret").search("에어팟")
    assert results == [ProductResult(title="에어팟 프로", price=250000, link="http://a", mall_name="몰A")]


def test_naver_http_error_returns_empty(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda *a, **kw: _FakeResp({}, status=500))
    assert NaverShoppingSource("id", "secret").search("에어팟") == []
