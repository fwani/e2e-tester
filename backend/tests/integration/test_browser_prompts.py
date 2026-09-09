"""브라우저 요구 가로채기 (010 T068 · FR-337~FR-339 · research R6·R7).

**가로채지 않으면 대상 페이지가 멈춘다.** 대화상자는 응답이 올 때까지 페이지를 세우고,
헤드리스에서는 화면에도 나타나지 않는다 — 사용자에게는 「클릭했는데 아무 일도 없다」로
보인다. 그것이 FR-339 가 금지하는 조용한 실패이고, 이 파일이 재는 것이 그 반전이다.

살아 있는 브라우저를 쓰는 이유는 이 성질이 **Playwright 의 사건 전달**에 걸려 있기
때문이다. 가짜로는 「가로챘다고 믿는 코드」까지만 잴 수 있다.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import pytest
from fastapi.testclient import TestClient
from us2_support import stop_quietly

EVENTS_PATH = "/api/sessions/{sid}/events"

INJECT = """
  const go = document.createElement('button');
  go.id = 'go';
  go.textContent = '확인 열기';
  go.onclick = () => { window.answer = confirm('계속할까요?'); };
  const pick = document.createElement('input');
  pick.id = 'pick';
  pick.type = 'file';
  document.body.append(go, pick);
"""
"""대화상자와 파일 선택 요소를 화면에 **주입한다.**

