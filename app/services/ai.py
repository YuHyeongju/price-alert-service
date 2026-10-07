"""AI 기능 (OpenAI).

두 곳에 AI를 쓴다 — 둘 다 키가 없거나 실패하면 안전하게 폴백한다.
  1) generate_comment        : 알림 한 줄 문구 생성   (폴백: 템플릿 문장)
  2) select_relevant_products: 검색 결과 중 '실제 본품'만 골라 정확도↑ (폴백: 원본 그대로)
"""
from __future__ import annotations

import json
import logging
import re

from app.config import settings
from app.services.price_source import ProductResult

logger = logging.getLogger(__name__)


def _openai_client():
    from openai import OpenAI

    # base_url 을 지정하면 OpenAI 호환 제공자(Groq/Gemini/Ollama 등)로 교체할 수 있다.
    return OpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url or None,
    )


# ---------------------------------------------------------------------------
# 1) 알림 문구 생성
# ---------------------------------------------------------------------------
def _template_comment(query: str, current_price: int, target_price: int) -> str:
    return (
        f"'{query}' 최저가가 {current_price:,}원이에요. "
        f"목표가 {target_price:,}원에 도달했어요! 지금이 살 타이밍일 수 있어요. 🛒"
    )


def generate_comment(query: str, current_price: int, target_price: int) -> str:
    """알림 한 줄 문구. 키가 없거나 실패하면 템플릿 문구로 대체."""
    if not settings.openai_enabled:
        return _template_comment(query, current_price, target_price)
    try:
        prompt = (
            f"상품 '{query}'의 최저가가 {current_price:,}원으로 "
            f"사용자의 목표가 {target_price:,}원에 도달했습니다. "
            "구매를 권하는 친근한 한국어 알림 문구를 한 문장으로 작성해줘. "
            "이모지 1개 포함, 40자 이내."
        )
        resp = _openai_client().chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,  # thinking 모델(gemini 등)이 사고에 토큰을 써도 답이 남도록 여유
            temperature=0.7,
        )
        text = (resp.choices[0].message.content or "").strip()
        return text or _template_comment(query, current_price, target_price)
    except Exception as exc:  # 외부 호출 실패가 알림 자체를 막으면 안 된다
        logger.warning("OpenAI 코멘트 생성 실패: %s", exc)
        return _template_comment(query, current_price, target_price)


# ---------------------------------------------------------------------------
# 2) 상품 정확도 필터
# ---------------------------------------------------------------------------
def _parse_indices(text: str, count: int) -> list[int]:
    """LLM 응답에서 JSON 정수 배열을 뽑아 [0, count) 범위로 정리(중복 제거)."""
    match = re.search(r"\[[-\d,\s]*\]", text or "")
    if not match:
        return []
    try:
        raw = json.loads(match.group())
    except json.JSONDecodeError:
        return []
    result: list[int] = []
    for x in raw:
        if isinstance(x, int) and 0 <= x < count and x not in result:
            result.append(x)
    return result


def select_relevant_products(
    query: str, products: list[ProductResult]
) -> list[ProductResult]:
    """검색 결과 중 'query에 해당하는 실제 본품'만 추려 반환한다.

    케이스/액세서리 같은 무관한 최저가가 잡히는 문제를 줄여 정확도를 높인다.
    키가 없거나(또는 USE_AI_FILTER=false) 실패하면 원본을 그대로 돌려준다.
    """
    if not products or not settings.openai_enabled or not settings.use_ai_filter:
        return products
    try:
        listing = "\n".join(
            f"{i}. {p.title} ({p.price:,}원)" for i, p in enumerate(products)
        )
        prompt = (
            f'사용자가 찾는 상품: "{query}"\n\n'
            "아래는 쇼핑 검색 결과(번호. 제목 (가격))야. "
            "이 중 '사용자가 실제로 사려는 정상 신품 본품'인 항목만 골라줘.\n\n"
            "[제외할 것]\n"
            "- 액세서리/부속품: 케이스, 커버, 보호필름, 충전기, 케이블, 거치대, 스트랩, 파우치\n"
            "- 한쪽/일부만 판매: '한쪽', '단품', '유닛', '왼쪽', '오른쪽', 'L', 'R', '분실대용', '한짝'\n"
            "- 비정품/상태이상: 리퍼, 리퍼비시, 중고, 벌크, 호환, 짝퉁, 모조\n"
            "- 가품 의심: 다른 정상 본품들의 가격대에 비해 비정상적으로 싼 항목(예: 절반 이하)\n\n"
            "[포함할 것]\n"
            "- 정상 신품 본품 ('충전 케이스 포함'처럼 구성품 표기가 있어도 세트 본품이면 포함)\n\n"
            "해당 항목의 번호만 JSON 배열로 답해. 예: [0, 3, 7]. 확실한 것만, 없으면 [].\n\n"
            f"{listing}"
        )
        resp = _openai_client().chat.completions.create(
            model=settings.openai_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,  # thinking 모델 여유분 (실제 답인 번호 배열은 짧음)
            temperature=0,
        )
        indices = _parse_indices(resp.choices[0].message.content or "", len(products))
        selected = [products[i] for i in indices]
        if selected:
            logger.info("AI 상품 필터: %d개 중 %d개 선택", len(products), len(selected))
            return selected
        return products  # 아무것도 못 고르면 원본 폴백
    except Exception as exc:
        logger.warning("AI 상품 필터 실패: %s", exc)
        return products
