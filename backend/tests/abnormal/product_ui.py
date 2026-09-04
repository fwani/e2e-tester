"""제품 UI 를 **실제로 띄우는** 검증 계층 (RG-105).

이 저장소에는 그동안 제품 화면을 실제로 여는 검증이 하나도 없었다.

- `backend/tests/e2e/` 는 이름과 달리 **요청 경계** 종단이다 (`TestClient` 인프로세스 호출).
  브라우저가 뜨긴 하지만 그것은 제품이 *대상 사이트*를 자동화하느라 여는 것이다
- `frontend/tests/` 는 화면 없는 환경에서 컴포넌트 하나씩을 그린다

그래서 아래를 판정할 수단이 없었다.

| 확인 | 시나리오 |
|---|---|
| 버튼 연타가 **실제로** 요청을 몇 번 내보내는가 | AS-024 (AP-022) |
| 화면을 벗어났다 돌아오면 무엇이 보이는가 | AS-026 (AP-023) |
| 두 창에서 같은 세션을 조작하면 어떻게 되는가 | AS-047 (AP-041) |
| 화면이 멈추는가 | 판정축 ② 전부 |

이 모듈이 제품 서버와 제품 화면을 띄우고 주소를 넘긴다. 화면 개발 서버 설정이 이미 `/api` 와
`/ws` 를 제품 서버로 넘기도록 되어 있어 설정을 바꾸지 않는다.

**도구나 포트가 없으면 건너뛰지 않고 실패한다** (RG-106). 조용한 건너뛰기는 "전건 통과"
(SC-201)를 거짓으로 만든다.
"""

from __future__ import annotations

import os
import pathlib
import shutil
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from dataclasses import dataclass
from urllib.error import URLError
from urllib.request import urlopen

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIR = REPO_ROOT / "frontend"

# 빈 포트를 골라 쓴다. 개발용 제품이 기본 포트에 떠 있어도 검증이 돌아가야 한다 —
# 화면 개발 서버가 `ITB_API_PORT`·`ITB_UI_PORT` 를 읽어 프록시 대상을 맞춘다.
HOST = "127.0.0.1"

BACKEND_TIMEOUT_S = 30.0
FRONTEND_TIMEOUT_S = 90.0  # 첫 변환이 오래 걸린다


@dataclass(frozen=True)
class ProductUI:
    """띄워진 제품. 화면 주소와 제품 서버 주소를 함께 넘긴다."""

    base_url: str
    """화면 주소. 브라우저가 이것을 연다."""

    api_url: str
    """제품 서버 주소. 화면을 거치지 않고 상태를 확인할 때 쓴다."""

    home: pathlib.Path
    """이 실행이 쓴 격리된 사용자 홈. 개발자의 실제 홈을 건드리지 않는다."""


def _free_port() -> int:
    with socket.socket() as s:
        s.bind((HOST, 0))
        return int(s.getsockname()[1])


def _wait_until_answers(url: str, proc: subprocess.Popen[bytes], timeout: float, what: str) -> None:
    deadline = time.monotonic() + timeout
    last: str = ""
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            err = (proc.stderr.read().decode(errors="replace") if proc.stderr else "")[-800:]
            pytest.fail(f"{what} 가 종료됐습니다 (코드 {proc.returncode}):\n{err}")
        try:
            with urlopen(url, timeout=1.0) as resp:  # noqa: S310 - 로컬 주소만 연다
                if resp.status < 500:
                    return
        except (URLError, OSError, TimeoutError) as exc:
            last = str(exc)
            time.sleep(0.3)
    proc.terminate()
    pytest.fail(f"{what} 가 {timeout}초 안에 응답하지 않았습니다 ({url}). 마지막 오류: {last}")


def _playwright_browser_cache() -> pathlib.Path | None:
    """`HOME` 을 돌리기 전에 브라우저 캐시 위치를 잡아 둔다.

    `tests/conftest.py` 의 같은 이름 함수와 목적이 같다. 여기서는 하위 프로세스 환경을
    만들어야 해서 monkeypatch 가 아니라 경로를 돌려준다.
    """
    if os.environ.get("PLAYWRIGHT_BROWSERS_PATH"):
        return pathlib.Path(os.environ["PLAYWRIGHT_BROWSERS_PATH"])
    real_home = pathlib.Path(os.path.expanduser("~"))
    cache = (
        real_home / "Library" / "Caches" / "ms-playwright"
        if sys.platform == "darwin"
        else real_home / ".cache" / "ms-playwright"
    )
    return cache if cache.is_dir() else None


def _require_preconditions() -> None:
    """없으면 **실패한다.** 건너뛰지 않는다 (RG-106)."""
    if shutil.which("npm") is None:
        pytest.fail(
            "npm 이 없어 제품 화면을 띄울 수 없습니다. 화면 면 시나리오 18건을 판정할 수단이 "
            "사라지므로 건너뛰지 않고 실패로 알립니다 (RG-106)."
        )
    if not (FRONTEND_DIR / "node_modules").is_dir():
        pytest.fail(f"프런트엔드 의존성이 설치되지 않았습니다. `cd {FRONTEND_DIR} && npm install`")
    if _playwright_browser_cache() is None:
        pytest.fail(
            "Playwright 브라우저가 설치되지 않았습니다. "
            "`cd backend && uv run playwright install chromium`"
        )


@pytest.fixture(scope="session")
def product_ui(tmp_path_factory: pytest.TempPathFactory) -> Iterator[ProductUI]:
    """제품 서버와 제품 화면을 띄우고 주소를 넘긴다. 세션 동안 한 번만 띄운다."""
    _require_preconditions()

    home = tmp_path_factory.mktemp("product-home")
    backend_port, frontend_port = _free_port(), _free_port()

    env = dict(os.environ)
    env.update(
        HOME=str(home),
        XDG_CONFIG_HOME=str(home / ".config"),
        XDG_DATA_HOME=str(home / ".local" / "share"),
        # 화면 개발 서버가 이 둘을 읽어 자기 포트와 프록시 대상을 맞춘다.
        ITB_API_PORT=str(backend_port),
        ITB_UI_PORT=str(frontend_port),
        PYTHONUNBUFFERED="1",
    )
    cache = _playwright_browser_cache()
    if cache is not None:
        env["PLAYWRIGHT_BROWSERS_PATH"] = str(cache)

    api_url = f"http://{HOST}:{backend_port}"
    base_url = f"http://{HOST}:{frontend_port}"

    backend = subprocess.Popen(  # noqa: S603 - 저장소 안의 알려진 진입점
        [
            sys.executable,
            "-m",
            "uvicorn",
            "itb.api.app:app",
            "--host",
            HOST,
            "--port",
            str(backend_port),
            "--log-level",
            "warning",
        ],
        cwd=BACKEND_DIR,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )

    frontend: subprocess.Popen[bytes] | None = None
    try:
        _wait_until_answers(f"{api_url}/api/health", backend, BACKEND_TIMEOUT_S, "제품 서버")

        frontend = subprocess.Popen(  # noqa: S603 - 저장소 안의 알려진 스크립트
            ["npm", "run", "dev", "--", "--port", str(frontend_port), "--strictPort"],  # noqa: S607
            cwd=FRONTEND_DIR,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        _wait_until_answers(base_url, frontend, FRONTEND_TIMEOUT_S, "제품 화면")

        yield ProductUI(base_url=base_url, api_url=api_url, home=home)
    finally:
        for proc in (frontend, backend):
            if proc is None:
                continue
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
