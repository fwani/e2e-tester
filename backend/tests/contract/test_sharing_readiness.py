"""019 T059 (C8·C13) — 실행 전 차단 (FR-044 · contracts §6·§7).

**브라우저를 띄우기 전에 막는다.** 예전에는 그 스텝에 도달해서야 실패했고, 공유받은
테스트를 처음 돌리는 사람은 자기 환경 문제인지 테스트 문제인지 구분할 수 없었다.

세션이 **만들어지지 않는다**는 것이 이 파일의 핵심 단언이다. 만들어졌다 실패하면 빈 세션이
남고, 원칙 III 가 세션을 살려 두라고 요구하므로 그것이 치워지지 않는다.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sharing_support import make_secret_test, make_test, seal_secret, write_tests

READINESS = "/api/tests/TC-001/readiness"


class ReadinessEndpointTests:
    def test_민감_값이_없으면_실행할_수_없다고_말한다(self, keyed_client: TestClient) -> None:
        write_tests(keyed_client, make_secret_test())
        body = keyed_client.get(READINESS).json()
        assert body["runnable"] is False
        assert body["missing_secrets"] == ["SECRET_LOGIN_PW"]

    def test_값을_채우면_실행할_수_있다(self, keyed_client: TestClient) -> None:
        write_tests(keyed_client, make_secret_test())
        seal_secret(keyed_client, "SECRET_LOGIN_PW")
        body = keyed_client.get(READINESS).json()
        assert body["runnable"] is True
        assert body["missing_secrets"] == []

    def test_빈_비민감_변수는_막지_않는다(self, keyed_client: TestClient) -> None:
        """C13 — 빈 문자열이 유효한 입력일 수 있다 (FR-044)."""
        write_tests(keyed_client, make_secret_test(plain_name="LOGIN_ID"))
        seal_secret(keyed_client, "SECRET_LOGIN_PW")
        body = keyed_client.get(READINESS).json()
        assert body["empty_variables"] == ["LOGIN_ID"]
        assert body["runnable"] is True

    def test_키가_없으면_그_사실을_알린다(self, project_client: TestClient) -> None:
        """값을 채우려면 키가 먼저 있어야 한다 (FR-045)."""
        write_tests(project_client, make_secret_test())
        body = project_client.get(READINESS).json()
        assert body["key_available"] is False
        assert body["runnable"] is False

    def test_민감_변수가_없는_테스트는_언제나_실행_가능하다(
        self, project_client: TestClient
    ) -> None:
        write_tests(project_client, make_test("TC-001", "평범"))
        assert project_client.get(READINESS).json()["runnable"] is True

    def test_없는_테스트는_404(self, project_client: TestClient) -> None:
        resp = project_client.get("/api/tests/TC-999/readiness")
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "TEST_NOT_FOUND"


class SessionGuardTests:
    """C8 — 세션 생성이 막힌다. **브라우저가 뜨지 않는다.**"""

    def _replay(self, client: TestClient) -> object:
        return client.post("/api/sessions", json={"mode": "replay", "test_id": "TC-001"})

    def test_값이_비면_세션을_만들지_않는다(self, keyed_client: TestClient) -> None:
        write_tests(keyed_client, make_secret_test())
        resp = self._replay(keyed_client)
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "SECRET_VALUE_MISSING"

    def test_어느_변수인지_알려준다(self, keyed_client: TestClient) -> None:
        write_tests(keyed_client, make_secret_test())
        detail = self._replay(keyed_client).json()["error"]["detail"]
        assert detail["missing"] == ["SECRET_LOGIN_PW"]
        assert detail["test_id"] == "TC-001"

    def test_막힌_뒤_살아_있는_세션이_없다(self, keyed_client: TestClient) -> None:
        """만들어졌다 실패하면 빈 세션이 남는다. 그것이 이 차단의 요점이다."""
        write_tests(keyed_client, make_secret_test())
        self._replay(keyed_client)
        assert keyed_client.get("/api/sessions").json()["sessions"] == []

    def test_재녹화도_같이_막는다(self, keyed_client: TestClient) -> None:
        """`rerecord` 도 앞 스텝을 재생하므로 같은 값이 필요하다 (analyze F3)."""
        write_tests(keyed_client, make_secret_test())
        resp = keyed_client.post(
            "/api/sessions",
            json={"mode": "rerecord", "test_id": "TC-001", "rerecord_step_ids": ["step-01"]},
        )
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "SECRET_VALUE_MISSING"

    def test_빈_비민감_변수만_있으면_막지_않는다(self, keyed_client: TestClient) -> None:
        """C13 — 이 경우 세션 생성이 이 검사에 걸리지 않아야 한다."""
        write_tests(keyed_client, make_secret_test(plain_name="LOGIN_ID"))
        seal_secret(keyed_client, "SECRET_LOGIN_PW")
        resp = self._replay(keyed_client)
        assert resp.json().get("error", {}).get("code") != "SECRET_VALUE_MISSING"

    def test_새로_만들기는_막지_않는다(self, keyed_client: TestClient) -> None:
        """`record`·AI 작성은 값을 **만드는** 중이므로 없는 것이 정상이다."""
        write_tests(keyed_client, make_secret_test())
        resp = keyed_client.post(
            "/api/sessions", json={"mode": "record", "start_url": "https://example.internal"}
        )
        assert resp.json().get("error", {}).get("code") != "SECRET_VALUE_MISSING"
