"""005 (UX 워크스루 결함 수정) 테스트 공용 재료.

`tests/` 에는 `__init__.py` 가 없으므로 pytest 가 이 디렉터리를 sys.path 에 넣는다.
테스트 모듈에서 ``from us5_support import ...`` 로 쓴다.

여기 있는 것은 **리포트의 증상을 재현하는 재료**다 (tasks T001). 리포트가 쓴 것과 같은
구성을 쓴다 — `fixtures/sample-app` 위에 중간 Step 에서 반드시 실패하는 테스트와 항상
통과하는 테스트.

**실패를 결정적으로 만든다.** 존재하지 않는 `testId` 를 쓰면 대상 앱을 고치지 않아도 되고,
실패 사유가 매번 같다. 타이밍에 의존하는 실패는 재현이 흔들려 회귀 판정을 못 한다.
"""

from __future__ import annotations

from itb.domain.locator import Candidate, CandidateStatus, TargetLocator
from itb.domain.step import (
    AssertionStep,
    ClickStep,
    FillStep,
    Step,
)
from itb.domain.test_case import AuthoringMode, Test

FAIL_STEP_INDEX = 5
"""TC-FAIL 에서 실패하는 Step 의 0-기반 인덱스. 사용자에게는 `Step 06` 으로 보인다."""

FAIL_WAIT_MS = 20_000
"""실패 Step 이 소진하는 대기 예산.

**이 구간이 중지·일시정지의 전이 동작을 관찰할 유일한 창**이다 (quickstart §0). 창이
없으면 US3 을 검증할 수 없다. 20초는 리포트가 실측한 값과 같다.
"""

MISSING_TEST_ID = "dashboard-open"
"""sample-app 에 존재하지 않는 testId. 리포트가 실패를 만든 것과 같은 값이다."""


def _target(test_id: str, css: str) -> TargetLocator:
    """testId 를 1순위로, css 를 최후 수단으로 갖는 후보 묶음.

    후보를 둘 두는 이유는 헌법 원칙 IV 다 — css 만 가진 Step 은 저장하지 않는다.
    """
    return TargetLocator(
        tag="button",
        test_id=Candidate(value=test_id, status=CandidateStatus.VERIFIED),
        css=Candidate(value=css, status=CandidateStatus.VERIFIED),
    )


def _missing_target() -> TargetLocator:
    """어느 후보로도 찾을 수 없는 요소.

    `status` 를 `VERIFIED` 로 두는 것은 **기록 시점에는 있었다가 화면이 바뀐 상황**을
    흉내 내기 위해서다. 그것이 사용자가 만나는 실패의 실제 모양이다.
    """
    return TargetLocator(
        tag="button",
        test_id=Candidate(value=MISSING_TEST_ID, status=CandidateStatus.VERIFIED),
        css=Candidate(value=f'[data-testid="{MISSING_TEST_ID}"]', status=CandidateStatus.VERIFIED),
    )


def failing_steps() -> list[Step]:
    """7 Step. 01~05 통과 · 06 실패(대기 예산 소진) · 07 미실행.

    01~02 가 로그인이다. **부분 실행이 로그인을 건너뛰면 06 이 다른 이유로 실패한다** —
    그 사실을 화면이 말하지 않는 것이 U-02 이고, US4 가 검증하는 것이 그것이다.
    """
    return [
        FillStep(
            id="step-01",
            label="이메일 입력",
            target=_target("login-email", "#email"),
            value="tester@example.com",
        ),
        ClickStep(
            id="step-02",
            label="로그인",
            target=_target("login-submit", "#submit"),
        ),
        ClickStep(
            id="step-03",
            label="프로젝트 생성 열기",
            target=_target("create-project", "#open-create"),
        ),
        FillStep(
            id="step-04",
            label="프로젝트명 입력",
            target=_target("project-type", "#pname"),
            value="005 검증",
        ),
        ClickStep(
            id="step-05",
            label="저장",
            target=_target("save-project", "#save"),
        ),
        ClickStep(
            id="step-06",
            label="대시보드 열기",
            target=_missing_target(),
            timeout_ms=FAIL_WAIT_MS,
        ),
        AssertionStep(
            id="step-07",
            label="대시보드 표시 확인",
            assertion=_visible_assertion(),
        ),
    ]


def _visible_assertion():  # noqa: ANN202 - Assertion 형태는 도메인이 정한다
    from itb.domain.assertion import Assertion, AssertionKind

    return Assertion(
        kind=AssertionKind.VISIBLE,
        target=_target("late-note", "#late-note"),
    )


def passing_steps() -> list[Step]:
    """5 Step. 항상 통과한다.

    US1 의 "성공한 실행의 결과를 열 수 있는가"(U-13)와 US2 의 통과 표기 검증에 쓴다.
    """
    return [
        FillStep(
            id="step-01",
            label="이메일 입력",
            target=_target("login-email", "#email"),
            value="tester@example.com",
        ),
        ClickStep(
            id="step-02",
            label="로그인",
            target=_target("login-submit", "#submit"),
        ),
        ClickStep(
            id="step-03",
            label="프로젝트 생성 열기",
            target=_target("create-project", "#open-create"),
        ),
        FillStep(
            id="step-04",
            label="프로젝트명 입력",
            target=_target("project-type", "#pname"),
            value="005 통과",
        ),
        ClickStep(
            id="step-05",
            label="저장",
            target=_target("save-project", "#save"),
        ),
    ]


def failing_test(test_id: str = "TC-901", start_url: str = "http://127.0.0.1:4300/login.html") -> Test:
    """TC-FAIL — Step 06 에서 반드시 실패한다."""
    return Test(
        id=test_id,
        name="005 실패 재현",
        authoring_mode=AuthoringMode.RECORD,
        start_url=start_url,
        steps=failing_steps(),
    )


def passing_test(test_id: str = "TC-902", start_url: str = "http://127.0.0.1:4300/login.html") -> Test:
    """TC-PASS — 항상 통과한다."""
    return Test(
        id=test_id,
        name="005 통과 재현",
        authoring_mode=AuthoringMode.RECORD,
        start_url=start_url,
        steps=passing_steps(),
    )
