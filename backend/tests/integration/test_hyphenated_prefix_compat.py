"""028 — 하이픈 접두어가 모든 통로를 지난다. 하위 호환은 검증으로만 증명된다.

spec FR-009·FR-011·FR-012 · SC-002 · SC-007 · research R7.

028 은 접두어에 하이픈을 허용하면서 **식별자를 읽는 방법**을 바꿨다 — 앞에서 자르던
것을 뒤에서 자른다. 그 변경이 지나간 자리가 열일곱 곳이고, 그중 하나라도 옛 방식으로
남으면 `IT-PM-001` 의 소속을 `IT` 로 읽는다. 그 상태는 **사고가 나야 드러난다** —
목록에는 보이는데 번호는 비어 있다고 판단하거나, 그룹 해체가 없는 테스트를 옮기려 든다.

그래서 이 파일은 통로마다 하이픈 접두어를 한 번씩 지나가게 한다.

**마이그레이션을 두지 않는다는 결정의 근거도 여기 있다.** 옛 자산이 그대로 동작한다는
것은 주장이 아니라 아래의 단언이다.
"""

from __future__ import annotations

import io
import zipfile

import pytest
from excel_support import make_test, repo_of
from fastapi.testclient import TestClient

from itb.domain.test_case import prefix_of

HYPHENATED = "IT-PM"
OTHER = "IT-DM"


def make_group(client: TestClient, prefix: str, name: str) -> None:
    resp = client.post("/api/groups", json={"prefix": prefix, "name": name})
    assert resp.status_code == 201, resp.text


class HyphenatedPrefixTests:
    """하이픈 접두어가 그룹으로서 제구실을 한다 (FR-001 · SC-001)."""

    def test_하이픈_접두어로_그룹을_만든다(self, project_client: TestClient) -> None:
        make_group(project_client, HYPHENATED, "프로젝트 관리")
        groups = project_client.get("/api/groups").json()["groups"]
        assert [g["prefix"] for g in groups] == [HYPHENATED]

    def test_번호가_그룹마다_이어진다(self, project_client: TestClient) -> None:
        """`IT-PM-001` 다음이 `IT-PM-002` 다 — `IT-001` 로 새로 세지 않는다."""
        repo = repo_of(project_client)
        assert repo.allocate_test_id(HYPHENATED) == f"{HYPHENATED}-001"
        repo.write_test(make_test(f"{HYPHENATED}-001", "첫째"))
        assert repo.allocate_test_id(HYPHENATED) == f"{HYPHENATED}-002"

    def test_접두어가_비슷해도_섞이지_않는다(self, project_client: TestClient) -> None:
        """**`IT-PM` 과 `IT-DM` 은 앞 두 글자가 같다.**

        앞에서 자르던 옛 방식에서는 둘 다 `IT` 가 되어 **한 그룹으로 합쳐진다.** 이
        단언이 028 의 회귀를 가장 먼저 잡는다.
        """
        repo = repo_of(project_client)
        repo.write_test(make_test(f"{HYPHENATED}-001", "피엠"))
        repo.write_test(make_test(f"{OTHER}-001", "디엠"))

        assert repo.used_numbers(HYPHENATED) == {1}
        assert repo.used_numbers(OTHER) == {1}
        assert repo.used_numbers("IT") == set(), "`IT` 라는 그룹은 존재하지 않는다"

    def test_목록이_그룹별로_센다(self, project_client: TestClient) -> None:
        make_group(project_client, HYPHENATED, "프로젝트 관리")
        make_group(project_client, OTHER, "데이터 관리")
        repo = repo_of(project_client)
        repo.write_test(make_test(f"{HYPHENATED}-001", "피엠"))
        repo.write_test(make_test(f"{HYPHENATED}-002", "피엠 둘"))
        repo.write_test(make_test(f"{OTHER}-001", "디엠"))

        counts = {
            g["prefix"]: g["count"]
            for g in project_client.get("/api/groups").json()["groups"]
        }
        assert counts == {HYPHENATED: 2, OTHER: 1}

    def test_그룹으로_걸러_본다(self, project_client: TestClient) -> None:
        make_group(project_client, HYPHENATED, "프로젝트 관리")
        repo = repo_of(project_client)
        repo.write_test(make_test(f"{HYPHENATED}-001", "피엠"))
        repo.write_test(make_test("TC-001", "그룹 없는 것"))

        kept = project_client.get("/api/tests", params={"group": HYPHENATED}).json()["tests"]
        assert [t["id"] for t in kept] == [f"{HYPHENATED}-001"]


