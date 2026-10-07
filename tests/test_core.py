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
