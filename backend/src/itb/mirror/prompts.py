"""브라우저 요구 가로채기 (010 T057~T059 · FR-337~FR-339 · research R6·R7).

**대상 브라우저가 사용자에게 요구하는 것 중 페이지 화면이 아닌 것**을 다룬다 —
`alert`·`confirm`·`prompt` 대화상자와 파일 선택이다. 미러는 페이지 화면을 그리므로 이것들은
거기 나타나지 않는다. 창을 띄우던 때는 운영체제가 대신 보여 줬고, 창이 없으면 그것도 없다.

**가로채지 않으면 대상 페이지가 멈춘다** (research R7). 대화상자는 응답이 올 때까지
페이지를 세우고, 헤드리스에서는 화면에도 나타나지 않는다 — 사용자에게는 「클릭했는데 아무
일도 없다」로 보인다. 그것이 FR-339 가 금지하는 조용한 실패다. 그래서 이 모듈은 조작
국면에서 **항상 켜져 있어야 한다.**

**처리할 수 없는 것은 처리할 수 없다고 말한다** (FR-339). 인증 요구 팝업처럼 제품이 대신
받을 수단이 없는 요구는 `unsupported` 로 알리고 폴백을 제시한다 — 무엇이 막혔는지 말하는
것까지가 이번 범위다 (research 미해결 항목).

**이 모듈은 Step 을 만들지 않는다.** 대화상자 응답은 브라우저 수준의 사건이고, 페이지에
생기는 결과는 리코더가 평소대로 잡는다 (헌법 원칙 I).
"""

from __future__ import annotations

import asyncio
import contextlib
import secrets
from dataclasses import dataclass, field
from typing import Any

DIALOG_KINDS = {
    "alert": "dialog.alert",
    "confirm": "dialog.confirm",
    "prompt": "dialog.prompt",
    "beforeunload": "dialog.confirm",
}
"""Playwright 의 대화상자 종류 → 계약의 `kind` (data-model §4).

`beforeunload` 를 `confirm` 으로 접는 이유는 사용자가 고를 것이 같기 때문이다 — 떠날
것인가 남을 것인가. 별도 종류로 두면 화면이 그 하나를 위해 다른 문구를 갖게 되고,
사용자는 같은 선택을 두 모양으로 만난다.
"""


@dataclass(slots=True)
class PendingPrompt:
    """응답을 기다리는 요구 하나 (data-model §4)."""

    prompt_id: str
    kind: str
    message: str
    multiple: bool = False
    blocking: bool = True
    _resolve: Any = None
    """실제 응답 통로. 대화상자면 Playwright `Dialog`, 파일 선택이면 `FileChooser`."""


