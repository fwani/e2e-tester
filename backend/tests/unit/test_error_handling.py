"""오류 처리·진단 일관성. FR-087·헌법 §보안(명시적 오류 처리) (T152).

헌법이 요구하는 것은 두 가지다.

1. **실패한 Step 은 항상 진단 가능한 결과를 남긴다** — 사유·스크린샷·로그
2. **처리되지 않은 오류로 러너 태스크가 죽지 않는다** — 조용한 실패도, 조용한 중단도 없다

이 파일은 그 두 가지를 코드 구조와 동작 양쪽에서 본다. 구조 점검(모든 예외 경로가 사유를
남기는가)은 브라우저 없이 할 수 있고, 그래서 전수로 볼 수 있다.
"""

from __future__ import annotations

import asyncio
import inspect
import pathlib

import pytest

from itb.api.errors import ApiError, ErrorCode, bad_request, conflict, not_found
from itb.domain.run_result import LocatorAttempt, StepOutcome
from itb.execution import runner as runner_mod
from itb.execution.runner import RunnerTask
from itb.execution.state_machine import Command, SessionState
from itb.execution.step_executor import StepFailure
from tests.unit.test_runner_pacing import _FakeSession as _PacingFakeSession

EXECUTION_DIR = pathlib.Path(runner_mod.__file__).parent


class _FakeSession(_PacingFakeSession):
    """러너가 요구하는 최소 표면. 브라우저를 띄우지 않는다.

    **004 의 가짜를 그대로 물려받는다** (`tests.unit.test_runner_pacing._FakeSession`).
    이 파일은 한동안 자기 벌을 따로 갖고 있었고, 그것이 정확히 `test_pause_before_index.py`
    가 경고한 결과를 냈다 — 005 가 러너에 세션 메서드 하나를 더했을 때 이 가짜만 낡아
    러너의 종료 경로가 여기서만 터졌다. 실패는 제품이 아니라 낡은 가짜를 가리켰다.

    여기서 좁히는 것은 상태 전이뿐이다. 이 파일의 대상은 **예외 경로**이므로 일시정지를
    흉내 낼 필요가 없고, `PAUSE` 를 받아 상태를 옮기면 "러너가 죽지 않는가" 를 보는
    단정이 일시정지에 가려진다.
    """

    def __init__(self, state: SessionState = SessionState.REPLAYING) -> None:
        super().__init__(state=state)

    async def apply(self, command: Command) -> SessionState:
        if command is Command.FINISH_PASS:
            self.state = SessionState.COMPLETED
        elif command is Command.FINISH_FAIL:
            self.state = SessionState.FAILED
        return self.state


# ─── 1. 실패는 항상 진단 가능한 결과를 남긴다 ─────────────────────────────


def test_step_failure_carries_diagnostics() -> None:
    """FR-021·FR-054 — 실패 예외가 사유와 시도 내역을 함께 들고 있다.

    사유만 있으면 "왜 못 찾았는지" 를 알 수 없고, 시도 내역만 있으면 사람이 읽을 문장이
    없다. 둘 다 필요하다.
    """
    attempts = [
        LocatorAttempt(
            candidate="test_id", expression="testId=x", matched=False, waited_ms=5000
        )
    ]
    failure = StepFailure("찾을 수 없습니다", attempts=attempts, tab_wait_ms=120)
    assert str(failure)
    assert failure.attempts == attempts
    assert failure.tab_wait_ms == 120


def test_unexpected_exception_in_a_step_becomes_a_run_error_event() -> None:
    """FR-087 — 예상하지 못한 오류로 러너가 **죽지 않는다.**

    태스크가 조용히 사라지면 화면은 "실행 중" 에 머문 채 아무 일도 일어나지 않는다.
    """
    session = _FakeSession()

    async def boom(_session: object, _index: int) -> bool:
        msg = "예상하지 못한 오류"
        raise RuntimeError(msg)

    task = RunnerTask(session=session, step_runner=boom, total_steps=1)  # type: ignore[arg-type]

    async def run() -> None:
        task.start()
        await task.wait()

    asyncio.run(run())

    kinds = [k for k, _ in session.events]
    assert "run_error" in kinds, kinds
    payload = next(p for k, p in session.events if k == "run_error")

    # 003 — 진단 정보는 사용자 메시지가 아니라 `detail` 에 담긴다. 예외 원문을 사용자에게
    # 그대로 보내면 내부 경로가 새어 나갈 수 있다 (EC-005). 무엇이 났는지는 여전히 남는다.
    assert payload["error"]["detail"]["kind"] == "RuntimeError"
    assert payload["error"]["code"] == "INTERNAL_ERROR"
    assert payload["error"]["category"] == "broken"
    assert payload["error"]["next_action"], "다음 행동이 비어 있다 (EC-004)"
    # 사용자 메시지에는 내부 타입 이름이 없다.
    assert "RuntimeError" not in payload["reason"]
    # 실패로 종료했다 — 통과로 넘어가지 않는다.
    assert session.state is SessionState.FAILED


