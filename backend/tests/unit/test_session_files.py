"""사용자가 보낸 파일 (010 T069·T070 · FR-337a~c · 헌법 보안 요건).

**이 파일이 지키는 것은 셋이다.**

1. **상한 없는 수신 경로를 두지 않는다** (FR-337a). 파일당 크기·세션당 개수. 넘으면
   자르지 않고 거절한다 — 잘린 파일을 대상 페이지가 받으면 그 실패는 원인을 드러내지 않는다.
2. **세션보다 오래 남지 않는다** (FR-337b). 사용자가 보낸 것이므로 그 수명이 세션의
   수명을 넘어서는 안 된다. 비정상 종료로 남은 것도 정리된다.
3. **파일 이름이 경로가 되지 않는다** (FR-337c). 경로는 서버가 발급한 식별자로 만든다 —
   경로 구분자·상위 참조가 이름에 들어와도 무해해지는 이유가 그것이다.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from itb.storage import session_files as sf
from itb.storage.paths import session_files_dir


@pytest.fixture(autouse=True)
def _isolated_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """저장소 뿌리를 임시 디렉터리로 옮긴다.

    실제 임시 디렉터리를 쓰면 검증이 개발자의 기계에 파일을 남긴다 — 그리고 그 파일은
    이 검증이 지키려는 「세션보다 오래 남지 않는다」를 스스로 어긴다.
    """
    monkeypatch.setenv("ITB_SESSION_FILES_DIR", str(tmp_path / "files"))


# ─── FR-337c: 이름이 경로가 되지 않는다 (T070) ──────────────────────────────


@pytest.mark.parametrize(
    "raw",
    [
        "../../etc/passwd",
        "..\\..\\windows\\system32\\config",
        "/etc/shadow",
        "....//....//secret",
        ".",
        "..",
        "",
        None,
    ],
)
def test_hostile_names_never_become_paths(raw: str | None) -> None:
    """**경로 구분자·상위 참조가 들어와도 무해하다** (FR-337c).

    막는 방법이 「위험한 이름을 걸러 내는 것」이 아니라 **「이름을 경로에 쓰지 않는 것」**
    이라는 게 요점이다. 걸러 내기는 목록을 빠뜨리면 뚫리고, 쓰지 않기는 빠뜨릴 목록이 없다.
    """
    store = sf.SessionFileStore("s1")
    entry = store.add(sf.sanitize_display_name(raw), b"x")

    # 저장 경로는 **식별자 하나**다. 이름의 어떤 조각도 들어가지 않는다.
    assert entry.path.name == entry.file_id
    assert entry.path.parent == store.directory
    # 뿌리 밖으로 나가지 않는다.
    assert store.directory.resolve() in entry.path.resolve().parents


@pytest.mark.parametrize(
    ("raw", "expect_not"),
    [("../../etc/passwd", "/"), ("a\\b\\c.txt", "\\"), ("x\x00y.txt", "\x00")],
)
def test_display_names_are_cleaned_for_showing(raw: str, expect_not: str) -> None:
    """표시 이름도 정리한다 — 이 값은 대상 브라우저와 화면에 간다 (FR-337c).

    경로에 쓰이지 않으므로 보안 경계는 아니다. 그래도 정리하는 이유는 제어 문자와 경로
    구분자가 표시하는 쪽마다 다르게 깨지고, 그 깨짐은 사용자가 무엇을 올렸는지 알 수
    없게 만들기 때문이다.
    """
    cleaned = sf.sanitize_display_name(raw)
    assert expect_not not in cleaned
    assert cleaned not in ("", ".", "..")


def test_display_names_keep_korean() -> None:
    """한글은 남긴다 — 사용자가 자기 파일을 알아볼 수 있어야 한다 (`slugify` 와 같은 판단)."""
    assert sf.sanitize_display_name("주문내역.csv") == "주문내역.csv"


def test_display_names_are_bounded() -> None:
    assert len(sf.sanitize_display_name("가" * 500)) <= sf.MAX_DISPLAY_NAME


# ─── FR-337a: 상한 (T069) ────────────────────────────────────────────────────


def test_product_limits_exist_and_are_bounded() -> None:
    """상한이 **있다.** 상한 없는 수신 경로를 두지 않는다 (FR-337a).

    값 자체보다 「있다」가 요점이므로 범위로 못 박는다 — 조정은 가능하되 없애지는
    못한다.
    """
    assert 0 < sf.MAX_FILE_BYTES <= 64 * 1024 * 1024
    assert 0 < sf.MAX_FILES_PER_SESSION <= 64


def test_the_channel_file_limit_matches_the_store_limit() -> None:
    """조작 채널의 개수 상한이 저장소의 것과 같다 (FR-337a).

    갈리면 사용자는 올릴 수 있는 만큼 지정하지 못하거나, 지정할 수 없는 것을 올린다 —
    어느 쪽이든 거절 사유가 사실과 어긋난다.
    """
    from itb.api.ws.control_channel import MAX_FILE_IDS

    assert MAX_FILE_IDS == sf.MAX_FILES_PER_SESSION


# ─── FR-337b: 세션보다 오래 남지 않는다 (T069) ──────────────────────────────


def test_cleanup_removes_the_session_directory() -> None:
    """세션이 끝나면 받은 파일이 사라진다 (FR-337b)."""
    store = sf.SessionFileStore("s1")
    entry = store.add("a.txt", b"hello")
    assert entry.path.is_file()

    store.cleanup()

    assert not entry.path.exists()
    assert not store.directory.exists()
    assert store.files == {}


def test_registry_drop_cleans_up() -> None:
    registry = sf.SessionFileRegistry()
    store = registry.store("s1")
    entry = store.add("a.txt", b"hello")

    registry.drop("s1")

    assert registry.get("s1") is None
    assert not entry.path.exists()


def test_sweep_removes_orphans_but_keeps_live_sessions() -> None:
    """**비정상 종료로 남은 것을 정리한다** (FR-337b).

    프로세스가 죽으면 `cleanup` 이 돌지 않는다. 다음 기동에서 뿌리를 훑어 활성 세션에
    속하지 않은 디렉터리를 지운다 — 그러지 않으면 사용자가 보낸 파일이 기계에 영원히
    쌓인다.
    """
    registry = sf.SessionFileRegistry()
    alive = registry.store("alive")
    alive.add("a.txt", b"x")
    dead = sf.SessionFileStore("dead")
    dead.add("b.txt", b"y")

    removed = sf.sweep_orphans({session_files_dir("alive").name})

    assert removed == 1
    assert alive.directory.exists(), "살아 있는 세션의 파일까지 지웠다"
    assert not dead.directory.exists()


def test_a_file_is_only_visible_to_its_own_session() -> None:
    """**다른 세션이 `fileId` 로 접근할 수 없다** (FR-340).

    격리가 검사가 아니라 **구조**로 성립한다 — 저장소가 세션 단위로 나뉘어 있으므로
    다른 세션의 사전에는 그 식별자가 아예 없다.
    """
    registry = sf.SessionFileRegistry()
    mine = registry.store("mine")
    entry = mine.add("a.txt", b"x")
    theirs = registry.store("theirs")

    assert mine.path_of(entry.file_id) is not None
    assert theirs.path_of(entry.file_id) is None


def test_a_deleted_file_is_not_returned() -> None:
    """디스크에서 사라진 파일은 조회되지 않는다.

    사전에만 남아 있는 식별자를 경로로 돌려주면, 대상 브라우저가 없는 파일을 지정하려다
    실패하고 그 실패는 원인을 드러내지 않는다.
    """
    store = sf.SessionFileStore("s1")
    entry = store.add("a.txt", b"x")
    entry.path.unlink()

    assert store.path_of(entry.file_id) is None
