"""실행 산출물 수집. FR-052·FR-053·FR-089d.

콘솔 기록과 네트워크 기록은 **실행 내내** 모으고, 스크린샷은 **실패 시점**에 찍는다.

**디스크에 쓰기 직전에 스크러버를 통과한다** (FR-089d, research R7). 마스킹을 수집 시점에
하지 않는 이유는, 어떤 값이 민감한지는 그 값이 복호화된 뒤에야 알 수 있기 때문이다 —
수집은 계속 돌고 있고, 마스킹 대상 집합은 실행 도중 늘어난다.

**스크린샷은 텍스트 치환을 하지 않는다.** PNG 바이트를 문자열로 바꿔 치환하면 파일이
깨진다. 대신 기록 직전에 민감 값이 들어 있는지 검사하고, 들어 있으면 **쓰지 않는다** —
깨진 파일을 남기거나 값을 남기는 것보다 낫다.
"""

from __future__ import annotations

import contextlib
import pathlib
import shutil
from dataclasses import dataclass, field
from datetime import UTC, datetime

from playwright.async_api import BrowserContext, ConsoleMessage, Page, Request, Response

from itb.secrets.scrubber import Scrubber

MAX_RECORDS = 2000
"""한 실행에서 보관하는 기록 수 상한. 넘으면 오래된 것을 버린다.

무제한으로 모으면 오래 도는 테스트에서 메모리가 계속 늘어난다. 진단에 쓰이는 것은
실패 근처의 기록이므로 최근 것을 남긴다.
"""

SCREENSHOT_NAME = "failure.png"
CONSOLE_NAME = "console.log"
NETWORK_NAME = "network.log"

STEP_SHOTS_DIR = "steps"
"""Step 별 화면이 쌓이는 하위 디렉터리 (011 FR-389). `.runs/<테스트ID>/steps/<index>.png`.

**보관 정책을 새로 만들지 않았다.** `.runs/<테스트ID>/` 는 이미 테스트당 하나이고
「최근 1건만」이다 (`storage/repository.py` 머리말). 실행 **시작 시** 이 디렉터리를 비우면
clarify 결정 3(테스트당 최근 실행 1회분)이 그대로 충족된다 — 장수 상한도, 보관 기간
장치도 필요 없다.

실행마다 Step 개수와 인덱스가 달라지므로 **덮어쓰기만으로는 부족하다.** Step 을 줄여
다시 돌리면 이전 실행의 높은 인덱스 파일이 남아, 사용자는 지금 실행에 없는 화면을 보게
된다.
"""


@dataclass(slots=True)
class ArtifactPaths:
    """결과에 기록할 산출물 경로. 프로젝트 루트 기준 상대 경로다.

    절대 경로를 넣으면 결과 파일이 장비에 묶이고 사용자 홈 경로가 노출된다.
    """

    failure_screenshot: str | None = None
    console_log: str | None = None
    network_log: str | None = None
    notes: list[str] = field(default_factory=list)
    """산출물을 남기지 못한 사유. 조용히 비우지 않는다."""


