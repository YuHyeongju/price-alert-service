"""AI 상품 필터 관련 테스트 (OpenAI 키 없이 검증 가능한 부분)."""
from app.services.ai import _parse_indices, select_relevant_products
from app.services.price_source import ProductResult


def test_parse_indices_basic():
    assert _parse_indices("[0, 2, 5]", 10) == [0, 2, 5]


def test_parse_indices_embedded_in_text():
    assert _parse_indices("고른 결과: [1, 3] 입니다.", 5) == [1, 3]


def test_parse_indices_clamps_and_dedups():
    # 범위를 벗어난 99, -1 은 제거하고 중복 2 도 한 번만
    assert _parse_indices("[0, 99, -1, 2, 2]", 3) == [0, 2]


def test_parse_indices_empty_or_garbage():
    assert _parse_indices("[]", 5) == []
    assert _parse_indices("해당 없음", 5) == []


def test_select_relevant_returns_all_without_key():
    # 테스트 환경엔 OpenAI 키가 없으므로 원본을 그대로 돌려줘야 한다(동작 보장)
    products = [
        ProductResult("에어팟 프로 2세대", 300000),
        ProductResult("에어팟 프로 케이스", 5000),
    ]
    assert select_relevant_products("에어팟 프로 2세대", products) == products
