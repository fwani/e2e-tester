"""엑셀 통로 검증용 공용 도구 (기능 014).

브라우저 없이 프로젝트를 채운다. 내보내기가 보는 것은 저장된 정의와 실행 결과뿐이므로,
그 둘을 직접 써 넣으면 녹화를 돌리지 않고도 모든 모양을 만들 수 있다.
"""

from __future__ import annotations

import contextlib
import datetime as dt
import io
import pathlib
from collections.abc import Iterator
from typing import Any

from fastapi.testclient import TestClient

from itb.domain.assertion import Assertion, AssertionKind
from itb.domain.locator import Candidate, CandidateStatus, TargetLocator
from itb.domain.run_result import Outcome, RunResult, RunScope
from itb.domain.step import AssertionStep, ClickStep, FillStep, Step
from itb.domain.test_case import AuthoringMode, Test, Variable
from itb.storage.repository import ProjectRepository


def verified(value: str) -> Candidate:
    return Candidate(value=value, status=CandidateStatus.VERIFIED)


def target(text: str) -> TargetLocator:
    return TargetLocator(text=verified(text))


def click(index: int, label: str) -> Step:
    return ClickStep(id=f"step-{index:02d}", label=label, target=target(label))


def fill(index: int, label: str, value: str) -> Step:
    return FillStep(id=f"step-{index:02d}", label=label, target=target(label), value=value)


def check(index: int, label: str, value: str) -> Step:
    return AssertionStep(
        id=f"step-{index:02d}",
        label=label,
        assertion=Assertion(kind=AssertionKind.TEXT, value=value),
    )


def make_test(
    test_id: str,
    name: str,
    *,
    steps: list[Step] | None = None,
    variables: list[Variable] | None = None,
    description: str | None = None,
    actor: str | None = None,
) -> Test:
    """저장 가능한 테스트 하나. 기본은 동작 2개 + 검증 1개."""
    return Test(
        id=test_id,
        name=name,
        description=description,
        actor=actor,
        authoring_mode=AuthoringMode.RECORD,
        start_url="https://example.internal/login",
        variables=variables or [],
        steps=steps
        or [
            click(1, "로그인 버튼"),
            click(2, "확인 버튼"),
            check(3, "대시보드 표시 확인", "대시보드"),
        ],
    )


def make_result(test_id: str, outcome: Outcome) -> RunResult:
    now = dt.datetime.now(dt.UTC)
    return RunResult(
        test_id=test_id,
        outcome=outcome,
        started_at=now,
        finished_at=now,
        total_ms=10,
        passed_count=1,
        total_count=1,
        browser="chromium",
        steps=[],
        scope=RunScope.FULL,
        attempted_count=1,
    )


def repo_of(client: TestClient) -> ProjectRepository:
    """열린 프로젝트의 저장소를 연다."""
    root = client.get("/api/project").json()["root"]
    return ProjectRepository.open(pathlib.Path(root))


def read_back(data: bytes) -> dict[str, list[list[Any]]]:
    """내보낸 바이트를 다시 읽어 ``{시트 이름: 행들}`` 로 만든다.

    **openpyxl 로 다시 읽는다.** 우리가 만든 자료구조를 그대로 확인하면 "썼다고 생각한 것"을
    확인하게 된다. 파일을 거쳐 오면 실제로 파일에 들어간 것을 본다.
    """
    from openpyxl import load_workbook

    wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    try:
        return {
            name: [list(row) for row in wb[name].iter_rows(values_only=True)]
            for name in wb.sheetnames
        }
    finally:
        wb.close()


def sheet_names(data: bytes) -> list[str]:
    from openpyxl import load_workbook

    wb = load_workbook(io.BytesIO(data), read_only=True)
    try:
        return list(wb.sheetnames)
    finally:
        wb.close()


# ─── 가져오기 검증용 ────────────────────────────────────────────────────────

HEADER_ROW = ["TC ID", "대상기능", "테스트항목", "수행자", "수행 절차", "기대 결과", "결과"]


def build_xlsx(sheets: dict[str, list[list[Any]]], *, header: list[Any] | None = None) -> bytes:
    """시트 이름 → 데이터 행들 로 워크북 바이트를 만든다.

    머리글은 기본으로 :data:`HEADER_ROW` 를 쓴다. 머리글 자체를 시험하려면 `header` 를
    주거나, 값에 머리글을 포함한 뒤 `header=[]` 를 준다.
    """
    from openpyxl import Workbook

    wb = Workbook()
    wb.remove(wb.active)
    for name, rows in sheets.items():
        ws = wb.create_sheet(title=name)
        head = HEADER_ROW if header is None else header
        if head:
            ws.append(head)
        for row in rows:
            ws.append(row)
    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def upload(client: TestClient, data: bytes, filename: str = "설계서.xlsx") -> Any:
    """미리보기에 파일을 올린다."""
    return client.post(
        "/api/import/preview",
        files={
            "file": (
                filename,
                data,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )


def preview(client: TestClient, sheets: dict[str, list[list[Any]]], **kw: Any) -> dict[str, Any]:
    """워크북을 만들어 올리고 계획을 돌려준다. 실패하면 그 자리에서 드러낸다."""
    resp = upload(client, build_xlsx(sheets, **kw))
    assert resp.status_code == 200, resp.text
    return resp.json()


def row(
    tc_id: str | None = None,
    name: str | None = None,
    description: str | None = None,
    actor: str | None = None,
    procedure: str | None = None,
    expectation: str | None = None,
    outcome: str | None = None,
) -> list[Any]:
    """머리글 순서에 맞춘 데이터 행 하나."""
    return [tc_id, name, description, actor, procedure, expectation, outcome]


@contextlib.contextmanager
def draft_write_fails(*, on_call: int | None = None) -> Iterator[None]:
    """초안 쓰기를 실패시킨다 — 되돌림을 실물로 확인하기 위한 것이다.

    **`monkeypatch.undo()` 를 쓰지 않는다.** 그것은 같은 `monkeypatch` 인스턴스가 걸어 둔
    *모든* 변경을 되돌리므로, `isolated_home` 이 설정한 `HOME`·`XDG_*` 까지 풀린다. 그러면
    그 뒤의 요청이 **개발자의 실제 홈**을 보게 되고, 검증이 엉뚱한 것을 확인한다
    (실제로 프로젝트 목록에 개발자의 진짜 프로젝트가 나타났다).

    이 도우미는 자기가 바꾼 것만 되돌린다.

    Args:
        on_call: 몇 번째 호출에서 실패할지 (1부터). ``None`` 이면 언제나 실패한다.
    """
    from itb.storage.drafts import DraftStore

    original = DraftStore.write
    calls = {"n": 0}

    def patched(self: DraftStore, draft: object) -> object:
        calls["n"] += 1
        if on_call is None or calls["n"] == on_call:
            msg = "초안 쓰기를 일부러 실패시킨다"
            raise OSError(msg)
        return original(self, draft)  # type: ignore[arg-type]

    DraftStore.write = patched  # type: ignore[method-assign]
    try:
        yield
    finally:
        DraftStore.write = original  # type: ignore[method-assign]
