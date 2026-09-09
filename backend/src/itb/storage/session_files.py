"""세션이 사용자에게 받은 파일 (010 T062~T064 · FR-337a~c · research R6).

**저장소를 라우터에서 떼어 둔다.** `AppState` 가 이 저장소를 들고 있어야 하는데(정리를
한 곳에서 보장하기 위해서다), 라우터는 `AppState` 를 임포트한다 — 저장소가 라우터에 있으면
고리가 생긴다. 방향을 하나로 유지하는 것이 이 모듈이 따로 있는 이유다.

**세 가지를 지킨다.**

- **상한** (FR-337a) — 파일당 크기와 세션당 개수. 상한 없는 수신 경로를 두지 않는다.
- **정리** (FR-337b) — 세션이 끝나면 지운다. 비정상 종료로 남은 것을 정리하는 경로도 둔다.
- **경계 검증** (FR-337c) — 저장 경로는 **서버가 발급한 식별자**로 만든다. 사용자가 보낸
  이름을 경로에 쓰지 않으므로 경로 구분자·상위 참조가 이름에 들어와도 무해해진다.
"""

from __future__ import annotations

import contextlib
import re
import secrets
import shutil
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from itb.storage.paths import session_files_dir, session_files_root

MAX_FILE_BYTES = 16 * 1024 * 1024
"""파일당 크기 상한 (FR-337a).

첨부 녹화에 쓰이는 파일은 보통 문서·이미지다. 16MB 는 그것을 넉넉히 덮고, 상한이 없는
경로를 두지 않는다는 요구를 만족한다. **넘으면 자르지 않고 거절한다** — 잘린 파일을
대상 페이지가 받으면 그 실패는 원인을 드러내지 않는다.
"""

MAX_FILES_PER_SESSION = 16
"""세션당 개수 상한 (FR-337a). 조작 채널의 `MAX_FILE_IDS` 와 같은 크기다."""

MAX_DISPLAY_NAME = 120

_UNSAFE_NAME = re.compile(r"[^0-9A-Za-z가-힣 ._-]+")


def sanitize_display_name(raw: str | None) -> str:
    """대상 브라우저에 보일 이름을 정리한다 (FR-337c).

    **이 값은 경로에 쓰이지 않는다** — 경로는 `fileId` 로 만든다. 그래도 정리하는 이유는
    이 이름이 대상 브라우저에 전달되고 화면에 표시되기 때문이다. 제어 문자와 경로
    구분자는 표시하는 쪽마다 다르게 깨지고, 그 깨짐은 사용자가 무엇을 올렸는지 알 수
    없게 만든다.
    """
    name = unicodedata.normalize("NFC", raw or "").strip()
    name = "".join(ch for ch in name if unicodedata.category(ch)[0] != "C")
    # 경로처럼 보이는 값이 와도 마지막 조각만 남긴다. 값 자체를 경로로 쓰지는 않지만,
    # 「../../etc/passwd」가 화면에 그대로 뜨는 것은 사용자를 놀라게 한다.
    name = name.replace("\\", "/").split("/")[-1]
    name = _UNSAFE_NAME.sub("-", name).strip("-. ")
    if name in ("", ".", ".."):
        return "file"
    return name[:MAX_DISPLAY_NAME]


@dataclass(slots=True)
class SessionFile:
    """세션 범위 파일 하나 (data-model §5)."""

    file_id: str
    display_name: str
    size: int
    path: Path


@dataclass(slots=True)
class SessionFileStore:
    """한 세션이 받은 파일들. **세션과 함께 사라진다** (FR-337b).

    다른 세션이 `fileId` 로 접근할 수 없다 (FR-340). 저장소가 세션 단위로 나뉘어 있으므로
    그 격리가 **조회 자체에서** 성립한다 — 검사로 막는 것이 아니라 구조로 막는다.
    """

    session_id: str
    files: dict[str, SessionFile] = field(default_factory=dict)

    @property
    def directory(self) -> Path:
        return session_files_dir(self.session_id)

    def path_of(self, file_id: str) -> Path | None:
        """식별자로 실제 경로를 찾는다. 없으면 `None`.

        **사용자가 보낸 값으로 경로를 만들지 않는다.** 여기서 하는 일은 사전 조회뿐이며,
        경로는 업로드 시점에 서버가 만들어 둔 것이다.
        """
        entry = self.files.get(file_id)
        if entry is None or not entry.path.is_file():
            return None
        return entry.path

    def add(self, display_name: str, data: bytes) -> SessionFile:
        """파일 하나를 받는다. 상한 검사는 호출자가 이미 했다."""
        directory = self.directory
        directory.mkdir(parents=True, exist_ok=True)
        # **경로는 서버가 발급한 식별자로만 만든다** (FR-337c). 사용자가 보낸 이름은
        # 표시용으로만 쓴다 — 이것이 경로 주입을 원천적으로 무해하게 만드는 자리다.
        file_id = f"f_{secrets.token_hex(8)}"
        path = directory / file_id
        path.write_bytes(data)
        entry = SessionFile(file_id, display_name, len(data), path)
        self.files[file_id] = entry
        return entry

    def cleanup(self) -> None:
        """세션이 끝났다. 받은 파일을 지운다 (FR-337b).

        **사용자가 보낸 파일이 세션보다 오래 남지 않는다.** 실패해도 예외를 내지 않는다 —
        정리 실패가 세션 종료를 막으면 안 되고, 남은 것은 아래 `sweep_orphans` 가
        다음 기동에서 정리한다.
        """
        self.files.clear()
        with contextlib.suppress(Exception):
            shutil.rmtree(self.directory, ignore_errors=True)


class SessionFileRegistry:
    """세션 ID 별 파일 저장소."""

    def __init__(self) -> None:
        self._stores: dict[str, SessionFileStore] = {}

    def get(self, session_id: str) -> SessionFileStore | None:
        return self._stores.get(session_id)

    def store(self, session_id: str) -> SessionFileStore:
        store = self._stores.get(session_id)
        if store is None:
            store = SessionFileStore(session_id)
            self._stores[session_id] = store
        return store

    def drop(self, session_id: str) -> None:
        store = self._stores.pop(session_id, None)
        if store is not None:
            store.cleanup()

    def drop_all(self) -> None:
        for session_id in list(self._stores):
            self.drop(session_id)


def sweep_orphans(active: set[str]) -> int:
    """살아 있지 않은 세션의 파일 디렉터리를 지운다 (FR-337b).

    **비정상 종료로 남은 것을 정리하는 경로다.** 프로세스가 죽으면 `cleanup` 이 돌지
    않으므로, 다음 기동에서 뿌리를 훑어 활성 세션에 속하지 않은 디렉터리를 지운다.

    지운 개수를 돌려준다. 실패는 삼킨다 — 정리가 기동을 막으면 안 된다.
    """
    root = session_files_root()
    if not root.is_dir():
        return 0
    removed = 0
    for child in root.iterdir():
        if child.name in active or not child.is_dir():
            continue
        with contextlib.suppress(Exception):
            shutil.rmtree(child, ignore_errors=True)
            removed += 1
    return removed
