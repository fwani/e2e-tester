"""023 US2 — 입력값 검증 (T034·T035·T047~T049).

## 이 파일이 확인하는 것

입력 칸을 대상으로 한 텍스트 검증은 **구조적으로 100% 실패한다.** 값이 텍스트 노드가
아니기 때문이다. 그 고장이 실제로 그러한지, 그리고 새 종류가 그것을 고치는지 본다.

**§비밀번호 묶음이 가장 중요하다.** 이 기능이 만드는 유일한 새 위험이고, 기존 스크러버로는
닫히지 않는 칸이다 — 스크러버는 그 실행에서 복호화된 값만 알고, 검증이 실패했다는 것은
관찰값이 그 목록에 **없다**는 뜻이다 (023 research R2).
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from fastapi.testclient import TestClient

NAME_FIELD = "#memo"
SELECT_FIELD = "#kind"
HIDDEN_FIELD = "#hidden-value"


def _session(client: TestClient, fixture_app: str) -> str:
    resp = client.post(
        "/api/sessions",
        json={"mode": "record", "start_url": f"{fixture_app}/interactions.html"},
    )
    assert resp.status_code == 201, resp.text
    return str(resp.json()["session_id"])


def _stop(client: TestClient, sid: str) -> None:
    client.post(f"/api/sessions/{sid}/stop")


def _page(client: TestClient, sid: str) -> Any:
    return client.app.state.itb.sessions.require(sid).tabs[0].page


def _pause(client: TestClient, sid: str) -> None:
    """검증 추가는 일시정지 상태에서만 할 수 있다."""
    resp = client.post(f"/api/sessions/{sid}/pause")
    assert resp.status_code in (200, 204, 409), resp.text


def _add(client: TestClient, sid: str, **body: Any) -> Any:
    return client.post(f"/api/sessions/{sid}/assertions", json=body)


def _run_steps(client: TestClient, sid: str) -> list[dict[str, Any]]:
    return list(client.get(f"/api/sessions/{sid}").json()["steps"])


# ── 값이 관찰된다 (T034) ────────────────────────────────────────────────────


@pytest.mark.usefixtures("fixture_app")
def test_value_assertion_reads_what_text_assertion_cannot(
    project_client: TestClient, fixture_app: str
) -> None:
    """**이 기능의 출발점.** 같은 칸·같은 값에 두 검증을 걸어 결과가 갈리는지 본다.

    텍스트 검증은 실패하고 입력값 검증은 통과해야 한다. 텍스트 쪽이 통과하면 고장이
    재현되지 않은 것이고, 입력값 쪽이 실패하면 고치지 못한 것이다.
    """
    sid = _session(project_client, fixture_app)
    try:
        page = _page(project_client, sid)

        async def act() -> None:
            await page.wait_for_selector(NAME_FIELD)
            await page.fill(NAME_FIELD, "E2E역할테스트")
            await asyncio.sleep(0.5)

        project_client.portal.call(act)  # type: ignore[attr-defined]
        _pause(project_client, sid)

        by_text = _add(
            project_client,
            sid,
            kind="text",
            target_selector=NAME_FIELD,
            value="E2E역할테스트",
        )
        by_value = _add(
            project_client,
            sid,
            kind="value",
            target_selector=NAME_FIELD,
            value="E2E역할테스트",
        )
        assert by_text.status_code == 200, by_text.text
        assert by_value.status_code == 200, by_value.text

        saved = project_client.post(f"/api/sessions/{sid}/save", json={"name": "두 검증"})
        assert saved.status_code == 200, saved.text
        test_id = str(saved.json()["id"])
    finally:
        _stop(project_client, sid)

    # **실행해야 갈린다.** 화면 폼 경로는 Step 을 만들 뿐 검증을 돌리지 않는다 —
    # 작성 시점 어긋남 기록(020)은 AI 작성 경로의 것이다.
    from us2_support import replay, result_of

    replay(project_client, test_id)
    result = result_of(project_client, test_id)
    by_label = {s["label"]: s for s in result["steps"]}

    text_step = next(s for k, s in by_label.items() if k.startswith("텍스트가"))
    value_step = next(s for k, s in by_label.items() if k.startswith("입력값이"))

    assert text_step["outcome"] == "fail", (
        "입력 칸 대상 텍스트 검증이 통과했다 — 고장이 재현되지 않았다"
    )
    assert "''" in (text_step.get("error_message") or ""), (
        f"관찰값이 빈 문자열로 나와야 한다: {text_step.get('error_message')}"
    )
    assert value_step["outcome"] == "pass", (
        f"입력값 검증이 실패했다: {value_step.get('error_message')}"
    )


@pytest.mark.usefixtures("fixture_app")
def test_multiline_value_keeps_newlines(
    project_client: TestClient, fixture_app: str
) -> None:
    """여러 줄 입력 칸의 줄바꿈이 보존된다 (FR-008).

    다듬으면 사용자가 적은 값과 비교가 어긋난다 — 화면 텍스트와 달리 이것은 **실제 값**
    이다.
    """
    sid = _session(project_client, fixture_app)
    try:
        page = _page(project_client, sid)

        async def act() -> None:
            await page.wait_for_selector(NAME_FIELD)
            await page.fill(NAME_FIELD, "첫줄\n둘째줄")
            await asyncio.sleep(0.5)

        project_client.portal.call(act)  # type: ignore[attr-defined]
        _pause(project_client, sid)

        resp = _add(
            project_client,
            sid,
            kind="value",
            target_selector=NAME_FIELD,
            value="첫줄\n둘째줄",
        )
        assert resp.status_code == 200, resp.text
        step = [s for s in _run_steps(project_client, sid) if s["type"] == "assertion"][-1]
        assert step.get("mismatch") is None, f"줄바꿈이 보존되지 않았다: {step['mismatch']}"
    finally:
        _stop(project_client, sid)


@pytest.mark.usefixtures("fixture_app")
def test_hidden_field_value_is_still_read(
    project_client: TestClient, fixture_app: str
) -> None:
    """화면에서 숨겨져 있어도 값은 읽힌다 (명세 Edge Cases · 실측 R8a).

    보이는지를 묻는 검증은 `요소가 보인다` 가 따로 있다 — 두 사실을 한 검증에 뭉치지
    않는다.
    """
    sid = _session(project_client, fixture_app)
    try:
        page = _page(project_client, sid)
        project_client.portal.call(  # type: ignore[attr-defined]
            lambda: page.wait_for_selector(NAME_FIELD)
        )
        _pause(project_client, sid)

        resp = _add(
            project_client, sid, kind="value", target_selector=HIDDEN_FIELD, value="숨은값"
        )
        assert resp.status_code == 200, resp.text
        step = [s for s in _run_steps(project_client, sid) if s["type"] == "assertion"][-1]
        assert step.get("mismatch") is None, f"숨겨진 칸의 값을 읽지 못했다: {step['mismatch']}"
    finally:
        _stop(project_client, sid)


# ── 오용 방지 (T064) ────────────────────────────────────────────────────────


@pytest.mark.usefixtures("fixture_app")
@pytest.mark.parametrize(
    ("selector", "expect_in_message"),
    [
        ("#agree", "체크"),  # 체크박스 — 값이 체크 여부와 무관
        ("#pool", "텍스트 검증"),  # 값 없는 대상 — 대안을 가리킨다
    ],
)
def test_value_assertion_refuses_targets_without_a_meaningful_value(
    project_client: TestClient, fixture_app: str, selector: str, expect_in_message: str
) -> None:
    """Step 을 만들지 않고 이유를 설명한다 (FR-031·FR-032).

    **거절 문구가 대안을 담는지**가 이 검증의 요점이다. 「지원하지 않습니다」로 끝나면
    사용자도 모델도 다음에 무엇을 할지 모른다.
    """
    sid = _session(project_client, fixture_app)
    try:
        page = _page(project_client, sid)
        project_client.portal.call(  # type: ignore[attr-defined]
            lambda: page.wait_for_selector(NAME_FIELD)
        )
        _pause(project_client, sid)

        before = len(_run_steps(project_client, sid))
        resp = _add(project_client, sid, kind="value", target_selector=selector, value="x")
        assert resp.status_code == 400, resp.text
        assert expect_in_message in resp.text, f"대안이 없는 거절 문구: {resp.text}"
        assert len(_run_steps(project_client, sid)) == before, "거절했는데 Step 이 늘었다"
    finally:
        _stop(project_client, sid)


@pytest.mark.usefixtures("fixture_app")
def test_select_target_is_allowed_with_a_note(
    project_client: TestClient, fixture_app: str
) -> None:
    """선택 목록은 만들되 **내부 식별자를 비교한다고 알린다** (FR-033).

    실측: 화면에 `분석` 이 보여도 값은 `analysis` 다 (R8a). 이것을 모르면 화면에서 읽은
    글자를 적고 실패한 뒤 이유를 찾지 못한다.
    """
    sid = _session(project_client, fixture_app)
    try:
        page = _page(project_client, sid)
        project_client.portal.call(  # type: ignore[attr-defined]
            lambda: page.wait_for_selector(SELECT_FIELD)
        )
        _pause(project_client, sid)

        resp = _add(
            project_client, sid, kind="value", target_selector=SELECT_FIELD, value="analysis"
        )
        assert resp.status_code == 200, resp.text
        view = project_client.get(f"/api/sessions/{sid}").json()
        notes = " ".join(view.get("edit_warnings") or [])
        assert "내부 식별자" in notes, f"선택 목록 안내가 없다: {notes}"
    finally:
        _stop(project_client, sid)


@pytest.mark.usefixtures("fixture_app")
def test_text_assertion_on_an_input_warns_but_is_created(
    project_client: TestClient, fixture_app: str
) -> None:
    """입력 칸에 텍스트 검증을 고르면 알리되 **막지 않는다** (FR-030).

    막으면 이미 저장된 정의를 여는 경로에서 거절이 일어나 FR-040 과 충돌한다.
    """
    sid = _session(project_client, fixture_app)
    try:
        page = _page(project_client, sid)
        project_client.portal.call(  # type: ignore[attr-defined]
            lambda: page.wait_for_selector(NAME_FIELD)
        )
        _pause(project_client, sid)

        before = len(_run_steps(project_client, sid))
        resp = _add(project_client, sid, kind="text", target_selector=NAME_FIELD, value="x")
        assert resp.status_code == 200, resp.text
        assert len(_run_steps(project_client, sid)) == before + 1, "Step 이 만들어지지 않았다"

        view = project_client.get(f"/api/sessions/{sid}").json()
        notes = " ".join(view.get("edit_warnings") or [])
        assert "입력값" in notes, f"대안을 가리키는 안내가 없다: {notes}"
    finally:
        _stop(project_client, sid)
