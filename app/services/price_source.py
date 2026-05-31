"""상품 가격 조회 어댑터.

- 네이버 쇼핑 검색 API 사용 (키가 있으면)
- 키가 없으면 MockPriceSource 로 자동 대체 → 키 없이도 전체 흐름 동작/테스트 가능

어댑터 패턴: 엔진(monitor)은 PriceSource 인터페이스에만 의존하고,
실제 구현(네이버/mock)은 get_price_source() 가 결정한다.
"""
from __future__ import annotations

import logging
import random
import re
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_TAG_RE = re.compile(r"<[^>]+>")  # 네이버 결과 title 의 <b> 태그 제거용


@dataclass
class ProductResult:
    title: str
    price: int
    link: str = ""
    mall_name: str = ""


class PriceSource(Protocol):
    def search(self, query: str) -> list[ProductResult]:
        ...


class NaverShoppingSource:
    """네이버 쇼핑 검색 API 어댑터."""

    URL = "https://openapi.naver.com/v1/search/shop.json"

    def __init__(self, client_id: str, client_secret: str, timeout: float = 5.0):
        self._headers = {
            "X-Naver-Client-Id": client_id,
            "X-Naver-Client-Secret": client_secret,
        }
        self._timeout = timeout

    def search(self, query: str) -> list[ProductResult]:
        # sort=sim(관련도순)으로 '실제 그 상품'들을 받아오고,
        # 그중 최저가는 cheapest() 로 고른다.
        # (sort=asc 로 하면 10원짜리 액세서리 같은 무관한 최저가가 잡힌다.)
        params = {"query": query, "display": 20, "sort": "sim"}
        try:
            resp = httpx.get(
                self.URL, headers=self._headers, params=params, timeout=self._timeout
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            # 외부 API 실패가 엔진 전체를 멈추면 안 된다 → 로깅 후 빈 결과
            logger.warning("네이버 API 호출 실패 (query=%s): %s", query, exc)
            return []

        items = resp.json().get("items", [])
        results: list[ProductResult] = []
        for it in items:
            try:
                results.append(
                    ProductResult(
                        title=_TAG_RE.sub("", it.get("title", "")),
                        price=int(it["lprice"]),
                        link=it.get("link", ""),
                        mall_name=it.get("mallName", ""),
                    )
                )
            except (KeyError, ValueError):
                continue
        return results


class MockPriceSource:
    """키가 없을 때 쓰는 가짜 가격 소스.

    검색어마다 일정한 기준가를 두고 ±15% 범위로 흔들어 준다.
    (목표가를 넉넉히 잡으면 알림이 터지는 걸 바로 확인할 수 있다.)
    """

    def search(self, query: str) -> list[ProductResult]:
        base = 10_000 + (abs(hash(query)) % 90_000)  # 1만~10만 사이 기준가
        jitter = random.uniform(-0.15, 0.15)
        price = int(base * (1 + jitter))
        return [
            ProductResult(
                title=f"[MOCK] {query}",
                price=price,
                link="https://example.com/mock",
                mall_name="목업스토어",
            )
        ]


def get_price_source() -> PriceSource:
    """설정에 따라 실제/목업 소스를 선택해 반환."""
    if settings.naver_enabled:
        return NaverShoppingSource(
            settings.naver_client_id, settings.naver_client_secret
        )
    return MockPriceSource()


def cheapest(results: list[ProductResult]) -> ProductResult | None:
    return min(results, default=None, key=lambda r: r.price)
