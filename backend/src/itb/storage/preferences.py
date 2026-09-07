"""사용자 취향. 004 FR-109·FR-110.

**프로젝트가 아니라 사람에 속한다.** 실행 속도는 보는 사람의 취향이지 프로젝트의 속성이
아니다. `itb-project.yaml` 에 넣으면 개인 취향이 팀 저장소에 커밋되고, 헌법 원칙 V 가
"사용자가 버전 관리하는 자산" 이라 부르는 트리를 오염시킨다 (research R8).

`~/.config/itb/registry.json` 과 같은 위치에 두고 같은 원자적 쓰기를 쓴다.

**읽기 실패가 실행을 막지 않는다.** 취향을 못 읽었다고 테스트를 못 돌리면 안 된다 —
레지스트리가 읽기 실패를 경고로만 처리하는 것과 같은 판단이다. 다만 조용히 넘기지도
않는다. 사유를 함께 돌려주고 화면이 알린다 (헌법 보안 요건: 예외를 삼키지 않는다).

**취향만 담는다.** 자격 증명·경로·프로젝트 식별자를 여기 넣지 않는다 (조직 보안 요건).
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass

from itb.domain.run_pacing import DEFAULT_PACING, RunPacing
from itb.storage import atomic
from itb.storage.paths import config_dir

FORMAT_VERSION = 1

PREFERENCES_FILE = "preferences.json"


class PreferencesWriteError(Exception):
    """취향을 남기지 못했다. 호출부가 사용자에게 알릴 수 있는 사유를 담는다."""


@dataclass(frozen=True, slots=True)
class Preferences:
    """사람에 속한 설정. 지금은 실행 속도 하나뿐이다."""

    run_pacing: RunPacing = DEFAULT_PACING

    warning: str | None = None
    """읽지 못한 사유. **저장하지 않는다** — 조회 시에만 채워지는 파생 값이다.

    `registry.ProjectEntry.accessible` 과 같은 판단이다: 파일 시스템은 도구 바깥에서
    바뀌므로 상태를 저장하면 즉시 낡는다.
    """


def preferences_file() -> pathlib.Path:
    """취향 파일 경로."""
    return config_dir() / PREFERENCES_FILE


def load() -> Preferences:
    """취향을 읽는다. **실패해도 예외를 던지지 않는다.**

    파일이 없는 것은 실패가 아니다 — 아직 아무것도 고르지 않은 상태이며 기본값이 맞다.
    깨진 파일과 알 수 없는 값은 사유를 담아 기본값으로 돌려준다. 손으로 편집될 수 있는
    파일이므로 어떤 내용이 들어와도 실행이 멈추면 안 된다.
    """
    path = preferences_file()
    if not path.exists():
        return Preferences()

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return Preferences(
            warning=f"설정 파일을 읽지 못해 기본값으로 진행합니다: {type(exc).__name__}"
        )

    if not isinstance(raw, dict):
        return Preferences(warning="설정 파일 형식이 올바르지 않아 기본값으로 진행합니다.")

    value = raw.get("run_pacing")
    try:
        pacing = RunPacing(value)
    except ValueError:
        return Preferences(
            warning=f"알 수 없는 실행 속도({value!r})라 기본값으로 진행합니다."
        )
    return Preferences(run_pacing=pacing)


def save(pacing: RunPacing) -> None:
    """취향을 남긴다. 실패하면 `PreferencesWriteError`.

    **원자적으로 쓴다.** 부분 기록된 파일이 남으면 다음 실행에서 읽기 실패로 나타나고,
    사용자는 자기가 고른 속도가 왜 사라졌는지 알 수 없다.

    쓰기 실패를 호출부가 어떻게 다룰지는 호출부가 정한다 — 세션의 속도 변경은 이미
    적용됐으므로 그 요청은 성공해야 한다 (contracts/rest-api.md §2).
    """
    path = preferences_file()
    body = json.dumps(
        {"format_version": FORMAT_VERSION, "run_pacing": pacing.value},
        ensure_ascii=False,
        indent=2,
    )
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic.write_text(path, body + "\n")
    except OSError as exc:
        msg = f"설정을 저장하지 못했습니다: {type(exc).__name__}"
        raise PreferencesWriteError(msg) from exc
