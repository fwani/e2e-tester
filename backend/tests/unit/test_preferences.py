"""사용자 취향 파일. 004 FR-109·FR-110, data-model §5.

**읽기 실패가 실행을 막지 않는지**가 이 파일의 주제다. 취향 파일은 손으로 편집될 수 있고
디스크는 도구 바깥에서 바뀐다. 어떤 내용이 들어와도 테스트를 못 돌리는 상태가 되면 안
된다 — 다만 조용히 넘기지도 않는다.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from itb.domain.run_pacing import DEFAULT_PACING, RunPacing
from itb.storage import preferences


@pytest.fixture(autouse=True)
def _isolated_config(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """사용자의 실제 `~/.config/itb` 를 건드리지 않는다."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))


def test_missing_file_is_not_a_failure() -> None:
    """파일이 없는 것은 실패가 아니다 — 아직 아무것도 고르지 않은 상태다."""
    loaded = preferences.load()
    assert loaded.run_pacing is DEFAULT_PACING
    assert loaded.warning is None, "없는 것을 경고로 알리면 첫 실행마다 경고가 뜬다"


def test_round_trip() -> None:
    preferences.save(RunPacing.SLOW)
    assert preferences.load().run_pacing is RunPacing.SLOW


def test_broken_json_falls_back_with_a_reason() -> None:
    """깨진 파일은 기본값으로 진행하되 **사유를 남긴다.**

    조용히 기본값으로 돌아가면 사용자는 자기가 고른 속도가 왜 사라졌는지 알 수 없다.
    """
    path = preferences.preferences_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{ 이건 JSON 이 아니다", encoding="utf-8")

    loaded = preferences.load()
    assert loaded.run_pacing is DEFAULT_PACING
    assert loaded.warning, "읽지 못한 사유가 있어야 한다"


def test_unknown_pacing_value_falls_back_with_a_reason() -> None:
    """손으로 편집된 알 수 없는 값도 실행을 막지 않는다."""
    path = preferences.preferences_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"format_version": 1, "run_pacing": "turtle"}), encoding="utf-8"
    )

    loaded = preferences.load()
    assert loaded.run_pacing is DEFAULT_PACING
    assert loaded.warning and "turtle" in loaded.warning


def test_non_object_content_falls_back_with_a_reason() -> None:
    path = preferences.preferences_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([1, 2, 3]), encoding="utf-8")

    loaded = preferences.load()
    assert loaded.run_pacing is DEFAULT_PACING
    assert loaded.warning


def test_load_never_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """읽기 중 어떤 OS 오류가 나도 예외가 밖으로 나가지 않는다.

    취향을 못 읽었다고 세션 생성이 실패하면, 사용자는 테스트를 아예 돌릴 수 없다.
    """
    path = preferences.preferences_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{}", encoding="utf-8")

    def _boom(*_args: object, **_kwargs: object) -> str:
        msg = "권한 없음"
        raise PermissionError(msg)

    monkeypatch.setattr(pathlib.Path, "read_text", _boom)
    loaded = preferences.load()
    assert loaded.run_pacing is DEFAULT_PACING
    assert loaded.warning


def test_write_is_atomic() -> None:
    """부분 기록된 파일을 남기지 않는다.

    반쪽짜리 파일이 남으면 다음 실행에서 읽기 실패로 나타난다 — 사용자는 자기가 고른
    속도가 왜 사라졌는지 알 수 없다.
    """
    preferences.save(RunPacing.SLOW)
    path = preferences.preferences_file()

    # 원자적 쓰기는 임시 파일을 남기지 않는다.
    leftovers = [
        p for p in path.parent.iterdir() if p != path and p.name.startswith(path.name)
    ]
    assert not leftovers, f"임시 파일이 남았다: {leftovers}"

    body = json.loads(path.read_text(encoding="utf-8"))
    assert body["run_pacing"] == RunPacing.SLOW.value
    assert body["format_version"] == preferences.FORMAT_VERSION


def test_write_failure_is_reported(monkeypatch: pytest.MonkeyPatch) -> None:
    """쓰기 실패를 삼키지 않는다. 호출부가 사용자에게 알릴 수 있어야 한다."""

    def _boom(*_args: object, **_kwargs: object) -> None:
        msg = "디스크 가득 참"
        raise OSError(msg)

    monkeypatch.setattr(preferences.atomic, "write_text", _boom)
    with pytest.raises(preferences.PreferencesWriteError):
        preferences.save(RunPacing.FAST)


def test_stores_preference_only() -> None:
    """**취향만 담는다** (조직 보안 요건).

    이 파일에 자격 증명·경로·프로젝트 식별자가 새어 들어가면 안 된다. 필드 집합을
    고정해 두면 나중에 편의로 무언가를 얹는 변경이 여기서 걸린다.
    """
    preferences.save(RunPacing.NORMAL)
    body = json.loads(preferences.preferences_file().read_text(encoding="utf-8"))
    assert set(body) == {"format_version", "run_pacing"}