픽스처 앱에 페이지를 더하지 않는 이유는 재는 것이 **브라우저 수준의 요구**이기 때문이다 —
그것은 어느 페이지에서나 같고, 픽스처는 요소 후보 수집을 위해 신중히 짜인 자산이다.
여기서 필요한 것은 요구를 일으키는 버튼 둘뿐이므로 자산을 건드리지 않는다.
"""


def _start(client: TestClient, fixture_app: str) -> str:
    created = client.post(
        "/api/sessions",
        json={"mode": "record", "start_url": f"{fixture_app}/interactions.html"},
    )
    assert created.status_code == 201, created.text
    session_id = str(created.json()["session_id"])

    page = _page(client, session_id)

    async def inject(p: Any = page) -> None:
        await p.evaluate(INJECT)

    client.portal.call(inject)  # type: ignore[attr-defined]
    return session_id


def _page(client: TestClient, session_id: str) -> Any:
    return client.app.state.itb.sessions.require(session_id).tabs[0].page


def _prompts(client: TestClient, session_id: str) -> Any:
    from itb.api.routes.sessions import work_of

    return work_of(session_id).prompts


def _wait_for_prompt(client: TestClient, session_id: str, timeout_s: float = 10.0) -> Any:
    """요구가 도착하기를 기다린다. 오지 않으면 실패한다.

    **오지 않는 것 자체가 결함이다** — 그러면 대상 페이지가 멈춘 채로 남고 사용자는
    무엇이 막혔는지 알 수 없다 (FR-339).
    """
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        prompts = _prompts(client, session_id)
        if prompts is not None and prompts.pending:
            return next(iter(prompts.pending.values()))
        time.sleep(0.05)
    msg = f"{timeout_s}초 안에 브라우저 요구가 도착하지 않았다 (FR-339)"
    raise AssertionError(msg)


@pytest.mark.browser
def test_a_confirm_dialog_is_intercepted_and_announced(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """`confirm` 이 가로채이고 그 사실이 알려진다 (FR-338 · research R7).

    **자동으로 닫지 않는다.** 닫으면 사용자가 고를 기회를 잃고, 그 선택은 대상 페이지의
    다음 화면을 정한다 — 제품이 대신 고르면 녹화된 것은 사용자가 하려던 것과 다르다.
    """
    session_id = _start(keyed_client, fixture_app)
    try:
        page = _page(keyed_client, session_id)

        async def click(p: Any = page) -> None:
            # 대화상자는 페이지를 세우므로 클릭을 기다리지 않는다.
            asyncio.get_running_loop().create_task(p.click("#go"))  # noqa: RUF006
            await asyncio.sleep(0.5)

        keyed_client.portal.call(click)  # type: ignore[attr-defined]

        prompt = _wait_for_prompt(keyed_client, session_id)
        assert prompt.kind == "dialog.confirm", f"종류가 다르다: {prompt.kind}"
        assert "계속할까요?" in prompt.message
        assert prompt.blocking is True, "대화상자는 페이지를 세우므로 blocking 이어야 한다"
    finally:
        stop_quietly(keyed_client, session_id)


@pytest.mark.browser
def test_the_users_choice_reaches_the_target_page(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """사용자의 선택이 대상 페이지에 전달된다 (FR-338 · US4 인수 2).

    수락하면 `confirm` 이 `true` 를 돌려주고 페이지가 계속 간다. 그것이 「제품 화면이
    대신 받는다」의 완결이다.
    """
    session_id = _start(keyed_client, fixture_app)
    try:
        page = _page(keyed_client, session_id)

        async def click(p: Any = page) -> None:
            asyncio.get_running_loop().create_task(p.click("#go"))  # noqa: RUF006
            await asyncio.sleep(0.5)

        keyed_client.portal.call(click)  # type: ignore[attr-defined]
        prompt = _wait_for_prompt(keyed_client, session_id)

        answered = keyed_client.post(
            f"/api/sessions/{session_id}/prompts/{prompt.prompt_id}",
            json={"accept": True},
        )
        assert answered.status_code == 204, answered.text

        async def read(p: Any = page) -> Any:
            await asyncio.sleep(0.3)
            return await p.evaluate("window.answer")

        assert keyed_client.portal.call(read) is True  # type: ignore[attr-defined]
    finally:
        stop_quietly(keyed_client, session_id)


@pytest.mark.browser
def test_answering_twice_is_refused(keyed_client: TestClient, fixture_app: str) -> None:
    """**이미 해소된 요구는 거절한다** (FR-340).

    두 번 응답하면 Playwright 가 예외를 내고, 그 예외는 사용자에게 아무것도 설명하지
    못한다. 사유가 있는 404 가 낫다.
    """
    session_id = _start(keyed_client, fixture_app)
    try:
        page = _page(keyed_client, session_id)

        async def click(p: Any = page) -> None:
            asyncio.get_running_loop().create_task(p.click("#go"))  # noqa: RUF006
            await asyncio.sleep(0.5)

        keyed_client.portal.call(click)  # type: ignore[attr-defined]
        prompt = _wait_for_prompt(keyed_client, session_id)
        path = f"/api/sessions/{session_id}/prompts/{prompt.prompt_id}"

        assert keyed_client.post(path, json={"accept": True}).status_code == 204
        again = keyed_client.post(path, json={"accept": True})
        assert again.status_code == 404, again.text
        assert "이미 처리" in again.text
    finally:
        stop_quietly(keyed_client, session_id)


@pytest.mark.browser
def test_an_unknown_prompt_id_is_refused(keyed_client: TestClient, fixture_app: str) -> None:
    """다른 세션의 `prompt_id` 는 이 세션에 없다 (FR-340).

    세션 식별자만으로 임의의 다른 세션을 조작할 수 없어야 한다. 요구 사전이 세션마다
    따로 있으므로 그 격리가 **검사가 아니라 구조로** 성립한다.
    """
    session_id = _start(keyed_client, fixture_app)
    try:
        refused = keyed_client.post(
            f"/api/sessions/{session_id}/prompts/p_deadbeef", json={"accept": True}
        )
        assert refused.status_code == 404
    finally:
        stop_quietly(keyed_client, session_id)


@pytest.mark.browser
def test_a_file_chooser_is_intercepted_without_an_os_window(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """파일 선택이 가로채인다 — **운영체제 창은 뜨지 않는다** (FR-337 · research R6).

    창을 띄우던 때는 운영체제 파일 선택 창이 떴다. 창이 없으면 그 창도 없고, 그 상태에서
    가로채지 않으면 사용자는 클릭했는데 아무 일도 일어나지 않는 것을 본다.

    **이것이 화면 없는 기계에서 파일 첨부 녹화가 성립하는 이유다** (SC-518).
    """
    session_id = _start(keyed_client, fixture_app)
    try:
        page = _page(keyed_client, session_id)

        async def click(p: Any = page) -> None:
            await p.click("#pick")
            await asyncio.sleep(0.4)

        keyed_client.portal.call(click)  # type: ignore[attr-defined]

        prompt = _wait_for_prompt(keyed_client, session_id)
        assert prompt.kind == "file.choose"
        # 파일 선택은 페이지를 세우지 않는다 — 고르지 않아도 페이지는 계속 돈다.
        assert prompt.blocking is False
    finally:
        stop_quietly(keyed_client, session_id)


@pytest.mark.browser
def test_an_uploaded_file_reaches_the_target_page(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """**사용자가 올린 파일이 대상 페이지에 전달된다** (FR-337 · US4 인수 1 · SC-517).

    사용자가 자기 기계에서 고른 파일을 제품이 받아 대상 브라우저에 지정한다 — 제품이
    도는 기계의 경로를 사용자가 입력하는 방식이 아니다.
    """
    session_id = _start(keyed_client, fixture_app)
    try:
        page = _page(keyed_client, session_id)

        async def click(p: Any = page) -> None:
            await p.click("#pick")
            await asyncio.sleep(0.4)

        keyed_client.portal.call(click)  # type: ignore[attr-defined]
        prompt = _wait_for_prompt(keyed_client, session_id)

        uploaded = keyed_client.post(
            f"/api/sessions/{session_id}/files",
            files={"file": ("주문내역.csv", b"a,b\n1,2\n", "text/csv")},
        )
        assert uploaded.status_code == 201, uploaded.text
        file_id = uploaded.json()["file_id"]
        assert uploaded.json()["display_name"] == "주문내역.csv"

        answered = keyed_client.post(
            f"/api/sessions/{session_id}/prompts/{prompt.prompt_id}",
            json={"accept": True, "file_ids": [file_id]},
        )
        assert answered.status_code == 204, answered.text

        async def read(p: Any = page) -> Any:
            await asyncio.sleep(0.4)
            return await p.evaluate(
                "document.getElementById('pick').files.length"
            )

        assert keyed_client.portal.call(read) == 1, "대상 페이지가 파일을 받지 못했다"  # type: ignore[attr-defined]
    finally:
        stop_quietly(keyed_client, session_id)


@pytest.mark.browser
def test_upload_over_the_size_limit_is_refused_with_a_reason(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """상한을 넘는 업로드는 **사유와 함께** 거절된다 (FR-337a).

    자르지 않는다 — 잘린 파일을 대상 페이지가 받으면 그 실패는 원인을 드러내지 않는다.
    """
    from itb.storage.session_files import MAX_FILE_BYTES

    session_id = _start(keyed_client, fixture_app)
    try:
        too_big = b"x" * (MAX_FILE_BYTES + 1024)
        refused = keyed_client.post(
            f"/api/sessions/{session_id}/files",
            files={"file": ("big.bin", too_big, "application/octet-stream")},
        )
        assert refused.status_code == 400, refused.status_code
        assert "상한" in refused.text
    finally:
        stop_quietly(keyed_client, session_id)


@pytest.mark.browser
def test_uploaded_files_are_gone_after_the_session_ends(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """**사용자가 보낸 파일이 세션보다 오래 남지 않는다** (FR-337b)."""
    from pathlib import Path

    session_id = _start(keyed_client, fixture_app)
    uploaded = keyed_client.post(
        f"/api/sessions/{session_id}/files",
        files={"file": ("a.txt", b"hello", "text/plain")},
    )
    assert uploaded.status_code == 201, uploaded.text
    store = keyed_client.app.state.itb.session_files.get(session_id)
    assert store is not None
    path = Path(str(store.path_of(uploaded.json()["file_id"])))
    assert path.is_file()

    stop_quietly(keyed_client, session_id)
    keyed_client.post(f"/api/sessions/{session_id}/discard")

    assert not path.exists(), "세션이 끝났는데 사용자가 보낸 파일이 남았다 (FR-337b)"


@pytest.mark.browser
def test_a_prompt_is_announced_on_the_observation_socket(
    keyed_client: TestClient, fixture_app: str
) -> None:
    """요구가 **관찰 소켓으로** 나간다 (contracts §4).

    방향은 바뀌지 않는다 — 서버 → 클라이언트다. 조작은 별개의 소켓으로 받는다. 이
    검증이 그 계약이 유지되는지를 본다.
    """
    session_id = _start(keyed_client, fixture_app)
    try:
        with keyed_client.websocket_connect(EVENTS_PATH.format(sid=session_id)) as ws:
            page = _page(keyed_client, session_id)

            async def click(p: Any = page) -> None:
                await p.click("#pick")
                await asyncio.sleep(0.4)

            keyed_client.portal.call(click)  # type: ignore[attr-defined]

            seen: list[dict[str, Any]] = []
            for _ in range(40):
                message = ws.receive_json()
                seen.append(message)
                if message.get("type") == "browser_prompt":
                    break
            announced = [m for m in seen if m.get("type") == "browser_prompt"]
            assert announced, f"요구가 관찰 소켓으로 나가지 않았다: {[m['type'] for m in seen]}"
            assert announced[0]["kind"] == "file.choose"
            assert "promptId" in announced[0]
    finally:
        stop_quietly(keyed_client, session_id)
