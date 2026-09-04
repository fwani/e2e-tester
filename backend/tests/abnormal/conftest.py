"""이상 경로 검증의 픽스처.

`product_ui` 는 **제품 서버와 제품 화면을 실제로 띄운다** (RG-105). 세션 범위라 한 번만
띄우고 화면 면 시나리오 18건이 나눠 쓴다.
"""

from __future__ import annotations

from tests.abnormal.product_ui import ProductUI, product_ui  # noqa: F401

__all__ = ["ProductUI", "product_ui"]
