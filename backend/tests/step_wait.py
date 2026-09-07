"""녹화된 Step 이 도달할 때까지 기다린다.

**고정 시간 대기를 쓰지 않기 위한 장치다.** 녹화 검증은 오랫동안 "동작한 뒤 0.4~0.8초
자고 나서 읽는다" 였다. 그 대기는 두 가지를 동시에 틀리게 한다.

1. **부하가 있으면 짧다.** 프로세스 8개가 CPU 를 나눠 쓰면 recorder.js → 백엔드 →
   세션 보기까지의 왕복이 0.4초를 넘는다. 실측: 8분할에서 `steps` 가 빈 배열로 읽혀
   "비밀번호 입력이 기록되지 않았다" 로 실패했다. 제품은 그대로다.
2. **평상시에는 길다.** 대개 100ms 안에 도달하는데 나머지 300ms 를 그냥 기다린다.

그래서 시간을 재지 않고 **조건을 본다.** 조건이 서면 즉시 돌아오고, 서지 않으면
마감까지 기다린 뒤 **마지막으로 읽은 것을 그대로 돌려준다** — 판정은 호출한 검증이
자기 단언으로 한다. 여기서 실패를 만들지 않는 이유는, 그러면 실패 메시지가 이 파일의
것이 되어 무엇을 확인하려던 검증인지 사라지기 때문이다.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient

DEFAULT_TIMEOUT_S = 10.0
"""넉넉하게 잡는다. 조건이 서면 즉시 돌아오므로 이 값이 커도 평상시 비용이 아니다.

CI 러너는 개발 장비보다 느리고 프로세스를 나눠 쓰면 더 느리다. 마감을 아끼면
"확인하려던 것" 이 아니라 "그날의 부하" 를 판정하게 된다.
"""

POLL_INTERVAL_S = 0.05


def read_steps(client: TestClient, session_id: str) -> list[dict[str, Any]]:
    """세션 보기의 Step 목록. 조회 자체가 실패하면 사유와 함께 즉시 실패한다."""
    resp = client.get(f"/api/sessions/{session_id}")
    assert resp.status_code == 200, resp.text
    return list(resp.json()["steps"])


def wait_for_steps(
    client: TestClient,
    session_id: str,
    predicate: Callable[[list[dict[str, Any]]], bool],
    *,
    timeout_s: float = DEFAULT_TIMEOUT_S,
) -> list[dict[str, Any]]:
    """`predicate` 가 참이 되면 그 시점의 Step 목록을, 아니면 마감 시점의 것을 준다."""
    deadline = time.monotonic() + timeout_s
    steps = read_steps(client, session_id)
    while not predicate(steps):
        if time.monotonic() >= deadline:
            return steps
        time.sleep(POLL_INTERVAL_S)
        steps = read_steps(client, session_id)
    return steps


def has_kinds(*kinds: str) -> Callable[[list[dict[str, Any]]], bool]:
    """주어진 종류가 **모두** 기록됐는지 보는 조건."""
    wanted = set(kinds)

    def check(steps: list[dict[str, Any]]) -> bool:
        return wanted <= {s["type"] for s in steps}

    return check


def has_any(
    match: Callable[[dict[str, Any]], bool],
) -> Callable[[list[dict[str, Any]]], bool]:
    """조건에 맞는 Step 이 **하나라도** 있는지 보는 조건."""

    def check(steps: list[dict[str, Any]]) -> bool:
        return any(match(s) for s in steps)

    return check