class ArtifactCollector:
    """한 실행의 콘솔·네트워크·스크린샷 수집기.

    컨텍스트 단위로 붙는다 — 새 탭에서 일어난 일도 자동으로 들어온다 (research R2).
    """

    def __init__(self, context: BrowserContext) -> None:
        self._context = context
        self._console: list[str] = []
        self._network: list[str] = []
        self._attached = False
        self.startup_notes: list[str] = []
        """실행이 **시작될 때** 생긴 산출물 사유 (011 FR-396c).

        `ArtifactPaths.notes` 는 실행이 끝나고 만들어지므로, 시작 시점의 사실(이전 실행
        화면을 지우지 못했다)을 담을 자리가 없었다. 조용히 넘기면 사용자는 지난 실행의
        화면을 이번 것으로 읽는다.
        """

    # ─── 수집 ───────────────────────────────────────────────────────────────

    def attach(self) -> None:
        """이벤트 청취를 시작한다. 청취 실패가 실행을 막지 않는다."""
        if self._attached:
            return
        self._attached = True
        with contextlib.suppress(Exception):
            self._context.on("console", self._on_console)
        with contextlib.suppress(Exception):
            self._context.on("response", self._on_response)
        with contextlib.suppress(Exception):
            self._context.on("requestfailed", self._on_request_failed)

    def _append(self, bucket: list[str], line: str) -> None:
        bucket.append(f"{datetime.now(UTC).isoformat()} {line}")
        if len(bucket) > MAX_RECORDS:
            del bucket[: len(bucket) - MAX_RECORDS]

    def _on_console(self, message: ConsoleMessage) -> None:
        with contextlib.suppress(Exception):
            self._append(self._console, f"[{message.type}] {message.text}")

    def _on_response(self, response: Response) -> None:
        with contextlib.suppress(Exception):
            self._append(
                self._network, f"{response.status} {response.request.method} {response.url}"
            )

    def _on_request_failed(self, request: Request) -> None:
        with contextlib.suppress(Exception):
            reason = request.failure or "실패"
            self._append(self._network, f"FAILED {request.method} {request.url} — {reason}")

    # ─── 기록 ───────────────────────────────────────────────────────────────

    async def write(
        self,
        run_dir: pathlib.Path,
        project_root: pathlib.Path,
        scrubber: Scrubber,
        failure_page: Page | None = None,
    ) -> ArtifactPaths:
        """산출물을 `run_dir` 에 쓰고 결과에 넣을 경로를 돌려준다.

        `failure_page` 가 있으면 그 화면의 스크린샷을 찍는다 (FR-052).
        """
        run_dir.mkdir(parents=True, exist_ok=True)
        paths = ArtifactPaths()
        # 011 — 시작 시점에 생긴 사유를 결과 산출물 기록에 함께 싣는다 (FR-396c).
        paths.notes.extend(self.startup_notes)

        paths.console_log = self._write_text(
            run_dir / CONSOLE_NAME, project_root, scrubber, self._console, paths
        )
        paths.network_log = self._write_text(
            run_dir / NETWORK_NAME, project_root, scrubber, self._network, paths
        )
        if failure_page is not None:
            paths.failure_screenshot = await self._write_screenshot(
                run_dir / SCREENSHOT_NAME, project_root, scrubber, failure_page, paths
            )
        return paths

    async def write_step_screenshot(
        self,
        run_dir: pathlib.Path,
        project_root: pathlib.Path,
        scrubber: Scrubber,
        page: Page,
        index: int,
    ) -> tuple[str | None, str | None]:
        """한 Step 이 끝난 시점의 화면을 쓴다 (011 FR-389). `(경로, 사유)` 를 돌려준다.

        **`_write_screenshot` 을 그대로 쓴다.** 민감 값 검사(`_contains_secret`)를 복제하면
        한쪽만 고쳐지는 날이 오고, 그날 평문 스크린샷이 디스크에 남는다. 실패 시점
        스크린샷과 같은 규칙·같은 코드다.

        사유를 `ArtifactPaths.notes` 가 아니라 **돌려주는** 이유: 그 자리는 실행 전체의
        산출물에 대한 것이고, 이것은 **그 Step** 의 사실이라 `StepResult` 에 붙어야 한다.
        결과 화면이 「이 Step 은 왜 화면이 없는가」를 그 행에서 말할 수 있어야 한다.
        """
        shots = run_dir / STEP_SHOTS_DIR
        try:
            shots.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            return None, f"화면을 담을 자리를 만들지 못했습니다: {exc}"

        # `notes` 를 빌려 쓰고 비운다 — 기존 함수의 사유 전달 통로가 그것뿐이다.
        sink = ArtifactPaths()
        path = await self._write_screenshot(
            shots / step_shot_name(index), project_root, scrubber, page, sink
        )
        if path is not None:
            return path, None
        return None, sink.notes[0] if sink.notes else "이 Step 의 화면을 남기지 못했습니다."

    def _write_text(
        self,
        path: pathlib.Path,
        project_root: pathlib.Path,
        scrubber: Scrubber,
        lines: list[str],
        paths: ArtifactPaths,
    ) -> str | None:
        body = "\n".join(lines)
        if not body:
            body = "(기록 없음)"
        try:
            path.write_text(scrubber.scrub(body) + "\n", encoding="utf-8")
        except OSError as exc:
            paths.notes.append(f"{path.name} 을 쓰지 못했습니다: {exc}")
            return None
        return _relative(path, project_root)

    async def _write_screenshot(
        self,
        path: pathlib.Path,
        project_root: pathlib.Path,
        scrubber: Scrubber,
        page: Page,
        paths: ArtifactPaths,
    ) -> str | None:
        try:
            data = await page.screenshot(type="png", timeout=5000)
        except Exception as exc:  # noqa: BLE001 - 화면이 이미 닫혔을 수 있다
            paths.notes.append(f"실패 시점 스크린샷을 찍지 못했습니다: {type(exc).__name__}")
            return None

        if _contains_secret(scrubber, data):
            # 치환하면 PNG 가 깨진다. 남기지 않고 사유를 기록한다 (FR-089d).
            paths.notes.append(
                "스크린샷에 민감 값 표현이 포함되어 저장하지 않았습니다."
            )
            return None

        try:
            path.write_bytes(data)
        except OSError as exc:
            paths.notes.append(f"스크린샷을 쓰지 못했습니다: {exc}")
            return None
        return _relative(path, project_root)


def clear_step_screenshots(run_dir: pathlib.Path) -> str | None:
    """실행 **시작 시** Step 화면 디렉터리를 비운다 (011 FR-396a).

    이것이 「테스트당 최근 실행 1회분만 보관」의 전부다 (clarify 결정 3). `.runs/<ID>/` 가
    이미 테스트당 하나이므로, 이 한 줄이 실행 간 누적을 막는다.

    **덮어쓰기로는 부족하다.** 실행마다 Step 개수가 달라지므로, Step 을 줄여 다시 돌리면
    이전 실행의 높은 인덱스 파일이 남는다 — 사용자는 지금 실행에 없는 화면을 보게 된다.

    **실패해도 실행을 막지 않는다** (FR-396c). 사유를 돌려주고 호출자가 산출물 기록에
    남긴다 — 읽기 전용 디스크에서 실행 자체가 서면 고치려던 것보다 나쁘다.
    """
    shots = run_dir / STEP_SHOTS_DIR
    if not shots.exists():
        return None
    try:
        shutil.rmtree(shots)
    except OSError as exc:
        return f"이전 실행의 Step 화면을 지우지 못했습니다: {exc}"
    return None


def step_shot_name(index: int) -> str:
    """Step 인덱스 → 파일 이름. **0-기반이다** (저장·API·이벤트와 같다)."""
    return f"{index}.png"


def _contains_secret(scrubber: Scrubber, data: bytes) -> bool:
    """바이트 안에 민감 값 표현이 있는지 본다. 치환하지 않고 검사만 한다."""
    if not scrubber:
        return False
    text = data.decode("latin-1")  # 바이트를 1:1로 문자로 본다 — 손실이 없다
    return scrubber.scrub(text) != text


def _relative(path: pathlib.Path, project_root: pathlib.Path) -> str:
    try:
        return str(path.relative_to(project_root))
    except ValueError:  # pragma: no cover - run_dir 은 항상 프로젝트 안이다
        return str(path)
