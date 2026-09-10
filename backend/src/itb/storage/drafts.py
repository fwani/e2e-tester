"""초안 저장소 (기능 014).

초안은 **우리 자산이고 우리 형식(YAML)** 이다. 그래서 남의 형식을 다루는
:mod:`itb.portability` 가 아니라 여기 산다.

배치:

.. code-block:: text

    <프로젝트>/
    ├── itb-project.yaml
    ├── tests/TC-001-....yaml        ← 테스트 (정본)
    ├── drafts/D-0001-로그인.yaml     ← 초안
    └── .runs/                        ← 실행 결과 (gitignore)

`tests/` 와 디렉터리를 나눈 이유는 두 가지다.

**첫째, 벽이 파일시스템이 된다.** 같은 디렉터리에 두면
:data:`itb.storage.repository._TEST_FILE_RE` 하나가 초안과 테스트를 가르는 유일한 벽이 되고,
그 정규식이 언젠가 느슨해지면 초안이 테스트 목록에 나타난다 (FR-027).

**둘째, 파일 하나에 몰지 않는다.** 초안 999개 × (절차 2,000자 + 기대결과 2,000자)는
:data:`itb.storage.yaml_io.MAX_FILE_BYTES`(4MB)를 넘긴다. 한 파일에 담으려면 그 상한을 이
기능 때문에 올려야 하고, 그러면 "정의 파일 하나가 4MB 를 넘으면 이상하다"는 기존 판단이
무너진다.

초안은 **버전 관리 대상이다** (FR-028). 프로젝트 생성 시 쓰는 `.gitignore` 템플릿을 건드리지
않으면 자동으로 그렇게 된다 — `.runs/` 와 `secrets.local.yaml` 만 무시 대상이다.
"""

from __future__ import annotations

import pathlib
import re

from itb.domain.draft import (
    DRAFT_ID_PATTERN,
    MAX_DRAFT_NUMBER,
    Draft,
    draft_number,
    format_draft_id,
)
from itb.storage.yaml_io import DefinitionError, dump_model, load_model

DRAFTS_DIR = "drafts"

_DRAFT_FILE_RE = re.compile(r"^(?P<id>D-(?P<number>\d{4}))-.*\.yaml$")
"""초안 파일 이름 = ``<식별자>-<이름 slug>.yaml``.

:func:`list_draft_paths` 와 :func:`allocate_draft_id` 가 **같은 것을 본다.** 파일 이름에서
식별자를 읽는 방법이 두 곳에서 갈리면, 목록에는 보이는데 번호는 비어 있다고 판단하는 상태가
생긴다 — 테스트 쪽이 이미 같은 이유로 정규식을 하나만 둔다.
"""

DRAFT_ID_RE = re.compile(DRAFT_ID_PATTERN)


class DraftError(Exception):
    """초안을 읽거나 쓰지 못했다."""


class DraftNotFoundError(DraftError):
    """지정한 초안이 없다.

    "없다" 와 "읽을 수 없다" 를 구분한다 — 후자는 :class:`DefinitionError` 로 올라간다.
    손상된 파일을 없는 것처럼 보고하면 사용자는 방금 만든 초안이 사라진 줄 안다.
    """


