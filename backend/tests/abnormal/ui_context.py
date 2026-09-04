"""화면 면 수단이 쓰는 실행 맥락. **제품 화면을 실제 브라우저로 조작한다** (RG-105).

이 저장소에는 제품 화면을 실제로 여는 검증이 없었다. `product_ui` 픽스처가 제품 서버와
제품 화면을 띄우고, 여기서 그것을 사람처럼 누른다.

세 가지를 지킨다.

1. **판정 근거는 화면에서 읽는다.** 제품이 응답으로 무엇을 냈는지가 아니라, 사용자가 무엇을
   보는지가 이 면의 판정 대상이다. 오류는 공용 통로(`ErrorNotice`)가 남긴 표시로 읽는다
2. **상태 준비는 제품 API 로 한다.** 열 화면에 닿기까지 열 번 클릭하는 과정은 재려는 것이
   아니다. 준비는 API 로 하고, **판정은 화면으로** 한다
3. **화면이 미리 막은 것은 결함이 아니다.** 보내고 나서 거절하는 것보다 낫다. 다만 무엇이
   막는지가 화면에 보여야 한다 — 그것은 판정축 ②가 본다

화면은 라우터가 없다. 상태로 화면을 고르므로 **매번 처음부터 눌러 들어간다.**
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from playwright.async_api import Browser, Page
from playwright.async_api import TimeoutError as PlaywrightTimeout

from tests.abnormal.catalogue import Attempt
from tests.abnormal.product_ui import ProductUI

# 화면이 뜨고 첫 요청이 오갈 때까지. 개발 서버가 첫 변환을 하는 동안은 느리다.
LOAD_TIMEOUT_MS = 20_000
ACT_TIMEOUT_MS = 8_000

NOTICE = "[data-error-notice]"
"""오류 공용 통로가 남기는 표시 (T016). 화면마다 다른 문구를 찾아다니지 않는다."""


@dataclass
class UiContext:
    """띄워진 제품과, 그것을 조작하는 창 하나."""

    ui: ProductUI
    browser: Browser
    fixture_app: str
    pages: list[Page] = field(default_factory=list)

    # ─── 창 ─────────────────────────────────────────────────────────────────

    async def open(self) -> Page:
        """새 창을 열어 제품 화면을 띄운다. 두 창이 필요한 시나리오가 있으므로 여러 개다."""
        page = await self.browser.new_page()
        # **무한정 기다리는 조작을 만들지 않는다.** 기본값(30초)을 그대로 두면 한 시나리오가
        # 멈췄을 때 실패도 통과도 아닌 상태로 남는다.
        page.set_default_timeout(ACT_TIMEOUT_MS)
        page.set_default_navigation_timeout(LOAD_TIMEOUT_MS)
        self.pages.append(page)
        await page.goto(self.ui.base_url, wait_until="domcontentloaded")
        await page.wait_for_selector("main, button", timeout=LOAD_TIMEOUT_MS)
        return page

    async def close_all(self) -> None:
        for page in self.pages:
            if not page.is_closed():
                await page.close()
        self.pages.clear()

    # ─── 제품 API (상태 준비 전용) ──────────────────────────────────────────

    def api(self, method: str, path: str, body: Any = None) -> tuple[int, Any]:
        """제품 서버에 직접 요청한다. **준비에만 쓴다** — 판정은 화면이 한다."""
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(  # noqa: S310 - 로컬 주소만 연다
            f"{self.ui.api_url}{path}",
            data=data,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
                raw = resp.read()
                return resp.status, (json.loads(raw) if raw else None)
        except urllib.error.HTTPError as exc:
            raw = exc.read()
            try:
                return exc.code, json.loads(raw)
            except ValueError:
                return exc.code, raw.decode(errors="replace")

    def fixture(self, path: str) -> str:
        """검증용 대상 앱의 한 주소."""
        return f"{self.fixture_app}{path}"

    def require_no_project(self) -> None:
        """프로젝트가 아직 열리지 않았어야 한다.

        제품 화면은 프로젝트가 열려 있으면 목록으로 가고 **프로젝트 선택 화면으로 돌아갈
        길이 없다** — 닫는 경로가 제품에 없기 때문이다. 그래서 그 화면의 시나리오는 다른
        시나리오가 프로젝트를 열기 전에 돌아야 한다.

        조건이 어긋나면 **건너뛰지 않고 실패한다** (RG-106). 조용히 지나가면 이 시나리오는
        아무것도 재지 않은 채 통과한다.
        """
        status, _ = self.api("GET", "/api/project")
        assert status != 200, (
            "이미 프로젝트가 열려 있어 프로젝트 선택 화면에 닿을 수 없습니다. "
            "이 시나리오는 목록에서 첫 화면 면 항목이라 다른 것보다 먼저 돌아야 합니다 — "
            "순서가 바뀌었는지 확인하세요."
        )

    def clear_sessions(self) -> None:
        """살아 있는 세션을 모두 치운다.

        시나리오는 서로 독립이어야 한다. 앞 시나리오가 남긴 세션이 있으면 목록 화면에
        "진행 중인 세션이 있습니다" 가 떠 다음 시나리오가 다른 화면을 보게 되고, 그
        차이가 있지도 않은 결함처럼 보인다.

        제품의 목록·중지 경로를 쓴다 — 파일이나 내부 상태를 직접 만지지 않는다.
        """
        status, body = self.api("GET", "/api/sessions")
        if status != 200:
            return
        for view in body.get("sessions", []):
            session_id = view.get("session_id")
            if not session_id:
                continue
            self.api("POST", f"/api/sessions/{session_id}/stop")
            self.api("POST", f"/api/sessions/{session_id}/discard")

    def session_count(self) -> int:
        status, body = self.api("GET", "/api/health")
        return int(body["active_sessions"]) if status == 200 else -1

    def sessions_healthy(self) -> bool:
        return self.api("GET", "/api/health")[0] == 200

    def step_count(self, session_id: str) -> int:
        status, body = self.api("GET", f"/api/sessions/{session_id}")
        return len(body.get("steps", [])) if status == 200 else -1

    def drop_keys(self) -> None:
        """키가 없는 상태로 만든다. 없으면 그대로 둔다."""
        self.api("DELETE", "/api/keys", {"confirm": "DELETE"})

    def ensure_keys(self) -> None:
        status, _ = self.api("GET", "/api/keys/status")
        if status == 200:
            self.api("POST", "/api/keys/generate", {"passphrase": None})

    def make_test_with_unusable_target(self, name: str) -> str:
        """쓸 수 있는 후보가 하나도 없는 Step 을 가진 정의를 만든다.

        후보는 기록 시점에 수집되고 화면은 표시만 한다 — 화면에서 후보를 지우는 조작은
        없다. 그래서 그런 정의를 만들어 두고 **화면이 그것을 말없이 정상처럼 보여 주는지**
        를 본다.
        """
        return self._write_definition(
            self._next_test_id(),
            name,
            steps=[
                {
                    "type": "click",
                    "id": "step-01",
                    "label": "쓸 수 없는 대상 누르기",
                    "author": "human",
                    "tab": 0,
                    "timeout_ms": 5000,
                    "target": {"css": {"value": ".gone", "status": "not_collected"}},
                }
            ],
        )

    def make_test_with_bare_result(self, name: str) -> str:
        """실패했지만 산출물이 하나도 없는 결과를 가진 테스트를 만든다.

        결과도 **제품의 모델로** 쓴다. 손으로 JSON 을 짜면 형태가 조금씩 어긋나고, 그
        어긋남이 화면의 결함처럼 보인다.
        """
        from itb.domain.run_result import RunResult, StepResult  # noqa: PLC0415
        from itb.storage.repository import ProjectRepository  # noqa: PLC0415

        test_id = self._write_definition(self._next_test_id(), name)
        ProjectRepository.open(self._root()).write_result(
            RunResult(
                test_id=test_id,
                outcome="fail",
                started_at="2026-09-04T00:00:00Z",
                finished_at="2026-09-04T00:00:12Z",
                browser="chromium",
                total_ms=12,
                passed_count=0,
                total_count=1,
                failed_step_index=1,
                steps=[
                    StepResult(
                        step_id="step-01",
                        index=1,
                        label="탭 닫기",
                        outcome="fail",
                        duration_ms=12,
                        error_message="산출물이 남지 않은 실패입니다.",
                    )
                ],
            )
        )
        return test_id

    def lose_browser(self, session_id: str) -> None:
        """세션이 쥔 브라우저를 **바깥에서** 잃게 만든다.

        제품 서버가 다른 프로세스라 객체를 직접 만질 수 없다. 대신 그 세션이 연 창을
        모두 닫는 조작을 Step 으로 보낸다 — 사용자가 창을 닫는 것과 같은 결과다.
        """
        self.api("POST", f"/api/sessions/{session_id}/pause")
        self.api(
            "POST",
            f"/api/sessions/{session_id}/steps",
            {"step": {"type": "close_tab", "id": "step-99", "label": "탭 닫기", "tab": 0}},
        )

    def _next_test_id(self) -> str:
        status, body = self.api("GET", "/api/tests")
        assert status == 200, f"목록을 읽지 못했다: {body}"
        return f"TC-{len(body['tests']) + 1:03d}"

    def ensure_project(self) -> None:
        """프로젝트가 열려 있게 한다. 대부분의 화면이 그것을 전제한다."""
        status, _ = self.api("GET", "/api/project")
        if status == 200:
            return
        created, body = self.api(
            "POST",
            "/api/project/create",
            {"name": "이상 조작 검증", "default_start_url": "https://example.invalid/login"},
        )
        assert created == 201, f"검증용 프로젝트를 만들지 못했다: {created} {body}"

    def make_test(self, name: str) -> str:
        """저장된 테스트 하나를 만든다. 화면이 목록에서 그것을 보게 하려는 것이다."""
        return self._write_definition(self._next_test_id(), name)

    def _write_definition(
        self, test_id: str, name: str, steps: list[dict[str, Any]] | None = None
    ) -> str:
        """정의 파일을 **제품의 저장 계층으로** 쓴다. 제품 서버와 같은 파일을 본다.

        브라우저를 띄워 녹화하는 과정을 매 시나리오마다 반복하면 화면 면 검증이 아니라
        녹화 검증이 된다. 만드는 방법은 재려는 것이 아니다.
        """
        from itb.domain.test_case import Test  # noqa: PLC0415
        from itb.storage.repository import ProjectRepository  # noqa: PLC0415

        repo = ProjectRepository.open(self._root())
        repo.write_test(
            Test(
                id=test_id,
                name=name,
                authoring_mode="record",
                start_url=repo.read_project().default_start_url,
                variables=[],
                steps=steps
                or [
                    {
                        "type": "close_tab",
                        "id": "step-01",
                        "label": "탭 닫기",
                        "author": "human",
                        "tab": 0,
                        "timeout_ms": 5000,
                    }
                ],
            )
        )
        return test_id

    def _root(self) -> Any:
        import pathlib  # noqa: PLC0415

        status, project = self.api("GET", "/api/project")
        assert status == 200, "프로젝트가 열려 있지 않다"
        return pathlib.Path(project["root"])

    # ─── 화면 읽기 ──────────────────────────────────────────────────────────

    async def notice(self, page: Page) -> dict[str, Any] | None:
        """공용 오류 통로가 화면에 남긴 것을 계약 형태로 읽는다.

        화면은 `code` 를 표시하지 않는 경우가 있어(`UNKNOWN`) 그대로 옮긴다 — 판정축 ①은
        분류와 다음 행동이 **화면에 닿았는지**를 보지, 코드를 대조하지 않는다.
        """
        node = page.locator(NOTICE).first
        if await node.count() == 0:
            return None
        message = (await node.locator("[data-error-message]").inner_text()).strip()
        action = (await node.locator("[data-error-next-action]").inner_text()).strip()
        return {
            "code": await node.get_attribute("data-code") or "UNKNOWN",
            "category": await node.get_attribute("data-category") or "blocked",
            "message": message,
            "next_action": action,
            "detail": {},
        }

    async def wait_for_notice(self, page: Page, timeout_ms: int = ACT_TIMEOUT_MS) -> None:
        """오류 표시가 나타나기를 기다린다. 없으면 조용히 지나간다 — 판정이 그것을 잡는다."""
        try:
            await page.wait_for_selector(NOTICE, timeout=timeout_ms)
        except PlaywrightTimeout:
            return

    async def visible_text(self, page: Page) -> str:
        return (await page.locator("body").inner_text()).strip()

    async def click(self, page: Page, name: str, timeout_ms: int = ACT_TIMEOUT_MS) -> None:
        await page.get_by_role("button", name=name, exact=False).first.click(timeout=timeout_ms)

    async def fill(self, page: Page, label: str, value: str) -> None:
        await page.get_by_label(label, exact=False).first.fill(value, timeout=ACT_TIMEOUT_MS)

    async def is_disabled(self, page: Page, name: str) -> bool:
        button = page.get_by_role("button", name=name, exact=False).first
        await button.wait_for(state="attached", timeout=ACT_TIMEOUT_MS)
        return await button.is_disabled()

    async def has_button(self, page: Page, name: str) -> bool:
        return await page.get_by_role("button", name=name, exact=False).count() > 0

    async def click_if_present(self, page: Page, name: str) -> bool:
        """있으면 누르고, 없거나 눌리지 않으면 그 사실을 돌려준다.

        **예외로 끝내지 않는다.** 화면이 그 조작을 이미 거두어 갔다는 것 자체가 판정
        대상이므로, 누르지 못한 것은 실패가 아니라 관측이다.
        """
        button = page.get_by_role("button", name=name, exact=False).first
        if await button.count() == 0:
            return False
        try:
            await button.click(timeout=3_000)
        except PlaywrightTimeout:
            return False
        return True

    async def settle(self, page: Page, ms: int = 1_200) -> None:
        """화면이 응답을 받아 다시 그릴 틈을 준다."""
        await page.wait_for_timeout(ms)

    # ─── 화면이 스스로 막은 자리의 안내 ─────────────────────────────────────

    async def leaf_texts(self, page: Page, limit: int = 400) -> list[str]:
        """화면의 **잎 노드 문구**를 모은다.

        `p`·`label` 같은 태그 목록으로 찾으면 그 태그를 쓰지 않은 안내를 놓친다 — 이
        화면들은 안내를 `div`·`span` 으로도 쓴다. 태그를 고르는 대신 **자식 요소가 없는
        노드**를 모으면 화면에 실제로 보이는 문구만 남는다. 버튼의 `title`·
        `aria-label` 도 함께 모은다 — 비활성 버튼의 사유가 거기 있다.
        """
        return await page.evaluate(
            """(limit) => {
                const out = [];
                for (const el of document.querySelectorAll("*")) {
                    if (el.childElementCount === 0) {
                        const text = (el.textContent || "").trim();
                        if (text && text.length < 300) out.push(text);
                    }
                    for (const attr of ["title", "aria-label", "placeholder"]) {
                        const value = (el.getAttribute(attr) || "").trim();
                        if (value) out.push(value);
                    }
                    if (el.childElementCount === 0 && out.length > limit) break;
                }
                return out;
            }""",
            limit,
        )

    async def form_guidance(self, page: Page, near: str) -> str:
        """화면이 "지금 왜 안 되는지" 를 말하고 있는가.

        오류 통로가 없는 자리다 — 요청을 보내지 않았으므로 오류가 없다. 그래도 무엇이
        막는지는 보여야 한다. `near` 와 겹치는 문구만 골라 모으고, 아무것도 없으면
        빈 문자열이 되어 판정축 ②가 그것을 잡는다.

        **이름표는 안내가 아니다.** "프로젝트 이름" 이라는 라벨이 있다는 사실도, 버튼에
        "AI 실행" 이라고 쓰여 있다는 사실도 "왜 지금 안 되는지" 를 말하지 않는다. 그것을
        안내로 세면 어떤 화면이든 통과해 아무것도 재지 못한다. 그래서 조작·입력의
        **이름표로 쓰인 문구는 뺀다.**
        """
        key = near.strip()
        labels = await page.evaluate(
            """() => {
                const out = [];
                for (const el of document.querySelectorAll("button, label, a, h1, h2, h3")) {
                    const text = (el.textContent || "").trim();
                    if (text) out.push(text);
                    const aria = (el.getAttribute("aria-label") || "").trim();
                    if (aria) out.push(aria);
                }
                return out;
            }"""
        )
        label_texts = {text.strip() for text in labels}
        hits = [
            text
            for text in await self.leaf_texts(page)
            if key in text and text.strip() != key and text.strip() not in label_texts
        ]
        return " / ".join(dict.fromkeys(hits))[:600]

    async def disabled_reason(self, page: Page, name: str) -> str:
        """비활성 버튼이 자기 사유를 들고 있는가.

        `title`·`aria-label`·`aria-describedby` 가 그 자리다. 사유 없이 눌리지 않는
        버튼은 "조작이 삼켜진 것" 과 사용자에게 구별되지 않는다 (AP-003).
        """
        button = page.get_by_role("button", name=name, exact=False).first
        if await button.count() == 0:
            return ""
        parts: list[str] = []
        for attr in ("title", "aria-label"):
            value = await button.get_attribute(attr)
            if value and value.strip() and value.strip() != name:
                parts.append(value.strip())
        described = await button.get_attribute("aria-describedby")
        if described:
            for token in described.split():
                node = page.locator(f"#{token}")
                if await node.count() > 0:
                    text = (await node.first.inner_text()).strip()
                    if text:
                        parts.append(text)
        return " / ".join(dict.fromkeys(parts))[:600]

    async def still_usable(self, page: Page, label: str) -> bool:
        """그 입력 자리가 여전히 화면에 있고 쓸 수 있는가 (판정축 ③ — form-input)."""
        box = page.get_by_label(label, exact=False).first
        return await box.count() > 0 and await box.is_editable()

    async def status_summary(self, page: Page) -> str:
        """화면이 지금 무엇을 보여 주고 있는지 모은다.

        오류 통로가 있으면 그것이 우선이다. 없으면 상태 표시(`role=alert`·`role=status`)
        와 **지금 화면의 상태 문구**를 모은다 — 거부가 아닌 시나리오에서 재는 것은
        "화면이 멈추지 않고 지금 상태를 보여 주는가" 이므로 그것이 근거다.

        화면 전체 텍스트를 그대로 쓰지 않는다. 상태를 말하는 자리만 모으고, 그것마저
        없으면 빈 문자열이 되어 판정축 ②가 잡는다.
        """
        body = await self.notice(page)
        if body is not None:
            return f"{body['message']} {body['next_action']}".strip()

        parts: list[str] = []
        for selector in ('[role="alert"]', '[role="status"]', "h1", "h2", "strong", "code"):
            nodes = page.locator(selector)
            for i in range(min(await nodes.count(), 12)):
                text = (await nodes.nth(i).inner_text()).strip()
                if text:
                    parts.append(text)

        # **이어서 할 수 있는 것이 있는가.** 거부가 아닌 시나리오에서 판정축 ②가 재는
        # 것은 "화면이 멈추지 않았는가" 다. 눌러서 진행할 수 있는 조작이 하나도 없으면
        # 화면이 멈춘 것이고, 그때 이 값은 비어 판정축 ②가 잡는다.
        parts.extend(
            await page.evaluate(
                """() => {
                    const out = [];
                    for (const b of document.querySelectorAll("button")) {
                        if (b.disabled) continue;
                        const text = (b.textContent || b.getAttribute("aria-label") || "").trim();
                        if (text && out.length < 10) out.push(text);
                    }
                    return out;
                }"""
            )
        )
        return " / ".join(dict.fromkeys(parts))[:600]

    async def status_note(self, page: Page) -> str:
        """화면이 스스로 붙인 안내(`role="status"`·`role="alert"`)를 읽는다.

        오류 통로가 있으면 그것이 우선이다. 없을 때 화면이 "지금 이건 안 된다" 를
        말하는 자리가 이곳이다 — 없으면 빈 문자열이 되어 판정축 ②가 잡는다.
        """
        body = await self.notice(page)
        if body is not None:
            return f"{body['message']} {body['next_action']}".strip()
        parts: list[str] = []
        for selector in ('[role="status"]', '[role="alert"]'):
            nodes = page.locator(selector)
            for i in range(min(await nodes.count(), 8)):
                text = (await nodes.nth(i).inner_text()).strip()
                if text:
                    parts.append(text)
        return " / ".join(dict.fromkeys(parts))[:600]

    async def key_status_summary(self, page: Page) -> str:
        """키 화면이 "키가 없다" 를 말하고 있는가."""
        hits = [t for t in await self.leaf_texts(page) if "키" in t]
        return " / ".join(dict.fromkeys(hits))[:600]

    async def result_summary(self, page: Page) -> str:
        """결과 화면이 산출물이 없다는 사실을 말하고 있는가."""
        hits = [
            t
            for t in await self.leaf_texts(page)
            if any(w in t for w in ("없", "산출물", "스크린샷", "결과", "실패"))
        ]
        return " / ".join(dict.fromkeys(hits))[:600]

    async def target_summary(self, page: Page) -> str:
        """Step 상세가 후보 상태를 말하고 있는가."""
        hits = [
            t
            for t in await self.leaf_texts(page)
            if any(w in t for w in ("후보", "확인 필요", "다시 집기", "없음", "쓸 수 없"))
        ]
        return " / ".join(dict.fromkeys(hits))[:600]

    # ─── 화면 이동 ──────────────────────────────────────────────────────────

    async def open_definition(self, page: Page, name: str) -> bool:
        """목록에서 그 테스트의 정의 화면으로 들어간다. ⋮ 메뉴 → 정의 보기."""
        menu = page.get_by_role("button", name=f"{name} 추가 동작", exact=False).first
        if await menu.count() == 0:
            return False
        await menu.click(timeout=ACT_TIMEOUT_MS)
        opened = await self.click_if_present(page, "정의 보기")
        await self.settle(page, ms=800)
        return opened

    async def open_result(self, page: Page) -> bool:
        """실패한 테스트의 결과 화면으로 들어간다. 버튼이 없으면 그 사실을 돌려준다."""
        return await self.click_if_present(page, "결과 보기")

    async def delete_from_list(self, page: Page, name: str) -> bool:
        """목록에서 그 테스트를 지운다. ⋮ 메뉴 → 삭제 → 확인.

        **확인 버튼도 "삭제" 다.** 메뉴 항목과 이름이 같아 하나만 누르면 확인 상자가
        열린 채로 남는다 — 그 상태를 "지웠다" 로 세면 아무것도 재지 못한다.
        """
        menu = page.get_by_role("button", name=f"{name} 추가 동작", exact=False).first
        if await menu.count() == 0:
            return False
        await menu.click(timeout=ACT_TIMEOUT_MS)
        if not await self.click_if_present(page, "삭제"):
            return False
        # 확인 상자의 삭제. 목록 항목이 사라졌으므로 이제 "삭제" 는 확인 버튼 하나다.
        confirmed = await self.click_if_present(page, "삭제")
        await self.settle(page, ms=800)
        return confirmed

    async def start_session_from_ui(self, page: Page, start_url: str) -> str:
        """화면에서 녹화 세션을 시작하고 그 식별자를 얻는다.

        화면에는 주소가 없다 — 상태로 화면을 고르므로 세션 화면에 URL 로 들어갈 수
        없다. 그래서 **화면이 실제로 만든** 세션의 식별자를 응답에서 읽는다.
        """
        await self.click(page, "테스트 만들기")
        await self.fill(page, "시작 URL", start_url)
        async with page.expect_response(
            lambda r: r.url.rstrip("/").endswith("/api/sessions") and r.request.method == "POST",
            timeout=60_000,
        ) as info:
            await self.click(page, "녹화 시작")
        resp = await info.value
        body = await resp.json()
        assert "session_id" in body, f"세션을 만들지 못했다: {body}"
        return str(body["session_id"])

    # ─── 결과 만들기 ────────────────────────────────────────────────────────

    async def from_screen(
        self,
        page: Page,
        *,
        rejected: bool,
        preserved: bool | None = None,
        prevented: bool = False,
        surfaced: str | None = None,
    ) -> Attempt:
        """화면에서 읽은 것으로 판정 대상을 만든다.

        `surfaced` 를 주지 않으면 오류 통로의 문구를 쓴다. 화면 전체 텍스트를 넣지
        않는다 — 그러면 무엇이 보이든 판정축 ②가 통과해 아무것도 재지 못한다.
        """
        body = await self.notice(page)
        if surfaced is None and body is not None:
            surfaced = f"{body['message']} {body['next_action']}".strip()
        return Attempt(
            rejected=rejected,
            error=body,
            surfaced=surfaced,
            preserved=preserved,
            prevented=prevented,
            crashed=bool(body and body["category"] == "broken"),
        )
