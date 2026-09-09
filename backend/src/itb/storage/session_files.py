"""세션이 사용자에게 받은 파일 (010 T062~T064 · FR-337a~c · research R6).

**저장소를 라우터에서 떼어 둔다.** `AppState` 가 이 저장소를 들고 있어야 하는데(정리를
한 곳에서 보장하기 위해서다), 라우터는 `AppState` 를 임포트한다 — 저장소가 라우터에 있으면
고리가 생긴다. 방향을 하나로 유지하는 것이 이 모듈이 따로 있는 이유다.

**세 가지를 지킨다.**

- **상한** (FR-337a) — 파일당 크기와 세션당 개수. 상한 없는 수신 경로를 두지 않는다.
- **정리** (FR-337b) — 세션이 끝나면 지운다. 비정상 종료로 남은 것을 정리하는 경로도 둔다.
- **경계 검증** (FR-337c) — 저장 경로의 **디렉터리는 서버가 발급한 식별자**다:
  ``<세션>/f_<hex>/<이름>``. 사용자가 보낸 이름은 마지막 조각에만 오고, 그 조각은
  `sanitize_display_name` 을 지나며 `add` 가 결과 경로의 담김을 다시 확인한다.

  **2026-09-09 에 이 규칙이 한 겹 좁아졌다** (사용자 보고 — 「파일 이름 에 확장자가
  포함되어야한다」). 이전에는 이름을 경로에 **전혀** 쓰지 않고 ``<세션>/f_<hex>`` 에
  저장했는데, 대상 브라우저가 받는 파일 이름은 **경로의 마지막 조각**이다
  (`FileChooser.set_files` · `DOM.setFileInputFiles` 는 둘 다 경로만 받는다). 그래서
  대상 페이지는 확장자 없는 ``f_1a2b3c…`` 를 받았고, 확장자를 보는 서비스는 거절했다.
  이름을 경로에서 빼는 것으로는 그 요구를 만족할 수 없다 — 자세한 근거는 `add` 에 있다.
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

    제어 문자와 경로 구분자를 걷어낸다 — 이 이름은 대상 브라우저에 전달되고 화면에
    표시되며, 그 깨짐은 사용자가 무엇을 올렸는지 알 수 없게 만든다.

    ## 2026-09-09 — **확장자를 보존한다** (사용자 보고)

    보고 문장: 「파일 이름 에 확장자가 포함되어야한다」. 이 함수가 확장자를 먹는 경우가
    있었다. 예: ``報告.xlsx`` → 허용 문자 밖의 글자가 ``-`` 로 바뀌어 ``-.xlsx`` 가 되고,
    마지막 ``.strip("-. ")`` 가 앞의 ``-.`` 를 함께 떼어 **``xlsx``** 가 남았다. 이름이
    확장자였던 것이 되고 확장자는 사라진다.

    그래서 **줄기와 확장자를 따로 정리한다.** 확장자는 이 기능의 핵심 정보다 — 사용자가
    말한 이유가 「실제 서비스에서는 확장자를 보는경우가 있기 때문」이다. 줄기가 정리 끝에
    비면 ``file`` 을 쓰고 확장자는 그대로 붙인다.

    허용 문자 목록(`_UNSAFE_NAME`)을 넓히지 않는다. 넓히면 표시·경로·로그마다 다르게
    깨지는 문자가 다시 들어오고, 그것이 이 함수가 있는 이유다.
    """
    name = unicodedata.normalize("NFC", raw or "").strip()
    name = "".join(ch for ch in name if unicodedata.category(ch)[0] != "C")
    # 경로처럼 보이는 값이 와도 마지막 조각만 남긴다. 「../../etc/passwd」가 화면에
    # 그대로 뜨는 것은 사용자를 놀라게 한다.
    name = name.replace("\\", "/").split("/")[-1]

    stem, dot, extension = name.rpartition(".")
    if not dot or not stem:
        # 확장자가 없거나 숨김 파일이다 (`.gitignore`). 통째로 정리한다 —
        # `itb.domain.step.extension_of` 와 같은 판정이다.
        cleaned = _UNSAFE_NAME.sub("-", name).strip("-. ")
        return (cleaned or "file")[:MAX_DISPLAY_NAME]

    clean_stem = _UNSAFE_NAME.sub("-", stem).strip("-. ") or "file"
    clean_ext = _UNSAFE_NAME.sub("-", extension).strip("-. ")
    if not clean_ext:
        # 확장자가 정리 끝에 비었다 — 붙일 것이 없다. 줄기만 남긴다.
        return clean_stem[:MAX_DISPLAY_NAME]
    # 확장자는 자르지 않는다. 잘린 확장자는 없는 확장자보다 나쁘다 (엉뚱한 유형이 된다).
    room = max(1, MAX_DISPLAY_NAME - len(clean_ext) - 1)
    return f"{clean_stem[:room]}.{clean_ext}"


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
        """파일 하나를 받는다. 상한 검사는 호출자가 이미 했다.

        ## 2026-09-09 — **파일 이름이 경로의 마지막 조각이 됐다** (사용자 보고)

        보고 문장: 「파일 이름 에 확장자가 포함되어야한다」.

        이전에는 ``<세션 디렉터리>/f_<hex>`` 에 저장했다. 경로에 사용자 이름을 쓰지 않는
        것이 FR-337c 의 방법이었고 그 자체로는 옳았다. 그런데 **대상 브라우저가 받는 이름은
        경로의 마지막 조각**이다 — `FileChooser.set_files` 와 `DOM.setFileInputFiles` 는
        둘 다 경로를 받고 그 basename 을 파일 이름으로 쓴다. 그래서 대상 페이지는
        ``f_1a2b3c…`` 라는 **확장자 없는** 파일을 받았고, 확장자를 보는 서비스는 그것을
        거절한다. 녹화도 그 이름을 Step 에 남겼다.

        **경로를 버퍼로 대신할 수는 없다.** `DOM.setFileInputFiles` 는 바이트를 받지
        않으므로(경로 전용), 이름은 경로가 실어야 한다.

        ## 격리는 그대로다

        마지막 조각만 이름이고 **그 위는 여전히 서버가 발급한 식별자다** —
        ``<세션 디렉터리>/f_<hex>/<이름>``. 파일마다 자기 디렉터리를 가지므로 이름이
        겹쳐도 서로 덮지 않는다.

        그리고 이름을 그대로 믿지 않는다: `sanitize_display_name` 이 경로 구분자·상위
        참조·제어 문자를 이미 걷어내고, 아래 담김 검사가 **결과 경로가 그 디렉터리 안에
        있는지**를 다시 본다. 걸러 내기 하나에 의존하지 않는다 — 걸러 내기는 목록을
        빠뜨리면 뚫리고, 담김 검사는 빠뜨릴 목록이 없다.
        """
        file_id = f"f_{secrets.token_hex(8)}"
        # 파일마다 자기 디렉터리. 이 조각이 **서버가 발급한 식별자**다 (FR-337c).
        holder = self.directory / file_id
        holder.mkdir(parents=True, exist_ok=True)

        name = sanitize_display_name(display_name)
        path = holder / name
        resolved = path.resolve()
        if holder.resolve() not in resolved.parents:
            # 정리를 지나온 이름이 여기 걸릴 일은 없다. 걸리면 정리가 뚫린 것이므로
            # 저장하지 않고 식별자만으로 떨어진다 — 뚫린 채 쓰는 것보다 낫다.
            path = holder / file_id
            name = file_id

        path.write_bytes(data)
        entry = SessionFile(file_id, name, len(data), path)
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