class DraftStore:
    """한 프로젝트의 초안들.

    :class:`itb.storage.repository.ProjectRepository` 가 이것을 들고 있다. 저장소를 따로 둔
    이유는 초안이 테스트와 **다른 생명주기**를 갖기 때문이다 — 초안은 저장되는 순간 사라지고,
    번호를 예약하지 않으며, 실행 결과를 갖지 않는다.
    """

    def __init__(self, root: pathlib.Path) -> None:
        self._root = root

    @property
    def dir(self) -> pathlib.Path:
        return self._root / DRAFTS_DIR

    # ─── 읽기 ────────────────────────────────────────────────────────────

    def list_paths(self) -> list[pathlib.Path]:
        """초안 파일 경로들. 이름 순으로 정렬한다.

        디렉터리가 없으면 빈 목록이다 — 초안을 한 번도 만들지 않은 프로젝트가 정상이므로
        없는 것을 오류로 다루지 않는다.
        """
        if not self.dir.is_dir():
            return []
        return sorted(p for p in self.dir.glob("*.yaml") if _DRAFT_FILE_RE.match(p.name))

    def find_path(self, draft_id: str) -> pathlib.Path | None:
        """식별자로 파일을 찾는다. 이름 slug 를 모르므로 훑어서 찾는다."""
        for p in self.list_paths():
            m = _DRAFT_FILE_RE.match(p.name)
            if m is not None and m.group("id") == draft_id:
                return p
        return None

    def list_all(self) -> tuple[list[Draft], list[str]]:
        """모든 초안과, 읽지 못한 파일의 사유를 함께 돌려준다.

        읽을 수 없는 파일 하나 때문에 목록 전체가 사라지면 안 된다 — `GET /api/tests` 가
        ``problems`` 로 같은 일을 한다. 사용자는 나머지를 계속 쓸 수 있어야 한다.
        """
        drafts: list[Draft] = []
        problems: list[str] = []
        for p in self.list_paths():
            try:
                drafts.append(load_model(p, Draft))
            except DefinitionError as exc:
                problems.append(str(exc))
        drafts.sort(key=lambda d: d.draft_id)
        return drafts, problems

    def read(self, draft_id: str) -> Draft:
        """초안 하나. 없으면 :class:`DraftNotFoundError`."""
        path = self.find_path(draft_id)
        if path is None:
            msg = f"초안을 찾을 수 없습니다: {draft_id}"
            raise DraftNotFoundError(msg)
        return load_model(path, Draft)

    def count(self) -> int:
        """초안 수. 파일을 열지 않고 이름만 센다 — 목록 화면이 자주 묻는다."""
        return len(self.list_paths())

    # ─── 쓰기 ────────────────────────────────────────────────────────────

    def path_for(self, draft: Draft) -> pathlib.Path:
        from itb.storage.repository import slugify

        return self.dir / f"{draft.draft_id}-{slugify(draft.name)}.yaml"

    def write(self, draft: Draft) -> pathlib.Path:
        """초안을 쓴다. 이름이 바뀌어 파일명이 달라지면 옛 파일을 지운다."""
        self.dir.mkdir(parents=True, exist_ok=True)
        target = self.path_for(draft)
        previous = self.find_path(draft.draft_id)
        dump_model(target, draft)
        if previous is not None and previous != target:
            previous.unlink(missing_ok=True)
        return target

    def delete(self, draft_id: str) -> None:
        """초안을 지운다. 없으면 :class:`DraftNotFoundError`.

        휴지통으로 보내지 않는다 — 초안은 스텝도 실행 결과도 없는 몇 줄의 글이고, 원본
        스프레드시트가 남아 있다. 테스트 삭제를 휴지통 이동으로 만든 판단(013)이 여기에는
        해당하지 않는다.
        """
        path = self.find_path(draft_id)
        if path is None:
            msg = f"초안을 찾을 수 없습니다: {draft_id}"
            raise DraftNotFoundError(msg)
        path.unlink()

    def allocate_id(self, *, taken: set[str] | None = None) -> str:
        """비어 있는 초안 식별자 하나.

        `taken` 은 아직 디스크에 없지만 이번 일괄 작업이 쓰기로 한 식별자들이다. 가져오기는
        초안 수십 개를 한꺼번에 만들므로, 디스크만 보면 전부 같은 번호를 받는다.
        """
        used = {
            int(m.group("number"))
            for p in self.list_paths()
            if (m := _DRAFT_FILE_RE.match(p.name)) is not None
        }
        if taken:
            used |= {draft_number(t) for t in taken}

        number = 1
        while number in used:
            number += 1
        if number > MAX_DRAFT_NUMBER:
            msg = f"초안이 {MAX_DRAFT_NUMBER}개를 넘었습니다. 먼저 녹화하거나 정리하세요."
            raise DraftError(msg)
        return format_draft_id(number)
