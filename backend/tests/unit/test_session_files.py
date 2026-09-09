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

    """2026-09-09 — **재는 것이 한 겹 옮겨졌다** (사용자 보고).

    이전 단언은 「저장 경로는 식별자 하나다. 이름의 어떤 조각도 들어가지 않는다」였다.
    대상 브라우저가 받는 파일 이름이 경로의 마지막 조각이라는 사실 때문에 그 배치로는
    확장자를 전달할 수 없었다 (`SessionFileStore.add` 의 주석).

    그래서 이름은 **마지막 조각에만** 온다. 재는 것은 여전히 같다 — 「이름이 경로를
    벗어날 수 없다」. 방법이 「이름을 아예 안 쓴다」에서 「이름을 한 조각에 가두고 담김을
    확인한다」로 바뀌었다.
    """
    # 이름이 들어오는 조각은 **마지막 하나**이고, 그 위는 서버가 발급한 식별자다.
    assert entry.path.parent.name == entry.file_id
    assert entry.path.parent.parent == store.directory
    # 이름 조각에 경로 구분자·상위 참조가 남지 않는다.
    assert "/" not in entry.path.name
    assert "\\" not in entry.path.name
    assert entry.path.name not in (".", "..")
    # 뿌리 밖으로 나가지 않는다 — 담김 검사가 `add` 안에도 있다.
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


# ─── T090 FR-337b: 기동이 남은 것을 정리한다 ────────────────────────────────


def test_startup_sweeps_leftovers() -> None:
    """**기동이 이전 실행의 잔여를 지운다** (FR-337b · T090).

    정상 종료 경로는 세션마다 지운다. 프로세스가 죽으면 그 경로가 돌지 않으므로 사용자가
    보낸 파일이 기계에 쌓인다 — 「세션보다 오래 남지 않는다」가 깨지는 유일한 자리다.

    `sweep_orphans` 가 **정의만 되고 불리지 않던 것**이 converge 1회차의 발견이었다.
    이 검증은 기동 경로가 실제로 그것을 부르는지를 본다.
    """
    from itb.api.app import _sweep_session_files

    leftover = sf.SessionFileStore("죽은-세션")
    entry = leftover.add("a.txt", b"x")
    assert entry.path.is_file()

    _sweep_session_files()

    assert not entry.path.exists(), "기동이 잔여 파일을 지우지 않았다"


def test_startup_sweep_never_blocks_boot() -> None:
    """정리가 실패해도 기동이 멈추지 않는다.

    정리는 위생이지 기능이 아니다. 여기서 터지면 제품이 아예 뜨지 못하고, 그 실패는
    원인이 파일 정리라는 것을 드러내지 않는다.
    """
    import itb.api.app as app_module
    from itb.api.app import _sweep_session_files

    def boom(_active: set[str]) -> int:
        msg = "정리가 터졌다"
        raise OSError(msg)

    original = app_module.sweep_orphans
    app_module.sweep_orphans = boom  # type: ignore[assignment]
    try:
        _sweep_session_files()  # 예외가 새면 여기서 터진다
    finally:
        app_module.sweep_orphans = original  # type: ignore[assignment]


# ─── 확장자가 대상 페이지까지 간다 (2026-09-09 사용자 보고) ──────────────────


class ExtensionSurvivesTests:
    """「파일 이름 에 확장자가 포함되어야한다」.

    ## 왜 이것이 검사할 값인가

    사용자가 든 이유는 「실제 서비스에서는 확장자를 보는경우가 있기 때문」이다. 확장자가
    없으면 그 서비스는 업로드를 거절하고, 그 실패는 ITB 의 결함으로 보이지 않는다 —
    사용자는 자기 파일이 잘못됐다고 생각한다.

    **대상 브라우저가 받는 이름은 경로의 마지막 조각이다.** 저장이 이름을 버리면 그 뒤의
    어떤 코드도 이름을 되살릴 수 없으므로, 재는 자리는 저장이다.
    """

    def test_the_stored_path_ends_with_the_file_name(self) -> None:
        store = sf.SessionFileStore("s1")
        entry = store.add(sf.sanitize_display_name("보고서.xlsx"), b"x")

        assert entry.path.name == "보고서.xlsx"
        assert entry.display_name == "보고서.xlsx"
        # 이것이 결함의 형태였다 — 경로가 식별자로 끝나면 확장자가 사라진다.
        assert entry.path.name != entry.file_id

    def test_names_that_lose_their_letters_keep_the_extension(self) -> None:
        """허용 문자 밖의 이름도 **확장자는 남는다.**

        ``報告.xlsx`` 는 줄기가 통째로 정리되지만 확장자는 이 기능의 핵심 정보다.
        이전 판은 줄기가 ``-`` 가 된 뒤 마지막 `strip("-. ")` 이 앞의 ``-.`` 를 함께 떼어
        **``xlsx``** 만 남겼다 — 이름이 확장자였던 것이 되고 확장자는 사라졌다.
        """
        assert sf.sanitize_display_name("報告.xlsx") == "file.xlsx"
        assert sf.sanitize_display_name("報告書.tar.gz").endswith(".gz")

    def test_a_long_name_never_loses_the_extension(self) -> None:
        """길이 상한이 확장자를 자르지 않는다.

        잘린 확장자(``.xls``)는 없는 확장자보다 나쁘다 — 엉뚱한 유형으로 읽히고, 그것은
        조용히 다른 검증을 통과하거나 실패한다.
        """
        name = sf.sanitize_display_name("가" * 300 + ".xlsx")
        assert name.endswith(".xlsx")
        assert len(name) <= sf.MAX_DISPLAY_NAME

    def test_files_with_the_same_name_do_not_overwrite_each_other(self) -> None:
        """이름이 경로에 들어오면 겹침을 생각해야 한다.

        파일마다 자기 디렉터리(`f_<hex>`)를 가지므로 같은 이름을 두 번 올려도 서로 덮지
        않는다. 덮으면 먼저 올린 파일을 가리키는 식별자가 다른 내용을 돌려준다.
        """
        store = sf.SessionFileStore("s1")
        first = store.add(sf.sanitize_display_name("같은.csv"), b"first")
        second = store.add(sf.sanitize_display_name("같은.csv"), b"second")

        assert first.file_id != second.file_id
        assert first.path != second.path
        assert first.path.read_bytes() == b"first"
        assert second.path.read_bytes() == b"second"

    def test_cleanup_still_removes_everything(self) -> None:
        """디렉터리가 한 겹 깊어졌어도 정리는 그대로다 (FR-337b)."""
        store = sf.SessionFileStore("s1")
        entry = store.add(sf.sanitize_display_name("보고서.xlsx"), b"x")
        assert entry.path.is_file()

        store.cleanup()

        assert not entry.path.exists()
        assert not store.directory.exists()