def test_failure_to_record_the_result_is_reported() -> None:
    """**결과를 남기지 못한 것도 알린다** (contracts/websocket.md §진단 이벤트).

    조용히 넘기면 사용자는 "실행이 원래 없었다" 고 오인한다.
    """
    session = _FakeSession()

    async def ok(_session: object, _index: int) -> bool:
        return True

    async def broken_finish(_passed: bool) -> None:
        msg = "디스크가 가득 찼습니다"
        raise OSError(msg)

    task = RunnerTask(
        session=session,  # type: ignore[arg-type]
        step_runner=ok,
        total_steps=1,
        on_finished=broken_finish,
    )

    async def run() -> None:
        task.start()
        await task.wait()

    asyncio.run(run())

    reasons = [p["reason"] for k, p in session.events if k == "run_error"]
    assert reasons, [k for k, _ in session.events]
    assert "정리하지 못했습니다" in str(reasons[0])


def test_cancellation_is_not_recorded_as_a_failure() -> None:
    """중지는 실패가 아니다.

    사용자가 멈춘 실행을 실패로 기록하면 목록 화면에 없던 실패가 생긴다.
    """
    session = _FakeSession()
    started = asyncio.Event()

    async def slow(_session: object, _index: int) -> bool:
        started.set()
        await asyncio.sleep(10)
        return True  # pragma: no cover - 취소된다

    finished_calls: list[bool] = []

    async def on_finished(passed: bool) -> None:  # pragma: no cover - 불려선 안 된다
        finished_calls.append(passed)

    task = RunnerTask(
        session=session,  # type: ignore[arg-type]
        step_runner=slow,
        total_steps=1,
        on_finished=on_finished,
    )

    async def run() -> None:
        task.start()
        await started.wait()
        await task.cancel()

    asyncio.run(run())

    assert finished_calls == [], "취소된 실행이 결과로 기록됐다"
    assert session.state is SessionState.REPLAYING


def test_skipped_steps_are_distinguished_from_not_run() -> None:
    """FR-055 — `skipped` 와 `not_run` 을 구분한다.

    둘을 합치면 "실패한 Step부터 실행" 의 결과에서 앞선 Step 이 왜 안 돌았는지 알 수 없다.
    """
    assert StepOutcome.SKIPPED != StepOutcome.NOT_RUN
    assert {o.value for o in StepOutcome} == {"pass", "fail", "skipped", "not_run"}


# ─── 2. 구조 점검 — 조용히 삼키는 경로가 없다 ─────────────────────────────


EXPECTED_BARE_SUPPRESS: dict[str, int] = {
    # 사유를 남길 수 없는 경로만 허용한다. 늘어나면 이 테스트가 알려 준다.
    # 9번째: 시작 주소를 열지 못한 세션의 브라우저를 닫는 정리 경로 (UX U-04). 실패 사유는
    # TargetUnreachableError 가 이미 들고 나가므로 닫기 실패까지 겹쳐 말할 것이 없다.
    "session.py": 9,
    "artifacts.py": 6,
    # 2번째: 실행 종료 시 전이 안내를 걷은 뒤의 **재발행**이다 (005 FR-146). 통보 경로이며,
    # 이벤트 전송 실패가 실행 종료 자체를 막으면 안 된다 — 상태 전이와 같은 블록에 묶지
    # 않은 이유도 그것이다. 목록은 이미 서버에서 걷혔으므로 REST 조회가 진실을 준다.
    "runner.py": 2,
    "session_loss.py": 5,
    # 2번째: 검증 기준 요소를 **토큰으로 되찾는** 경로다. 페이지가 교체되는 중이거나
    # 참조가 이미 회수됐으면 읽히지 않는다 — 그때는 CSS 재조회로 떨어지고, 그것도
    # 실패하면 기준 없이 `UNVERIFIED` 로 남는다. 확인하지 못한 것을 확인된 것으로 적지
    # 않으므로 삼켜도 안전하다.
    "element_probe.py": 2,
}
"""`contextlib.suppress(Exception)` 이 허용된 횟수.

정리·통보 경로에서는 실패를 삼키는 것이 맞다 — 탭을 닫다 실패한 것이 실행 결과를 바꾸면
안 되고, 이벤트 전송 실패가 실행을 멈추면 안 된다 (FR-047b).

**허용 횟수를 숫자로 고정한다.** 새로 생긴 `suppress` 는 이 테스트를 깨뜨리므로, 그때
"이것도 정리 경로인가" 를 사람이 판단하게 된다. 판단 없이 늘어나는 것을 막는 것이 목적이다.
"""


