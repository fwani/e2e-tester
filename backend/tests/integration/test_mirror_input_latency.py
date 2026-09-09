"""조작 → 화면 반영 지연 (010 T086 · SC-514 · FR-334·FR-335 · research R8).

**재는 것은 하나다** — 미러에서 조작한 결과가 화면에 나타나기까지의 시간이, 사용자가 같은
곳을 다시 누르지 않을 만큼 짧은가.

## 기준선

research R8 이 로컬 헤드리스에서 실측한 값이다.

```
클릭 → 프레임 도착: 15.4 24.2 25.2 25.9 27.3 24.9 21.1 42.9 31.6 17.1 25.2 29.7 (ms)
성공 12/12, 중앙값 약 25ms, 최대 42.9ms
```

**이 값에서 멀어졌으면 ack 흐름을 먼저 의심한다.** 같은 실측에서 ack 를 보내지 않으면
5회 중 2회만 프레임이 왔다 — CDP 는 ack 가 없으면 3프레임 뒤 밀기를 멈춘다. 그 상태는
사용자에게 「조작해도 화면이 안 바뀐다」로 보이고, 원인은 지연이 아니라 정지다.

## 왜 상한을 넉넉히 두는가

이 검증의 목적은 **회귀를 잡는 것**이지 기준선을 재현하는 것이 아니다. 실측 최대값의
여러 배를 상한으로 두면 「조금 느려진 것」은 통과하고 「구조가 깨진 것」만 걸린다 —
ack 가 멈추거나, 조작이 프레임 전달을 막거나(FR-336), 무프레임 보충이 사라진 경우다.

`timing` 마커가 붙어 있어 **순차로만 돈다.** 병렬로 돌면 재는 값이 제품의 성질이 아니라
그 순간의 부하가 된다 (`tests/tiers.py`).
"""

from __future__ import annotations

import json
import queue
import statistics
import threading
import time
from typing import Any

import pytest
from fastapi.testclient import TestClient
from us2_support import stop_quietly

CONTROL_PATH = "/api/sessions/{sid}/control"
EVENTS_PATH = "/api/sessions/{sid}/events"

ROUNDS = 12
"""research R8 과 같은 횟수. 중앙값을 낼 만큼이고 실시간을 많이 쓰지 않는다."""

BASELINE_MEDIAN_MS = 25.0
"""research R8 의 중앙값. **단언이 아니라 기준이다** — 보고에만 쓴다."""

MEDIAN_LIMIT_MS = 400.0
"""중앙값 상한. 기준선의 16배다.

**넉넉한 것이 의도다.** 이 검증이 잡으려는 것은 「조금 느려짐」이 아니라 **구조가
깨짐**이다 — ack 가 멈추면 프레임이 아예 오지 않고, 그때 이 값은 상한이 아니라 시간
초과로 나타난다.
"""

FRAME_TIMEOUT_S = 3.0
"""한 회차에서 프레임을 기다리는 시간.

**넘으면 실패다.** 프레임이 오지 않는 것은 느린 것이 아니라 멈춘 것이고, 사용자에게는
「조작이 안 먹었다」로 보인다 (FR-334).
"""


class FrameProbe:
    """관찰 소켓에서 프레임 도착 시각을 읽는다.

    `TestClient` 의 WebSocket 은 `receive_json()` 이 무기한 막히므로 읽기를 별도 스레드에
    둔다 — `test_mirror_late_subscribe.py` 의 하니스와 같은 이유다.
    """

    def __init__(self) -> None:
        self.frames: queue.Queue[float] = queue.Queue()
        self.stop = threading.Event()

    def pump(self, ws: Any) -> None:
        while not self.stop.is_set():
            try:
                message = ws.receive_json()
            except Exception:  # noqa: BLE001 - 닫히면 여기로 온다
                return
            if message.get("type") == "mirror_frame":
                self.frames.put(time.monotonic())

    def drain(self) -> None:
        """쌓인 프레임을 비운다. 회차 사이의 잔여가 다음 회차로 새지 않게 한다."""
        while True:
            try:
                self.frames.get_nowait()
            except queue.Empty:
                return

    def next_after(self, sent_at: float, timeout_s: float) -> float | None:
        """`sent_at` 이후 처음 도착한 프레임까지의 밀리초. 없으면 `None`."""
        deadline = time.monotonic() + timeout_s
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None
            try:
                arrived = self.frames.get(timeout=remaining)
            except queue.Empty:
                return None
            if arrived >= sent_at:
                return (arrived - sent_at) * 1000.0


