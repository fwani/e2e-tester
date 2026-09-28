"""023 보안 — 입력값 검증이 비밀번호를 새게 하지 않는다 (T047~T049 · FR-015~FR-017).

## 왜 이 파일이 따로 있는가

**입력값 검증은 기존 방어선을 우회하는 새 통로다.** 녹화는 비밀번호 칸에 넣은 값을 민감
변수 참조로 바꾸고, 정의는 민감 변수의 평문을 거절하고, 공유는 민감 값에 닿는 경로가
차단돼 있다. 그런데 **검증 Step 의 비교 값만 그 밖이었다** — 입력 Step 이 아니므로 위의
어느 규칙도 걸리지 않는다.

## 스크러버로는 닫히지 않는 칸이 있다

`Scrubber` 는 그 실행에서 **복호화된** 민감 값만 안다. 검증이 실패했다는 것은 관찰값이
기대값과 다르다는 뜻이고, 다르다는 것은 그 목록에 **없다**는 뜻이다 — 그래서 **검증이
실패할 때만 새는 구조**였다 (023 research R2). 그 문장은 실행 결과와 작성 시점 어긋남
기록에 그대로 저장된다.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from fastapi.testclient import TestClient

PASSWORD_FIELD = "#password"
TYPED_PASSWORD = "wrong-pass-typed-by-user"  # noqa: S105 - 고정 대상에 넣는 더미 값


def _session(client: TestClient, fixture_app: str) -> str:
    resp = client.post(
        "/api/sessions",
        json={"mode": "record", "start_url": f"{fixture_app}/login.html"},
    )
    assert resp.status_code == 201, resp.text
    return str(resp.json()["session_id"])


def _stop(client: TestClient, sid: str) -> None:
    client.post(f"/api/sessions/{sid}/stop")


def _page(client: TestClient, sid: str) -> Any:
    return client.app.state.itb.sessions.require(sid).tabs[0].page


def _type_password(client: TestClient, sid: str) -> None:
    page = _page(client, sid)

    async def act() -> None:
        await page.wait_for_selector(PASSWORD_FIELD)
        await page.fill(PASSWORD_FIELD, TYPED_PASSWORD)
        await asyncio.sleep(0.5)

    client.portal.call(act)  # type: ignore[attr-defined]
    resp = client.post(f"/api/sessions/{sid}/pause")
    assert resp.status_code in (200, 204, 409), resp.text


def _add(client: TestClient, sid: str, value: str) -> Any:
    return client.post(
        f"/api/sessions/{sid}/assertions",
        json={"kind": "value", "target_selector": PASSWORD_FIELD, "value": value},
    )


# ── 작성 시점 거절 (T047) ───────────────────────────────────────────────────


@pytest.mark.usefixtures("fixture_app")
@pytest.mark.parametrize(
    ("value", "why"),
    [
        ("hunter2", "평문"),
        ("{{USERNAME}}", "민감하지 않은 변수 참조 — 정의 파일에 값이 남는다"),
        ("{{SECRET_PW}} 뒤에 평문", "참조와 평문이 섞였다"),
    ],
)
def test_plaintext_comparison_on_a_password_field_is_refused(
    keyed_client: TestClient, fixture_app: str, value: str, why: str
) -> None:
    """비밀번호 칸의 비교 값은 **민감 변수 참조로만** 쓸 수 있다 (FR-015).

    둘째 줄이 판단이 필요한 칸이다 — **참조라는 형식이 아니라 민감한지가 기준이다.**
    민감하지 않은 변수는 정의 파일에 값을 가지므로, 그것으로 비교하면 평문을 적은 것과
    결과가 같다.
    """
    sid = _session(keyed_client, fixture_app)
    try:
        _type_password(keyed_client, sid)
        resp = _add(keyed_client, sid, value)
        assert resp.status_code == 400, f"{why} 인데 통과했다: {resp.text}"
        assert "SECRET_" in resp.text, f"이름 규약을 알려 주지 않는다: {resp.text}"
    finally:
        _stop(keyed_client, sid)


@pytest.mark.usefixtures("fixture_app")
def test_sensitive_reference_is_accepted(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """민감 변수 참조는 받아들여진다 — 막는 것은 대상이 아니라 *평문 값*이다."""
    sid = _session(keyed_client, fixture_app)
    try:
        _type_password(keyed_client, sid)
        put = keyed_client.put("/api/secrets/SECRET_PW", json={"value": "expected-pass"})
        assert put.status_code in (200, 201, 204), put.text

        resp = _add(keyed_client, sid, "{{SECRET_PW}}")
        assert resp.status_code == 200, resp.text
    finally:
        _stop(keyed_client, sid)


# ── 실패해도 새지 않는다 (T048) ─────────────────────────────────────────────


@pytest.mark.usefixtures("fixture_app")
def test_failed_comparison_does_not_leak_the_typed_value(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """**스크러버로는 닫히지 않는 칸** (FR-016 · research R2).

    칸에 든 값과 기대값이 다르므로 검증은 실패한다. 그 관찰값은 **복호화된 민감 값 목록에
    없으므로** 스크러버가 지우지 못한다 — 검증이 실패할 때만 새는 구조였다.

    **재실행으로 본다.** 화면 폼 경로는 Step 을 만들 뿐 검증을 돌리지 않는다 — 작성 시점
    어긋남 기록(020)은 AI 작성 경로의 것이다.
    """
    from us2_support import replay, result_of

    sid = _session(keyed_client, fixture_app)
    try:
        _type_password(keyed_client, sid)
        resp = _add(keyed_client, sid, "{{SECRET_PW}}")
        assert resp.status_code == 200, resp.text
        saved = keyed_client.post(f"/api/sessions/{sid}/save", json={"name": "비밀번호"})
        assert saved.status_code == 200, saved.text
        test_id = str(saved.json()["id"])
    finally:
        _stop(keyed_client, sid)

    # 재실행이 칸에 넣는 값과 기대값을 **다르게** 둔다. 그래야 검증이 실패하고, 실패해야
    # 관찰값이 설명에 실린다 — 이 검증이 보려는 것이 바로 그 자리다.
    for name, value in _required_secrets(keyed_client, test_id, TYPED_PASSWORD):
        put = keyed_client.put(f"/api/secrets/{name}", json={"value": value})
        assert put.status_code in (200, 201, 204), put.text
    put = keyed_client.put(
        "/api/secrets/SECRET_PW", json={"value": "something-else-entirely"}
    )
    assert put.status_code in (200, 201, 204), put.text

    replay(keyed_client, test_id)
    result = result_of(keyed_client, test_id)
    checks = [s for s in result["steps"] if s["label"].startswith("입력값이")]
    assert checks, f"검증 Step 결과가 없다: {[s['label'] for s in result['steps']]}"

    # 판정은 그대로여야 한다 — 가렸다고 통과로 바뀌면 검증이 무의미해진다.
    assert checks[0]["outcome"] == "fail", "값이 다른데 통과했다 — 마스킹이 판정을 바꿨다"

    message = checks[0].get("error_message") or ""
    assert TYPED_PASSWORD not in message, f"칸에 입력한 값이 설명에 남았다: {message}"
    assert "*" in message, f"관찰값이 가려지지 않았다: {message}"
    assert TYPED_PASSWORD not in str(result), "실행 결과 어딘가에 평문이 남았다"


@pytest.mark.usefixtures("fixture_app")
def test_saved_definition_has_no_plaintext(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """저장된 파일 어디에도 평문이 없다 (FR-017).

    quickstart §6-3 의 `grep` 을 기계로 옮긴 것이다 — 사람이 매번 확인할 수 없다.
    """
    sid = _session(keyed_client, fixture_app)
    try:
        _type_password(keyed_client, sid)
        put = keyed_client.put("/api/secrets/SECRET_PW", json={"value": TYPED_PASSWORD})
        assert put.status_code in (200, 201, 204), put.text
        resp = _add(keyed_client, sid, "{{SECRET_PW}}")
        assert resp.status_code == 200, resp.text
        saved = keyed_client.post(f"/api/sessions/{sid}/save", json={"name": "비밀번호 확인"})
        assert saved.status_code == 200, saved.text
    finally:
        _stop(keyed_client, sid)

    root = keyed_client.app.state.itb.project_root
    offenders = [
        str(path)
        for path in root.rglob("*")
        if path.is_file()
        and path.suffix in {".yaml", ".yml", ".json", ".md"}
        and TYPED_PASSWORD in path.read_text(encoding="utf-8", errors="ignore")
    ]
    assert not offenders, f"평문이 남은 파일: {offenders}"


def _required_secrets(
    client: TestClient, test_id: str, value: str
) -> list[tuple[str, str]]:
    """재실행이 요구하는 민감 변수와 채울 값. 녹화가 만든 것들이다."""
    resp = client.post("/api/sessions", json={"mode": "replay", "test_id": test_id})
    if resp.status_code == 201:
        client.post(f"/api/sessions/{resp.json()['session_id']}/stop")
        return []
    detail = (resp.json().get("error") or {}).get("detail") or {}
    return [(str(n), value) for n in (detail.get("missing") or []) if n != "SECRET_PW"]
