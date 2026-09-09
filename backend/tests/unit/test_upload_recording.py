"""파일 업로드 녹화 (2026-09-09 사용자 보고 — 「파일업로드 녹화가 제대로 안됨」).

## 무엇을 고정하는가

이전에는 이 경로에 Step 이 없었다. 주입 스크립트가 ``file_input`` 을 보내면 Python 쪽은
경고 하나만 남겼다 — 「파일 입력이 감지됐습니다 … Step 편집에서 파일 경로를 직접 지정해야
합니다」. 그 안내가 가리키는 곳이 제품에 없었으므로(그런 칸도 Step 종류도 없었다) 사용자는
안내를 따를 수 없었고, 재실행은 파일 없이 지나갔다.

이 파일은 **브라우저 없이** 그 경로만 본다. 후보 수집은 살아 있는 문서를 요구하므로
(`collect_and_verify`) 그 한 지점을 대역으로 바꾼다 — 재는 것은 「받은 것으로 어떤 Step 을
만드는가」이고, 후보 수집은 이미 다른 검증이 덮는다.
"""

from __future__ import annotations

from typing import Any

import pytest

from itb.domain.locator import Candidate, CandidateStatus, TargetLocator
from itb.domain.step import Step, StepType, extension_of
from itb.recording.recorder import Origin, Recorder


class _FakeSession:
    """리코더가 요구하는 최소 세션. 브라우저 없이 파이프라인만 본다."""

    def __init__(self) -> None:
        self.emitted: list[tuple[str, dict[str, Any]]] = []
        self.context = None
        self.max_tabs = 10

    async def emit(self, event_type: str, **payload: Any) -> None:
        self.emitted.append((event_type, payload))

    def tab_of(self, _page: Any) -> Any:
        return None

    def open_tabs(self) -> list[Any]:
        return []


class _FakePage:
    """`Origin` 이 요구하는 자리만 채운다. 이 검증은 페이지를 만지지 않는다."""

    url = "https://example.internal/upload"


def _recorder(
    sink_log: list[Step], warnings: list[str], monkeypatch: pytest.MonkeyPatch
) -> Recorder:
    async def sink(step: Step, _index: int) -> None:
        sink_log.append(step)

    rec = Recorder(
        session=_FakeSession(),  # type: ignore[arg-type]
        sink=sink,
        store=None,
        public_key=None,
    )

    async def collect(
        _origin: Origin, _element: dict[str, Any], warn_on_failure: bool = True
    ) -> TargetLocator | None:
        return TargetLocator(
            test_id=Candidate(value="attach", status=CandidateStatus.VERIFIED)
        )

    """후보 수집만 대역으로 바꾼다 — 그 지점이 살아 있는 문서를 요구하는 유일한 곳이다.

    `Recorder` 는 슬롯을 쓰므로 인스턴스 속성을 새로 붙일 수 없다 (`__slots__` 또는
    `@dataclass(slots=True)`). 클래스에 걸고 `monkeypatch` 가 되돌린다 — 이 검증만
    영향을 받는다.
    """
    monkeypatch.setattr(Recorder, "_collect_target", collect, raising=True)
    monkeypatch.setattr(
        Recorder, "_warn", lambda _self, message: warnings.append(message), raising=True
    )
    return rec


def _origin() -> Origin:
    page = _FakePage()
    return Origin(page=page, root=page, tab=0, frame_url=None)  # type: ignore[arg-type]


ELEMENT = {"label": "첨부 파일", "attributes": {}}


class UploadRecordingTests:
    async def test_makes_an_upload_step_with_the_file_name(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """**확장자가 정의에 들어간다.** 사용자가 요구한 것이 그것이다."""
        steps: list[Step] = []
        rec = _recorder(steps, [], monkeypatch)
        rec.active = True

        await rec._record_upload(_origin(), ELEMENT, {"files": ["보고서.xlsx"]})

        assert len(steps) == 1, "파일 선택이 Step 을 만들지 않았다"
        step = steps[0]
        assert step.type == StepType.UPLOAD
        assert step.file_name == "보고서.xlsx"
        assert extension_of(step.file_name) == "xlsx"

    async def test_the_label_names_the_file(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """목록 행에서 **어느 파일인지** 보여야 한다 — 행을 열지 않고 확장자를 읽는다."""
        steps: list[Step] = []
        rec = _recorder(steps, [], monkeypatch)
        rec.active = True

        await rec._record_upload(_origin(), ELEMENT, {"files": ["자료.csv"]})

        assert "자료.csv" in steps[0].label
        assert "첨부 파일" in steps[0].label

    async def test_cancelling_makes_no_step(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """파일을 고르지 않고 닫으면 만들 Step 이 없다.

        ``change`` 가 빈 목록으로 올 수 있다. 그때 Step 을 만들면 「아무 파일도 올리지
        않는 업로드 Step」이 생기고, 재실행에서 무엇을 올릴지 알 수 없다.
        """
        steps: list[Step] = []
        rec = _recorder(steps, [], monkeypatch)
        rec.active = True

        await rec._record_upload(_origin(), ELEMENT, {"files": []})
        await rec._record_upload(_origin(), ELEMENT, {})
        await rec._record_upload(_origin(), ELEMENT, {"files": ["   "]})

        assert steps == []

    async def test_multiple_files_record_the_first_and_warn(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """**조용히 버리지 않는다.**

        다중 업로드는 Step 하나가 여러 파일을 갖는 모양을 요구하고, 그것은 지금 요구에
        없다. 첫 번째만 기록하되 그 사실을 경고로 알린다 — 조용히 버리면 사용자는
        재실행이 왜 다르게 도는지 알 수 없다.
        """
        steps: list[Step] = []
        warnings: list[str] = []
        rec = _recorder(steps, warnings, monkeypatch)
        rec.active = True

        await rec._record_upload(
            _origin(), ELEMENT, {"files": ["첫.xlsx", "둘.csv", "셋.png"]}
        )

        assert len(steps) == 1
        assert steps[0].file_name == "첫.xlsx"
        assert any("첫.xlsx" in w for w in warnings), f"경고가 없다: {warnings}"
        assert any("3" in w for w in warnings)
