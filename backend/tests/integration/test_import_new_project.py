"""엑셀에서 새 프로젝트를 만들며 가져온다 (014 T044 · FR-014a·b·c).

**만들다 만 프로젝트를 남기지 않는다.** 가져오기가 실패하면 방금 만든 프로젝트가 사라져야
한다 — 남으면 사용자는 빈 프로젝트가 왜 생겼는지 알 수 없고, 다시 시도할 때 이름이 겹친다.
"""

from __future__ import annotations

from excel_support import build_xlsx, draft_write_fails, row, upload
from fastapi.testclient import TestClient

ENDPOINT = "/api/import/create-project"


def plan_id_for(client: TestClient, sheets: dict[str, list[list[object]]]) -> str:
    resp = upload(client, build_xlsx(sheets))
    assert resp.status_code == 200, resp.text
    return resp.json()["plan_id"]


def create(client: TestClient, plan_id: str, **over: object) -> object:
    body: dict[str, object] = {
        "plan_id": plan_id,
        "name": "가져온 프로젝트",
        "default_start_url": "https://example.internal",
    }
    body.update(over)
    return client.post(ENDPOINT, json=body)


class SuccessTests:
    def test_프로젝트와_그룹과_초안을_한꺼번에_만든다(self, client: TestClient) -> None:
        pid = plan_id_for(
            client, {"회원": [row("USER-001", "로그인"), row("USER-002", "로그아웃")]}
        )
        resp = create(client, pid)
        assert resp.status_code == 201, resp.text

        body = resp.json()
        assert body["project"]["name"] == "가져온 프로젝트"
        assert body["created_groups"] == [{"prefix": "USER", "name": "회원"}]
        assert len(body["drafts"]) == 2

    def test_만든_프로젝트가_열린_상태가_된다(self, client: TestClient) -> None:
        pid = plan_id_for(client, {"회원": [row("USER-001", "가")]})
        create(client, pid)
        assert client.get("/api/project").json()["name"] == "가져온 프로젝트"

    def test_레지스트리에_등록된다(self, client: TestClient) -> None:
        pid = plan_id_for(client, {"회원": [row("USER-001", "가")]})
        create(client, pid)
        names = [p["name"] for p in client.get("/api/project/list").json()["projects"]]
        assert "가져온 프로젝트" in names

    def test_초안이_새_프로젝트_안에_있다(self, client: TestClient) -> None:
        pid = plan_id_for(client, {"회원": [row("USER-001", "로그인")]})
        create(client, pid)
        drafts = client.get("/api/drafts").json()
        assert drafts["count"] == 1
        assert drafts["drafts"][0]["name"] == "로그인"

    def test_시작_URL_이_프로젝트에_들어간다(self, client: TestClient) -> None:
        pid = plan_id_for(client, {"회원": [row("USER-001", "가")]})
        create(client, pid, default_start_url="https://target.internal/login")
        assert (
            client.get("/api/project").json()["default_start_url"]
            == "https://target.internal/login"
        )

    def test_여러_시트가_여러_그룹이_된다(self, client: TestClient) -> None:
        pid = plan_id_for(
            client,
            {"회원": [row("USER-001", "가")], "데이터": [row("DATA-002", "나")]},
        )
        body = create(client, pid).json()
        assert {g["prefix"] for g in body["created_groups"]} == {"USER", "DATA"}

    def test_사용자가_준_접두어를_쓴다(self, client: TestClient) -> None:
        pid = plan_id_for(client, {"데이터관리": [row(None, "조회")]})
        body = create(client, pid, prefixes={"데이터관리": "DATA"}).json()
        assert body["created_groups"] == [{"prefix": "DATA", "name": "데이터관리"}]
        assert len(body["drafts"]) == 1


class RollbackTests:
    def test_초안_쓰기가_실패하면_프로젝트가_남지_않는다(self, client: TestClient) -> None:
        before = [p["name"] for p in client.get("/api/project/list").json()["projects"]]
        pid = plan_id_for(client, {"회원": [row("USER-001", "가")]})

        with draft_write_fails():
            resp = create(client, pid)

        assert resp.status_code == 500, resp.text
        after = [p["name"] for p in client.get("/api/project/list").json()["projects"]]
        assert after == before

    def test_실패하면_열린_프로젝트가_되지_않는다(self, client: TestClient) -> None:
        pid = plan_id_for(client, {"회원": [row("USER-001", "가")]})

        with draft_write_fails():
            create(client, pid)

        assert client.get("/api/project").status_code == 404

    def test_실패_사유가_정리_실패로_가려지지_않는다(self, client: TestClient) -> None:
        # 사용자가 알아야 하는 것은 가져오기가 왜 실패했는가이지, 정리가 왜 실패했는가가
        # 아니다.
        pid = plan_id_for(client, {"회원": [row("USER-001", "가")]})

        with draft_write_fails():
            body = create(client, pid).json()["error"]

        assert body["code"] in ("IMPORT_FAILED", "IMPORT_PARTIAL")


class ValidationTests:
    def test_없는_계획을_거절한다(self, client: TestClient) -> None:
        resp = create(client, "pl_deadbeef")
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "IMPORT_PLAN_NOT_FOUND"

    def test_거절되면_프로젝트를_만들지_않는다(self, client: TestClient) -> None:
        before = client.get("/api/project/list").json()["projects"]
        create(client, "pl_deadbeef")
        assert client.get("/api/project/list").json()["projects"] == before

    def test_이름이_비면_거절한다(self, client: TestClient) -> None:
        pid = plan_id_for(client, {"회원": [row("USER-001", "가")]})
        assert create(client, pid, name="").status_code == 422

    def test_잘못된_접두어를_거절한다(self, client: TestClient) -> None:
        pid = plan_id_for(client, {"데이터관리": [row(None, "조회")]})
        resp = create(client, pid, prefixes={"데이터관리": "TC"})
        assert resp.status_code == 400
        assert resp.json()["error"]["code"] == "GROUP_PREFIX_RESERVED"

    def test_접두어_거절_시에도_프로젝트를_만들지_않는다(self, client: TestClient) -> None:
        # 접두어 검사는 **프로젝트를 만들기 전에** 한다. 만들고 나서 거절하면 되돌릴
        # 것이 생긴다.
        before = client.get("/api/project/list").json()["projects"]
        pid = plan_id_for(client, {"데이터관리": [row(None, "조회")]})
        create(client, pid, prefixes={"데이터관리": "TC"})
        assert client.get("/api/project/list").json()["projects"] == before