@pytest.mark.browser
@pytest.mark.timing
def test_a_mirror_click_shows_up_on_screen_quickly(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """조작한 결과가 곧 화면에 나타난다 (SC-514 · FR-334 · research R8).

    **화면을 실제로 바꾸는 조작을 쓴다.** 바꾸지 않는 조작은 프레임을 만들지 않고, 그때는
    무프레임 보충이 채운다 (FR-335) — 그것은 아래 검증이 따로 잰다.
    """
    created = keyed_client.post(
        "/api/sessions",
        json={"mode": "record", "start_url": f"{fixture_app}/interactions.html"},
    )
    assert created.status_code == 201, created.text
    session_id = str(created.json()["session_id"])

    try:
        page = keyed_client.app.state.itb.sessions.require(session_id).tabs[0].page

        async def inject(p: Any = page) -> None:
            # 클릭할 때마다 확실히 화면이 바뀌는 요소. 픽스처의 성질에 기대지 않는다.
            await p.evaluate(
                "const b=document.createElement('button');b.id='blink';"
                "b.style.cssText='position:fixed;left:20px;top:20px;width:200px;height:80px';"
                "b.onclick=()=>{b.style.background=b.style.background==='red'?'blue':'red';};"
                "document.body.append(b);"
            )

        keyed_client.portal.call(inject)  # type: ignore[attr-defined]

        async def center(p: Any = page) -> dict[str, float]:
            box = await p.locator("#blink").bounding_box()
            assert box is not None
            return box

        box = keyed_client.portal.call(center)  # type: ignore[attr-defined]
        x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2

        probe = FrameProbe()
        with keyed_client.websocket_connect(EVENTS_PATH.format(sid=session_id)) as events:
            reader = threading.Thread(
                target=probe.pump, args=(events,), name="latency-probe", daemon=True
            )
            reader.start()
            try:
                with keyed_client.websocket_connect(
                    CONTROL_PATH.format(sid=session_id)
                ) as control:
                    control.receive_json()  # control_state open

                    samples: list[float] = []
                    misses = 0
                    for _ in range(ROUNDS):
                        probe.drain()
                        sent = time.monotonic()
                        for event in (
                            {"kind": "pointer.down", "tab": 0, "x": x, "y": y, "button": "left"},
                            {"kind": "pointer.up", "tab": 0, "x": x, "y": y, "button": "left"},
                        ):
                            control.send_text(json.dumps(event))
                        elapsed = probe.next_after(sent, FRAME_TIMEOUT_S)
                        if elapsed is None:
                            misses += 1
                        else:
                            samples.append(elapsed)
            finally:
                probe.stop.set()
                events.close()
                reader.join(timeout=5.0)
    finally:
        stop_quietly(keyed_client, session_id)

    assert misses == 0, (
        f"{ROUNDS}회 중 {misses}회에서 프레임이 오지 않았다. **먼저 ack 흐름을 의심하라** — "
        "ack 가 멈추면 CDP 는 3프레임 뒤 밀기를 정지하고, 그 상태는 사용자에게 "
        "「조작해도 화면이 안 바뀐다」로 보인다 (research R8)."
    )
    median = statistics.median(samples)
    print(  # noqa: T201 - 실측값을 남긴다. 기준선과 비교할 때 이 줄이 근거다
        f"[T086] 조작 → 화면 반영: 중앙값 {median:.1f}ms · 최대 {max(samples):.1f}ms · "
        f"{len(samples)}/{ROUNDS} 성공 (기준선 중앙값 {BASELINE_MEDIAN_MS:.0f}ms)"
    )
    assert median <= MEDIAN_LIMIT_MS, (
        f"조작 → 화면 반영 중앙값이 {median:.1f}ms 다 (상한 {MEDIAN_LIMIT_MS:.0f}ms · "
        f"기준선 {BASELINE_MEDIAN_MS:.0f}ms). 이만큼 멀어졌으면 지연이 아니라 구조가 "
        f"바뀐 것이다 — ack 흐름과 조작·프레임의 상호 간섭(FR-336)을 확인하라. "
        f"표본: {[round(s, 1) for s in samples]}"
    )


@pytest.mark.browser
@pytest.mark.timing
def test_a_silent_screen_is_refreshed_while_controlling(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """**화면을 바꾸지 않는 조작 뒤에도 현재 화면이 확인된다** (FR-335 · research R8).

    초점 이동이나 값이 같은 입력은 프레임을 만들지 않는다. 기존 2초 감시가 그것을 덮지만
    2초는 조작 피드백으로 길다 — 사용자는 그 2초를 「내 클릭이 안 먹었다」로 읽고 같은
    곳을 다시 누른다.

    조작 국면에서 주기가 줄었는지를 **실제 브라우저에서** 확인한다. 단위 검증은 주기를
    고른 것까지만 볼 수 있고, 그 주기로 실제 프레임이 오는지는 볼 수 없다.
    """
    from itb.mirror.screencast import CONTROL_IDLE_INTERVAL_S, IDLE_INTERVAL_S

    created = keyed_client.post(
        "/api/sessions",
        json={"mode": "record", "start_url": f"{fixture_app}/interactions.html"},
    )
    assert created.status_code == 201, created.text
    session_id = str(created.json()["session_id"])

    try:
        probe = FrameProbe()
        with keyed_client.websocket_connect(EVENTS_PATH.format(sid=session_id)) as events:
            reader = threading.Thread(
                target=probe.pump, args=(events,), name="idle-probe", daemon=True
            )
            reader.start()
            try:
                # 아무것도 조작하지 않는다. 화면은 완전히 조용하다.
                probe.drain()
                started = time.monotonic()
                first = probe.next_after(started, IDLE_INTERVAL_S)
            finally:
                probe.stop.set()
                events.close()
                reader.join(timeout=5.0)
    finally:
        stop_quietly(keyed_client, session_id)

    assert first is not None, (
        "조작 국면의 조용한 화면에서 프레임이 보충되지 않았다 (FR-335). "
        "무프레임 감시가 조작 국면 주기를 쓰고 있는지 확인하라."
    )
    # 관찰 국면 주기(2초)보다 확실히 빠르게 왔다는 것이 요점이다.
    assert first <= IDLE_INTERVAL_S * 1000, (
        f"보충 프레임이 {first:.0f}ms 만에 왔다 — 조작 국면 주기"
        f"({CONTROL_IDLE_INTERVAL_S * 1000:.0f}ms)가 적용되지 않은 것으로 보인다"
    )
