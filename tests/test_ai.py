"""AI 서비스(폴백 동작 + 인덱스 파싱) 테스트.

테스트 환경은 OPENAI_API_KEY 가 비어 있어 openai 가 비활성 → 전부 안전한 폴백 경로를 탄다.
"""
from app.services.ai import (
    _template_comment,
    generate_comment,
    _parse_indices,
    select_relevant_products,
)
from app.services.price_source import ProductResult


def test_template_comment_contains_query_and_prices():
    msg = _template_comment("에어팟", 250_000, 270_000)
    assert "에어팟" in msg
    assert "250,000" in msg      # 천단위 콤마
    assert "270,000" in msg
    assert "🛒" in msg


def test_generate_comment_falls_back_to_template():
    # 키가 없으므로 템플릿과 동일해야 한다
    assert generate_comment("키보드", 40_000, 50_000) == _template_comment("키보드", 40_000, 50_000)


def test_parse_indices_valid():
    assert _parse_indices("고른 항목: [0, 2, 5]", 6) == [0, 2, 5]


def test_parse_indices_filters_out_of_range_and_dupes():
    assert _parse_indices("[0, 99, 2]", 3) == [0, 2]     # 99 는 범위 밖
    assert _parse_indices("[1, 1, 2]", 5) == [1, 2]      # 중복 제거


def test_parse_indices_no_array_or_invalid():
    assert _parse_indices("배열 없음", 5) == []
    assert _parse_indices("", 5) == []


def test_select_relevant_products_passthrough_without_ai():
    products = [
        ProductResult(title="에어팟 프로", price=300000),
        ProductResult(title="에어팟 케이스", price=9000),
    ]
    # openai 비활성 → 원본 그대로 반환
    assert select_relevant_products("에어팟", products) == products
    assert select_relevant_products("에어팟", []) == []