@dataclass
class BrowserPrompts:
    """한 세션의 브라우저 요구. 가로채고, 알리고, 응답을 전달한다.

    **가로채기는 컨텍스트 단위로 건다.** 새 탭에도 자동으로 붙는다 — 리코더가
    `add_init_script` 를 컨텍스트에 거는 것과 같은 이유이고, 탭마다 걸면 한 탭이 빠진다.
    """

    emit: Any
    """이벤트 통로. `(event_type, **payload)` 를 받는다."""

    pending: dict[str, PendingPrompt] = field(default_factory=dict)
    _attached: bool = False

    def attach(self, context: Any) -> None:
        """가로채기를 건다. 이미 걸려 있으면 아무것도 하지 않는다.

        **조작 국면에서 항상 켜져 있어야 한다** (research R7). 켜지 않으면 대화상자가
        페이지를 세우고, 헤드리스에서는 그 사실이 어디에도 나타나지 않는다.
        """
        if self._attached:
            return
        self._attached = True
        context.on("dialog", self._on_dialog)
        context.on("page", self._on_page)
        for page in getattr(context, "pages", []) or []:
            self._on_page(page)

    def _on_page(self, page: Any) -> None:
        """새 탭에 파일 선택 가로채기를 건다.

        파일 선택은 **페이지 단위 이벤트**다 — 대화상자와 달리 컨텍스트에 걸 수 없다.
        그래서 탭이 열릴 때마다 붙인다.
        """
        with contextlib.suppress(Exception):
            page.on("filechooser", self._on_file_chooser)

    # ─── 가로채기 ──────────────────────────────────────────────────────────

    def _on_dialog(self, dialog: Any) -> None:
        """대화상자를 가로채 알린다 (FR-338 · research R7).

        **자동으로 닫지 않는다.** 닫으면 사용자가 고를 기회를 잃고, 그 선택은 대상
        페이지의 다음 화면을 정한다 — 제품이 대신 고르면 녹화된 것은 사용자가 하려던
        것과 다른 흐름이다.
        """
        kind = DIALOG_KINDS.get(str(getattr(dialog, "type", "") or ""), "dialog.alert")
        prompt = PendingPrompt(
            prompt_id=_new_id(),
            kind=kind,
            message=str(getattr(dialog, "message", "") or ""),
            blocking=True,
            _resolve=dialog,
        )
        self._announce(prompt)

    def _on_file_chooser(self, chooser: Any) -> None:
        """파일 선택 요구를 가로채 알린다 (FR-337 · research R6).

        **운영체제 창은 뜨지 않는다.** 헤드리스에서 파일 선택 요소를 클릭하면 이 이벤트만
        발생하고, 제품 화면이 파일을 고를 수단을 대신 제시한다 — 그것이 화면 없는 기계에서
        파일 첨부 녹화가 성립하는 이유다 (SC-518).
        """
        prompt = PendingPrompt(
            prompt_id=_new_id(),
            kind="file.choose",
            message="",
            multiple=bool(getattr(chooser, "is_multiple", lambda: False)()),
            # 파일 선택은 페이지를 세우지 않는다 — 사용자가 고르지 않아도 페이지는 돈다.
            blocking=False,
            _resolve=chooser,
        )
        self._announce(prompt)

    def announce_unsupported(self, what: str, remedy: str) -> None:
        """제품이 대신 받을 수 없는 요구를 알린다 (FR-339).

        **조용히 아무 일도 일어나지 않게 두지 않는다.** 무엇이 막혔는지와 어떤 수단이
        남아 있는지를 담는다 — 화면은 그 자리에서 실제 창으로 전환할 수 있어야 한다
        (FR-353a).

        인증 요구 팝업이 이 경로의 대표다. 처리 자체는 이번 범위 밖이고, **말하는 것까지**
        가 범위다 (research 미해결 항목).
        """
        prompt = PendingPrompt(
            prompt_id=_new_id(),
            kind="unsupported",
            message=f"{what} 제품 화면이 대신 받을 수 없습니다. {remedy}",
            blocking=False,
            _resolve=None,
        )
        self._announce(prompt)

    def _announce(self, prompt: PendingPrompt) -> None:
        self.pending[prompt.prompt_id] = prompt
        # CDP·Playwright 이벤트 핸들러는 동기 호출이므로 태스크로 넘긴다.
        with contextlib.suppress(RuntimeError):
            asyncio.create_task(  # noqa: RUF006
                self.emit(
                    "browser_prompt",
                    promptId=prompt.prompt_id,
                    kind=prompt.kind,
                    message=prompt.message,
                    multiple=prompt.multiple,
                    blocking=prompt.blocking,
                )
            )

    # ─── 응답 ──────────────────────────────────────────────────────────────

    async def answer(
        self,
        prompt_id: str,
        *,
        accept: bool = True,
        text: str | None = None,
        paths: list[str] | None = None,
    ) -> bool:
        """사용자의 선택을 대상에 전달한다 (FR-338·FR-340).

        **이미 해소된 요구는 거절한다** (`False` 를 돌려준다). 두 번 응답하면 Playwright 가
        예외를 내고, 그 예외는 사용자에게 아무것도 설명하지 못한다.

        `prompt_id` 는 이 세션의 사전에서만 찾는다 — 다른 세션의 식별자는 여기 없다.
        그 격리가 검사가 아니라 **구조**로 성립한다 (FR-340).
        """
        prompt = self.pending.pop(prompt_id, None)
        if prompt is None:
            return False

        resolver = prompt._resolve
        try:
            if prompt.kind == "file.choose" and resolver is not None:
                # 고르지 않겠다는 선택도 응답이다. 빈 목록을 보내면 대상 페이지는
                # 「선택 없음」으로 읽고 계속 간다.
                await resolver.set_files(paths or [])
            elif prompt.kind.startswith("dialog.") and resolver is not None:
                if accept:
                    await resolver.accept(text or "")
                else:
                    await resolver.dismiss()
        except Exception:  # noqa: BLE001, S110 - 응답 실패가 실행을 실패시키지 않는다 (FR-348).
            # 사유를 남기지 않는 것도 의도다: 이미 닫힌 대화상자에 답하려는 것이 가장 흔한
            # 경우이고, 그것은 결함이 아니라 경합이다. 로그를 채워 정작 봐야 할 실행 로그를
            # 밀어내지 않는다 (`screencast._idle_loop` 와 같은 판단).
            pass
        finally:
            await self._resolved(prompt_id)
        return True

    async def _resolved(self, prompt_id: str) -> None:
        with contextlib.suppress(Exception):
            await self.emit("browser_prompt_resolved", promptId=prompt_id)

    async def dismiss_all(self, reason: str) -> None:
        """남은 요구를 정리한다. 세션이 끝날 때 부른다.

        **대상 페이지를 세운 채로 두지 않는다.** 가로챈 대화상자를 응답 없이 버리면 그
        페이지는 영원히 멈춰 있고, 그 상태는 세션을 닫는 경로에서 시간 초과로 나타난다.
        """
        for prompt_id in list(self.pending):
            await self.answer(prompt_id, accept=False)
        if reason:
            with contextlib.suppress(Exception):
                await self.emit("browser_prompt_resolved", promptId="*", reason=reason)


def _new_id() -> str:
    return f"p_{secrets.token_hex(4)}"