class GroupMoveTests:
    """자산을 옮기는 통로 (FR-009)."""

    def test_그룹으로_옮기면_식별자가_바뀐다(self, project_client: TestClient) -> None:
        make_group(project_client, HYPHENATED, "프로젝트 관리")
        repo = repo_of(project_client)
        repo.write_test(make_test("TC-001", "로그인"))

        resp = project_client.post(
            "/api/tests:move", json={"test_ids": ["TC-001"], "to_prefix": HYPHENATED}
        )
        assert resp.status_code == 200, resp.text
        assert [t["id"] for t in project_client.get("/api/tests").json()["tests"]] == [
            f"{HYPHENATED}-001"
        ]

    def test_그룹_해체가_그_안의_테스트를_되돌린다(self, project_client: TestClient) -> None:
        """**`groups.py` 가 파일 이름에서 식별자를 손으로 복원하고 있었다.**

        `split("-", 2)[0] + "-" + [1]` 은 `IT-PM-001-로그인.yaml` 에서 `IT-PM` 을 식별자로
        읽는다. 그런 테스트는 없으므로 해체가 통째로 실패한다 (research R3).
        """
        make_group(project_client, HYPHENATED, "프로젝트 관리")
        repo = repo_of(project_client)
        repo.write_test(make_test(f"{HYPHENATED}-001", "로그인"))

        resp = project_client.delete(f"/api/groups/{HYPHENATED}")
        assert resp.status_code == 200, resp.text
        # 응답은 **옮겨진 뒤**의 식별자를 담는다 — 사용자가 목록에서 찾을 이름이 그것이다.
        assert resp.json()["ungrouped"] == ["TC-001"]
        assert [t["id"] for t in project_client.get("/api/tests").json()["tests"]] == ["TC-001"]


class BackwardCompatibilityTests:
    """**마이그레이션이 없는 이유** (FR-011 · SC-002)."""

    def test_옛_자산이_그대로_읽힌다(self, project_client: TestClient) -> None:
        make_group(project_client, "USER", "사용자관리")
        repo = repo_of(project_client)
        repo.write_test(make_test("USER-001", "로그인"))
        repo.write_test(make_test("TC-014", "옛날 것"))

        ids = [t["id"] for t in project_client.get("/api/tests").json()["tests"]]
        assert set(ids) == {"USER-001", "TC-014"}
        assert repo.used_numbers("USER") == {1}
        assert prefix_of("USER-001") == "USER"

    def test_옛_접두어와_새_접두어가_한_프로젝트에_있는다(
        self, project_client: TestClient
    ) -> None:
        make_group(project_client, "USER", "사용자관리")
        make_group(project_client, HYPHENATED, "프로젝트 관리")
        repo = repo_of(project_client)
        repo.write_test(make_test("USER-001", "로그인"))
        repo.write_test(make_test(f"{HYPHENATED}-001", "피엠"))

        counts = {
            g["prefix"]: g["count"]
            for g in project_client.get("/api/groups").json()["groups"]
        }
        assert counts == {"USER": 1, HYPHENATED: 1}


class ExcelRoundTripTests:
    """엑셀 왕복 (SC-007)."""

    def test_하이픈_그룹이_시트가_된다(self, project_client: TestClient) -> None:
        make_group(project_client, HYPHENATED, "프로젝트 관리")
        repo = repo_of(project_client)
        repo.write_test(make_test(f"{HYPHENATED}-001", "로그인"))

        resp = project_client.get("/api/export")
        assert resp.status_code == 200, resp.text
        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
            assert "[Content_Types].xml" in zf.namelist()

    def test_내보낸_행이_하이픈_식별자를_싣는다(self, project_client: TestClient) -> None:
        from excel_support import read_back

        make_group(project_client, HYPHENATED, "프로젝트 관리")
        repo = repo_of(project_client)
        repo.write_test(make_test(f"{HYPHENATED}-001", "로그인"))

        sheets = read_back(project_client.get("/api/export").content)
        found = [
            cell
            for rows in sheets.values()
            for row in rows
            for cell in row
            if isinstance(cell, str) and cell.startswith(HYPHENATED)
        ]
        assert f"{HYPHENATED}-001" in found, f"시트에서 식별자를 찾지 못했다: {sheets}"


class SharingTests:
    """공유 묶음 (FR-012 · SC-007)."""

    def test_하이픈_그룹을_묶어_내보낸다(self, project_client: TestClient) -> None:
        make_group(project_client, HYPHENATED, "프로젝트 관리")
        repo = repo_of(project_client)
        repo.write_test(make_test(f"{HYPHENATED}-001", "로그인"))

        resp = project_client.post(
            "/api/share/export", json={"test_ids": [f"{HYPHENATED}-001"]}
        )
        assert resp.status_code in {200, 201}, resp.text


@pytest.mark.parametrize("bad", ["IT-", "-PM", "IT--PM", "IT-001", "ABCDEFGHIJKLM"])
def test_잘못된_접두어는_경계에서_막힌다(project_client: TestClient, bad: str) -> None:
    """헌법 §보안 — 모든 외부 입력은 경계에서 검증된다."""
    resp = project_client.post("/api/groups", json={"prefix": bad, "name": "아무개"})
    assert resp.status_code == 422, resp.text
