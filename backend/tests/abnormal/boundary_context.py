"""외부 경계 수단이 쓰는 실행 맥락.

요청 경계(`ApiContext`)가 HTTP 요청으로 조작을 가한다면, 여기서는 **제품이 바깥과 맞닿는
자리**를 직접 흔든다 — 대상 사이트, 브라우저, 언어모델, 파일 쓰기.

세 가지 원칙을 지킨다.

1. **제품에 실패 주입 스위치를 넣지 않는다** (헌법 원칙 II). 대상 사이트가 느린 것은 고정
   앱이 실제로 느리게 굴어서고, 브라우저가 사라지는 것은 바깥에서 실제로 닫아서다
2. **경계 하나만 흔든다.** `create_client` 는 늦은 임포트라, `_sdk_driver` 는 모듈 전역이라
   각각 하나를 바꿔치면 제품 코드를 고치지 않고 실패를 재현할 수 있다 (research R4)
3. **쓰기 중단은 진짜 쓰기 경로를 지난다.** `Path.write_text` 를 반만 쓰고 끊게 만들면
   원자적 쓰기를 지나는 경로와 곧바로 덮어쓰는 경로가 서로 다른 결과를 낸다 — 그 차이가
   AS-049·AS-050 이 재려는 것이다
"""

from __future__ import annotations

import contextlib
import pathlib
from collections.abc import AsyncIterator, Callable, Iterator
from dataclasses import dataclass
from typing import Any

from tests.abnormal.context import ApiContext

# 고정 앱의 이상 경로 (fixtures/sample-app/serve.py). 제품이 아니라 대상 사이트다.
SLOW_PATH = "/slow?ms=1500"
HANG_PATH = "/hang"
BOOM_PATH = "/boom?status=503"
NOISY_PATH = "/noisy.html"
NAMELESS_PATH = "/nameless.html"


@dataclass(frozen=True)
class StepOutcome:
    """Step 하나를 실행한 결과.

    `code` 는 **제품이 붙인 분류**다. 러너가 `step_failed` 를 내보낼 때 쓰는 것과 같은
    값이며, 수단은 그것을 옮기기만 한다.
    """

    ok: bool
    reason: str
    code: Any


class _FakeBlock:
    """모델이 낸 텍스트 블록 하나. 에이전트는 `.text` 만 읽는다."""

    def __init__(self, text: str) -> None:
        self.text = text


class _FakeMessage:
    """모델 응답 하나. 에이전트는 `.stop_reason` 과 `.content` 만 읽는다."""

    def __init__(self, text: str = "", stop_reason: str | None = "end_turn") -> None:
        self.stop_reason = stop_reason
        self.content = [_FakeBlock(text)] if text else []


