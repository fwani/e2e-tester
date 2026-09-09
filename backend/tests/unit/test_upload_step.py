"""파일 업로드 Step (2026-09-09 사용자 보고).

보고 문장 둘.

1. 「파일업로드 녹화가 제대로 안됨」
2. 「파일업로드 녹화의 경우, 파일의 확장자 기록되 되어야함. 실제 서비스에서는 확장자를
   보는경우가 있기 때문」

## 무엇이 없어서 그랬나

`StepType` 에 `upload` 가 없었다. 리코더는 파일 입력을 감지하고도 경고 하나만 남겼고
(「파일 입력이 감지됐습니다 … Step 편집에서 파일 경로를 직접 지정해야 합니다」), 그
안내가 가리키는 「Step 편집에서 파일 경로 지정」은 **제품에 없었다** — 그런 칸도 Step
종류도 없었으므로 사용자는 안내를 따를 수 없었다 (006 E-03 과 같은 형태).

001 research 는 「감지해 Step 을 만들되 경로는 사용자가 지정한다」로 정해 두었고, 구현이
비어 있는 채 문구만 남아 있었다.

이 파일이 고정하는 것은 **확장자가 정의에서 실행까지 살아남는가**다.
"""

from __future__ import annotations

import pathlib

import pytest

from itb.domain.locator import Candidate, CandidateStatus, TargetLocator
from itb.domain.step import (
    StepType,
    UploadStep,
    extension_of,
    mime_type_of,
    target_of,
)
from itb.domain.test_case import AuthoringMode, Test
from itb.execution.step_edits import FieldNotSupportedError, update_step
from itb.storage.yaml_io import dump_model, load_model


def _target() -> TargetLocator:
    return TargetLocator(
        test_id=Candidate(value="attach", status=CandidateStatus.VERIFIED)
    )


def _step(file_name: str = "보고서.xlsx") -> UploadStep:
    return UploadStep(
        id="step-01", label=f"첨부 에 {file_name} 올리기", target=_target(), file_name=file_name
    )


class ExtensionTests:
    """확장자 판정 — **한 곳에서만 한다** (`extension_of`)."""

    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("보고서.xlsx", "xlsx"),
            ("보고서.XLSX", "xlsx"),
            ("사진.jpeg", "jpeg"),
            # 마지막 조각만 본다. `tar.gz` 를 한 덩이로 보려면 규칙이 두 개가 된다.
            ("archive.tar.gz", "gz"),
            # 확장자가 없는 것은 **오류가 아니다** — 확장자 없는 파일도 올릴 수 있다.
            ("README", ""),
            # 점으로 끝나면 확장자가 없다. 빈 확장자를 지어내지 않는다.
            ("이름.", ""),
            # 숨김 파일은 이름이 점으로 시작한다 — 확장자가 아니다.
            (".gitignore", ""),
        ],
    )
    def test_reads_the_last_segment_lowercased(self, name: str, expected: str) -> None:
        assert extension_of(name) == expected


class MimeTypeTests:
    def test_guesses_from_the_name(self) -> None:
        assert "spreadsheetml.sheet" in mime_type_of("보고서.xlsx")
        assert mime_type_of("사진.png") == "image/png"

    def test_falls_back_to_octet_stream(self) -> None:
        """**지어내지 않는다.** 모르는 유형에 그럴듯한 값을 넣으면 서버가 다른 이유로
        거절하고, 사용자는 업로드가 왜 실패했는지 알 수 없다."""
        assert mime_type_of("README") == "application/octet-stream"
        assert mime_type_of("데이터.itb-unknown") == "application/octet-stream"


class ModelTests:
    def test_is_part_of_the_step_union(self) -> None:
        """판별 유니온에 있어야 정의 파일에서 읽힌다 (원칙 I)."""
        assert StepType.UPLOAD in set(StepType)

    def test_has_a_target(self) -> None:
        """대상 요소를 갖는다 — 어느 파일 입력에 넣는지가 없으면 재실행할 수 없다."""
        assert target_of(_step()) is not None

    def test_rejects_an_empty_file_name(self) -> None:
        """이름이 없으면 확장자도 없다 — 이 Step 의 뜻이 사라진다."""
        with pytest.raises(ValueError):
            UploadStep(id="step-01", label="첨부", target=_target(), file_name="")

    def test_survives_a_definition_roundtrip(self, tmp_path: pathlib.Path) -> None:
        """**정의 파일에 남아야 한다** (원칙 V).

        사용자가 git 에 커밋해 보관하는 자산이므로, 확장자가 왕복에서 사라지면 이 기능은
        없는 것과 같다.
        """
        test = Test(
            id="TC-001",
            name="첨부",
            authoring_mode=AuthoringMode.RECORD,
            start_url="https://example.internal/upload",
            steps=[_step()],
        )
        # `dump_model` 은 경로에 원자적으로 쓴다 (003 AP-042) — 파일을 지나야 왕복이다.
        path = tmp_path / "TC-001.yaml"
        dump_model(path, test)
        loaded = load_model(path, Test)
        assert loaded.steps[0].type == StepType.UPLOAD
        assert loaded.steps[0].file_name == "보고서.xlsx"
        assert extension_of(loaded.steps[0].file_name) == "xlsx"


class EditingTests:
    """편집 경로는 **하나다** (`update_step`) — 세션 편집과 정의 편집이 같이 쓴다."""

    def test_changes_the_file_name(self) -> None:
        result = update_step([_step()], 0, "step-01", file_name="자료.csv")
        updated = result.steps[0]
        assert updated.file_name == "자료.csv"
        assert extension_of(updated.file_name) == "csv"

    def test_other_kinds_reject_the_field(self) -> None:
        """**파일 이름을 갖지 않는 종류에는 붙지 않는다.**

        조용히 무시하면 사용자는 고쳐졌다고 믿는다. 거절 문구가 어느 필드인지 말한다.
        """
        from itb.domain.step import ClickStep

        click = ClickStep(id="step-01", label="클릭", target=_target())
        with pytest.raises(FieldNotSupportedError):
            update_step([click], 0, "step-01", file_name="자료.csv")

    def test_keeps_the_kind(self) -> None:
        """종류는 편집으로 바뀌지 않는다 (`update_step` 의 규칙)."""
        result = update_step([_step()], 0, "step-01", label="다시")
        assert result.steps[0].type == StepType.UPLOAD