def test_broad_suppression_is_bounded() -> None:
    """`itb.execution` 에서 예외를 삼키는 지점이 늘지 않았는지 본다."""
    counts: dict[str, int] = {}
    for path in sorted(EXECUTION_DIR.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        found = text.count("contextlib.suppress(Exception)")
        if found:
            counts[path.name] = found

    assert counts == EXPECTED_BARE_SUPPRESS, (
        "예외를 삼키는 지점이 바뀌었다. 정리·통보 경로인지 확인하고 "
        f"EXPECTED_BARE_SUPPRESS 를 갱신하라: {counts}"
    )


def test_every_broad_except_in_execution_has_a_reason_comment() -> None:
    """`except Exception` 마다 **왜 넓게 잡는지** 가 적혀 있다.

    이유 없는 광범위 포획은 조용한 실패의 출발점이다. 주석을 강제하면 최소한 판단이
    기록된다.
    """
    offenders: list[str] = []
    for path in sorted(EXECUTION_DIR.glob("*.py")):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if not stripped.startswith("except Exception"):
                continue
            if "#" not in stripped:
                offenders.append(f"{path.name}:{number}")
    assert not offenders, f"이유가 적히지 않은 광범위 예외 포획: {offenders}"


def test_step_executor_never_returns_silently_on_failure() -> None:
    """실행기의 모든 실패 경로가 `StepFailure` 를 던진다.

    `None` 을 돌려주거나 조용히 통과하면 실패가 통과로 기록된다 — 테스트 도구에서 가장
    나쁜 결함이다.
    """
    from itb.execution import step_executor

    source = inspect.getsource(step_executor)
    # 실패를 표현하는 유일한 수단이 예외임을 확인한다.
    assert "return False" not in source
    assert source.count("raise StepFailure") >= 5


# ─── API 오류 형태 ─────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("factory", "status"),
    [(bad_request, 400), (not_found, 404), (conflict, 409)],
)
def test_api_errors_follow_the_contract_shape(factory: object, status: int) -> None:
    """contracts/rest-api.md — `{error:{code,message,detail}}` 형태를 지킨다."""
    error: ApiError = factory(ErrorCode.NOT_PAUSED, "메시지", state="paused")  # type: ignore[operator]
    assert error.status_code == status
    body = error.detail["error"]
    assert body["code"] == "NOT_PAUSED"
    assert body["message"] == "메시지"
    assert body["detail"] == {"state": "paused"}


def test_error_messages_do_not_leak_internal_paths() -> None:
    """헌법 §보안 — 사용자에게 보여줄 메시지에 내부 경로·스택을 담지 않는다.

    오류 코드 목록에 담긴 문자열은 모두 사용자에게 그대로 노출될 수 있다.
    """
    for code in ErrorCode:
        assert "/Users/" not in code.value
        assert "Traceback" not in code.value


# ─── 004 — 요소 탐색 실패의 세 갈래 (FR-120·FR-123) ─────────────────────────


def test_element_codes_are_blocked_not_broken() -> None:
    """신규 코드 둘 다 `blocked` 다.

    분류는 "내가 고칠 수 있는가"에만 답한다 (003 EC-001). 대상 화면이 느린 것도, 요소가
    모호해진 것도 사용자가 할 일이 있는 상황이므로 `broken` 이 아니다.
    """
    from itb.domain.error import CATEGORY, Category
    from itb.domain.error import ErrorCode as DomainErrorCode

    assert CATEGORY[DomainErrorCode.ELEMENT_NOT_READY] is Category.BLOCKED
    assert CATEGORY[DomainErrorCode.ELEMENT_AMBIGUOUS] is Category.BLOCKED


def test_element_failure_codes_are_distinct_from_step_failed() -> None:
    """FR-120 — 세 실패가 서로 다른 코드로 나가야 한다.

    같은 코드로 내보내면 사용자는 문구를 읽어 구별해야 하고, 그것이 FR-123 이 막으려는
    것이다. "정의 문제"와 "화면이 느린 문제"는 할 일이 정반대다 — 하나는 Step 을 고치고
    하나는 기다리면 된다.
    """
    from itb.domain.error import ErrorCode as DomainErrorCode

    codes = {
        DomainErrorCode.STEP_FAILED,
        DomainErrorCode.ELEMENT_NOT_READY,
        DomainErrorCode.ELEMENT_AMBIGUOUS,
    }
    assert len(codes) == 3


def test_element_codes_carry_a_next_action() -> None:
    """FR-122 — 시간 초과 실패는 다음 행동을 함께 준다.

    `error_body` 가 코드별 기본 안내를 갖고 있어야 한다. 호출부가 매번 문구를 적으면
    같은 상황에 다른 안내가 나간다.
    """
    from itb.domain.error import ErrorCode as DomainErrorCode
    from itb.domain.error import error_body

    for code in (
        DomainErrorCode.ELEMENT_NOT_READY,
        DomainErrorCode.ELEMENT_AMBIGUOUS,
    ):
        body = error_body(code, "요소를 찾을 수 없습니다.")
        assert body["next_action"], f"{code} 에 다음 행동 안내가 없다"
