"""로그 스크러버. FR-089d.

복호화된 민감 값이 산출물에 남지 않게, **디스크에 쓰기 직전** 또는 **전송 직전**에
마스킹한다. 값의 여러 표현 형태를 함께 잡는다 — 대상 앱이 값을 URL 인코딩하거나
JSON 으로 직렬화해 로그·네트워크 기록에 남길 수 있다 (research R7).
"""

from __future__ import annotations

import base64
import json
import re
import urllib.parse

MASK = "***MASKED***"
MIN_LENGTH = 4
"""너무 짧은 값은 마스킹하지 않는다 — 무관한 텍스트를 대량으로 가리게 된다."""


def _variants(value: str) -> set[str]:
    """한 값이 산출물에 나타날 수 있는 형태들."""
    out = {value}
    out.add(urllib.parse.quote(value))
    out.add(urllib.parse.quote_plus(value))
    out.add(urllib.parse.quote(value, safe=""))
    # JSON 문자열로 직렬화된 형태 (따옴표 제외)
    out.add(json.dumps(value, ensure_ascii=False)[1:-1])
    out.add(json.dumps(value)[1:-1])
    try:
        out.add(base64.b64encode(value.encode("utf-8")).decode("ascii"))
    except (UnicodeError, ValueError):
        pass
    out.add(value.encode("unicode_escape").decode("ascii"))
    return {v for v in out if len(v) >= MIN_LENGTH}


class Scrubber:
    """실행 컨텍스트의 민감 값 집합을 들고 산출물을 마스킹한다.

    **불변식**: 이 객체는 값을 보관하지만 절대 노출하지 않는다. 직렬화 대상이 아니다.
    """

    __slots__ = ("_pattern", "_count")

    def __init__(self, values: object = ()) -> None:
        variants: set[str] = set()
        for v in values:  # type: ignore[union-attr]
            if isinstance(v, str) and len(v) >= MIN_LENGTH:
                variants |= _variants(v)
        self._count = len(variants)
        # 긴 것부터 치환한다 — 짧은 변형이 긴 변형의 일부를 먼저 가리면 안 된다.
        self._pattern = (
            re.compile("|".join(re.escape(v) for v in sorted(variants, key=len, reverse=True)))
            if variants
            else None
        )

    def __bool__(self) -> bool:
        return self._pattern is not None

    @property
    def variant_count(self) -> int:
        return self._count

    def scrub(self, text: str) -> str:
        """텍스트에서 민감 값의 모든 표현을 마스킹한다."""
        if self._pattern is None:
            return text
        return self._pattern.sub(MASK, text)

    def scrub_bytes(self, data: bytes) -> bytes:
        if self._pattern is None:
            return data
        return self.scrub(data.decode("utf-8", errors="replace")).encode("utf-8")

    def scrub_obj(self, obj: object) -> object:
        """중첩 구조를 재귀적으로 마스킹한다. 딕셔너리 키도 대상이다."""
        if isinstance(obj, str):
            return self.scrub(obj)
        if isinstance(obj, dict):
            return {self.scrub_obj(k): self.scrub_obj(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self.scrub_obj(v) for v in obj]
        if isinstance(obj, tuple):
            return tuple(self.scrub_obj(v) for v in obj)
        return obj