@dataclass
class BoundaryContext(ApiContext):
    """`ApiContext` 에 외부 경계를 흔드는 도구를 더한다."""

    # ─── 대상 사이트 ────────────────────────────────────────────────────────

    def target(self, path: str) -> str:
        """고정 앱의 한 경로. 제품이 보기에는 그냥 바깥 사이트다."""
        return f"{self.fixture_app}{path}"

    def session_at(self, path: str) -> tuple[int, str | None, str]:
        """그 주소로 세션을 시작한다. `(상태 코드, 세션 식별자, 본문)`."""
        resp = self.client.post(
            "/api/sessions", json={"mode": "record", "start_url": self.target(path)}
        )
        session_id = resp.json().get("session_id") if resp.status_code < 400 else None
        return resp.status_code, session_id, resp.text

    # ─── 브라우저 ───────────────────────────────────────────────────────────

    def call(self, fn: Callable[[], Any]) -> Any:
        """제품의 이벤트 루프에서 코루틴 하나를 돌린다.

        `TestClient` 는 앱을 자기 포털의 루프에서 돌린다. 세션이 쥔 Playwright 객체는 그
        루프에 묶여 있으므로 바깥에서 만든 루프로는 만질 수 없다.
        """
        return self.client.portal.call(fn)  # type: ignore[attr-defined]

    def session_obj(self, session_id: str) -> Any:
        return self.client.app.state.itb.sessions.require(session_id)  # type: ignore[attr-defined]

    def close_tab_outside(self, session_id: str, tab_index: int = 0) -> None:
        """탭 하나를 **바깥에서** 닫는다. 제품에게 알리지 않는다."""

        async def close_it() -> None:
            session = self.session_obj(session_id)
            handle = session.find_tab(tab_index)
            if handle is not None:
                with contextlib.suppress(Exception):
                    await handle.page.close()

        with contextlib.suppress(Exception):
            self.call(close_it)

    def run_step(self, session_id: str, step: dict[str, Any]) -> StepOutcome:
        """Step 하나를 세션에 대고 실제로 실행한다.

        요청 경계를 지나지 않는다 — 실행기가 브라우저와 맞닿는 자리를 직접 재는 것이
        이 면의 목적이다.

        실패하면 **제품이 붙인 분류**(`StepFailure.code`)를 함께 돌려준다. 수단이 분류를
        정하지 않는다 — 정하면 판정이 자기 자신을 재는 것이 된다.
        """
        from pydantic import TypeAdapter

        from itb.domain.error import ErrorCode
        from itb.domain.step import Step
        from itb.execution.step_executor import StepExecutor, StepFailure

        parsed = TypeAdapter(Step).validate_python(step)

        async def go() -> StepOutcome:
            session = self.session_obj(session_id)
            executor = StepExecutor(session, _PassthroughResolver())  # type: ignore[arg-type]
            try:
                await executor.execute(parsed)
            except StepFailure as exc:
                return StepOutcome(False, str(exc), exc.code)
            except Exception as exc:  # noqa: BLE001 - 무엇이 나오든 사유로 옮긴다
                # 실행기가 잡지 못한 예외다. 제품이 처리하지 못했다는 뜻이므로 그렇게 센다.
                return StepOutcome(
                    False, f"{type(exc).__name__}: {exc}", ErrorCode.INTERNAL_ERROR
                )
            return StepOutcome(True, "", None)

        return self.call(go)  # type: ignore[no-any-return]

    def goto(self, session_id: str, path: str, timeout_ms: int = 3000) -> StepOutcome:
        """세션의 활성 탭을 그 주소로 옮긴다. 제품의 실행기를 지난다."""
        return self.run_step(
            session_id,
            {
                "type": "navigate",
                "id": "step-99",
                "label": "이동",
                "url": self.target(path),
                "timeout_ms": timeout_ms,
            },
        )

    def session_readable(self, session_id: str) -> bool:
        return self.client.get(f"/api/sessions/{session_id}").status_code == 200

    # ─── 언어모델 ───────────────────────────────────────────────────────────

    @contextlib.contextmanager
    def ai_driver(self, drive: Callable[..., AsyncIterator[Any]]) -> Iterator[None]:
        """도구 루프를 도는 것을 대역으로 바꾼다.

        `AuthoringAgent._drive` 가 모듈 전역 `_sdk_driver` 를 읽으므로 그 이름 하나만
        바꾸면 된다. 제품 코드에 분기를 넣지 않는다.
        """
        self.monkeypatch.setattr("itb.authoring.agent._sdk_driver", drive)
        try:
            yield
        finally:
            self.monkeypatch.undo()

    @contextlib.contextmanager
    def ai_returning_garbage(self) -> Iterator[None]:
        """모델이 JSON 이 아닌 본문을 돌려준다 — SDK 가 해석 단계에서 터진다 (AS-013)."""

        def drive(_tools: Any, _messages: Any, _config: Any) -> AsyncIterator[Any]:
            async def gen() -> AsyncIterator[Any]:
                msg = "Expecting value: line 1 column 1 (char 0)"
                raise ValueError(msg)
                yield  # pragma: no cover - 도달하지 않는다

            return gen()

        with self.ai_driver(drive):
            yield

    @contextlib.contextmanager
    def ai_asking_for_unknown_step(self, session_id: str) -> Iterator[None]:
        """모델이 존재하지 않는 Step 종류를 지시한다 (AS-014).

        SDK 는 도구가 낸 오류를 모델에게 돌려준다. 대역도 같게 굴어야 한다 — 도구를
        직접 부르고, 그 결과를 받은 뒤 아무것도 만들지 못한 채 끝낸다.

        도구 목록이 아니라 **도구함**을 부른다. SDK 의 도구 포장 방식에 기대면 SDK 가
        바뀔 때 이 대역이 조용히 아무것도 하지 않게 된다.
        """
        toolbox = self.toolbox_of(session_id)

        def drive(_tools: Any, _messages: Any, _config: Any) -> AsyncIterator[Any]:
            async def gen() -> AsyncIterator[Any]:
                result: Any = "도구함이 없어 부르지 못했습니다"
                if toolbox is not None:
                    result = await toolbox.assert_condition(kind="존재하지-않는-종류")
                yield _FakeMessage(f"검증을 걸어 보았습니다: {result}")

            return gen()

        with self.ai_driver(drive):
            yield

    def toolbox_of(self, session_id: str) -> Any:
        """그 세션의 도구함. 없으면 ``None``."""
        from itb.api.routes.sessions import _WORK

        work = _WORK.get(session_id)
        return None if work is None else work.toolbox

    @contextlib.contextmanager
    def ai_transport_failing(self) -> Iterator[None]:
        """연결 단계에서 실패한다 — 요청이 나가지도 못한 경우다 (AS-042)."""

        def drive(_tools: Any, _messages: Any, _config: Any) -> AsyncIterator[Any]:
            async def gen() -> AsyncIterator[Any]:
                msg = "[Errno 61] Connection refused"
                raise ConnectionError(msg)
                yield  # pragma: no cover - 도달하지 않는다

            return gen()

        with self.ai_driver(drive):
            yield

    # ─── 파일 쓰기 ──────────────────────────────────────────────────────────

    @contextlib.contextmanager
    def writes_interrupted(self, *, contains: str) -> Iterator[list[str]]:
        """이름에 그 조각이 든 파일을 쓰는 도중 쓰기가 끊긴다 (AS-049·AS-050).

        **반만 쓰고 끊는다.** 곧바로 덮어쓰는 경로는 원본 자리에 반쪽 파일을 남기고,
        원자적 쓰기를 지나는 경로는 임시 파일만 반쪽으로 남긴 채 원본을 지킨다. 그
        차이가 이 시나리오의 판정 대상이다.

        확장자가 아니라 **이름 조각**으로 고른다. 원자적 쓰기의 임시 파일은
        `.TC-001.yaml.itbtmp` 처럼 확장자가 달라지므로, 확장자로 고르면 원자적 경로를
        지나는 쓰기를 하나도 끊지 못하고 검증이 통과한 것처럼 보인다.

        `write_text` 와 `open` 을 **둘 다** 잡는다. 어느 쪽으로 쓰든 끊겨야 한다.
        """
        original_write_text = pathlib.Path.write_text
        original_open = pathlib.Path.open
        hits: list[str] = []

        def targeted(p: pathlib.Path) -> bool:
            return contains in p.name

        def half_then_die(
            self_path: pathlib.Path, data: str, *args: Any, **kwargs: Any
        ) -> int:
            if not targeted(self_path):
                return original_write_text(self_path, data, *args, **kwargs)  # type: ignore[arg-type]
            hits.append(self_path.name)
            original_write_text(self_path, data[: len(data) // 2], *args, **kwargs)  # type: ignore[arg-type]
            raise OSError(_interrupted(self_path))

        def opener(
            self_path: pathlib.Path, mode: str = "r", *args: Any, **kwargs: Any
        ) -> Any:
            handle = original_open(self_path, mode, *args, **kwargs)
            if not targeted(self_path) or not any(m in mode for m in ("w", "a", "x", "+")):
                return handle
            return _HalfWriter(handle, self_path, hits)

        self.monkeypatch.setattr(pathlib.Path, "write_text", half_then_die)
        self.monkeypatch.setattr(pathlib.Path, "open", opener)
        try:
            yield hits
        finally:
            self.monkeypatch.undo()

        # **한 번도 걸리지 않았으면 실패다.** 쓰기 경로가 바뀌어 대역이 비켜 가면
        # 시나리오는 아무것도 재지 않은 채 통과한다 — RG-106 이 막으려는 상태다.
        assert hits, (
            f"이름에 {contains!r} 이 든 파일 쓰기를 한 번도 끊지 못했습니다. "
            "쓰기 경로가 바뀌었는지 확인하세요 — 끊지 못하면 AS-049·AS-050 은 "
            "아무것도 재지 않고 통과합니다."
        )

    def definition_readable(self, test_id: str) -> bool:
        """정의가 여전히 읽히고 Step 이 남아 있는가."""
        resp = self.client.get(f"/api/tests/{test_id}")
        return resp.status_code == 200 and bool(resp.json().get("steps"))

    def secret_names(self) -> list[str] | None:
        resp = self.client.get("/api/secrets")
        if resp.status_code != 200:
            return None
        return [n["name"] for n in resp.json().get("names", [])]


def _interrupted(path: pathlib.Path) -> str:
    return f"검증용 대역: {path.name} 을 쓰는 도중 끊겼습니다"


class _HalfWriter:
    """반만 쓰고 끊기는 파일 손잡이.

    감싼 손잡이에 나머지를 그대로 넘긴다 (`flush`·`fileno`·`close`). 원자적 쓰기가
    `fsync` 를 부르므로 `fileno` 가 없으면 이 대역 때문에 다른 이유로 실패한다 —
    그러면 무엇을 재고 있는지 알 수 없게 된다.
    """

    def __init__(self, handle: Any, path: pathlib.Path, hits: list[str]) -> None:
        self._handle = handle
        self._path = path
        self._hits = hits

    def write(self, data: Any) -> int:
        self._hits.append(self._path.name)
        half = data[: len(data) // 2]
        if half:
            self._handle.write(half)
        self._handle.flush()
        raise OSError(_interrupted(self._path))

    def __getattr__(self, name: str) -> Any:
        return getattr(self._handle, name)

    def __enter__(self) -> _HalfWriter:
        return self

    def __exit__(self, *exc: Any) -> None:
        self._handle.close()


class _PassthroughResolver:
    """변수 치환을 하지 않는 해석기.

    외부 경계 시나리오는 변수를 쓰지 않는다. 진짜 해석기를 만들려면 프로젝트 정의와 키가
    필요한데, 그것은 이 면이 재려는 것과 무관하다.
    """

    def substitute(self, value: str) -> str:
        return value

    def declare(self, *_args: Any, **_kwargs: Any) -> None:
        return None
