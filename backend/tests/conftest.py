"""통합·종단 테스트 공용 픽스처.

픽스처 앱을 띄우고, 프로젝트를 만들고, TestClient 를 준비한다.
픽스처 앱이 없으면 테스트를 건너뛰지 않고 **명확한 사유로 실패**한다 — 조용히 건너뛰면
검증하지 않은 것을 통과로 오인한다 (헌법 품질 게이트 4).
"""

from __future__ import annotations

import os
import pathlib
import socket
import subprocess
import sys
import time
from collections.abc import Iterator
from urllib.request import urlopen

import pytest
from fastapi.testclient import TestClient

from tests.tiers import HEAVY_FIXTURES, TIMING_MODULES

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
FIXTURE_APP = REPO_ROOT / "fixtures" / "sample-app" / "serve.py"
STARTUP_TIMEOUT_S = 20.0


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """실제 스택을 지나는 검증에 `browser` 마커를 **자동으로** 붙인다.

    파일 90개에 손으로 마커를 달면 새 파일에서 잊는다. 잊은 것은 조용히 빠른 계층에
    섞여 개발 루프를 다시 느리게 만들고, 그 원인은 드러나지 않는다. 그래서 판정을
    한곳에서 한다 — **무거운 픽스처를 요구하면 실제 스택을 지난다.**

    `fixturenames` 는 간접 의존까지 포함하므로 `keyed_client` 처럼 픽스처 앱을 거쳐
    가는 것도 함께 걸린다.

    쓰임:
        uv run pytest -m "not browser"   # 개발 루프 (브라우저·npm 없음)
        uv run pytest                    # 전량 (커밋·CI)
    """
    for item in items:
        if HEAVY_FIXTURES & set(getattr(item, "fixturenames", ())):
            item.add_marker(pytest.mark.browser)
        rel = item.path.relative_to(REPO_ROOT / "backend").as_posix()
        if rel in TIMING_MODULES:
            item.add_marker(pytest.mark.timing)


@pytest.fixture(autouse=True)
def _timing_needs_one_process(request: pytest.FixtureRequest) -> None:
    """시간을 재는 검증이 **병렬 실행에 섞이면** 사유와 함께 실패한다.

    섞인 채 돌면 실패 메시지가 "지연 p95 737ms 가 목표 200ms 를 넘었다" 로 나온다.
    그것을 읽은 사람은 제품이 느려졌다고 판단하고 있지도 않은 회귀를 찾는다. 실제
    원인은 프로세스 8개가 CPU 를 나눠 쓴 것이다.

    건너뛰지 않는다 — 건너뛰면 재지 않은 것이 통과로 보인다 (헌법 품질 게이트 4).
    """
    if not request.node.get_closest_marker("timing"):
        return
    worker_input = getattr(request.config, "workerinput", None)
    workers = int(worker_input["workercount"]) if worker_input else 1
    if workers > 1:
        pytest.fail(
            f"시간을 재는 검증입니다 — 프로세스 {workers}개로는 재는 값이 그 순간의 "
            "부하가 됩니다. `-n 0` 을 붙이거나 `scripts/test-backend.sh` 로 돌리세요."
        )


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


@pytest.fixture(scope="session")
def fixture_app() -> Iterator[str]:
    """검증용 대상 웹 앱. 세션 동안 한 번 띄운다."""
    if not FIXTURE_APP.exists():
        pytest.fail(f"픽스처 앱이 없습니다: {FIXTURE_APP}")

    port = _free_port()
    proc = subprocess.Popen(  # noqa: S603 - 저장소 안의 알려진 스크립트
        [sys.executable, str(FIXTURE_APP), "--port", str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    base = f"http://127.0.0.1:{port}"
    deadline = time.monotonic() + STARTUP_TIMEOUT_S
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            err = (proc.stderr.read().decode() if proc.stderr else "")[:400]
            pytest.fail(f"픽스처 앱이 종료됐습니다: {err}")
        try:
            with urlopen(f"{base}/login.html", timeout=0.5) as resp:  # noqa: S310
                if resp.status == 200:
                    break
        except OSError:
            time.sleep(0.2)
    else:
        proc.terminate()
        pytest.fail(f"픽스처 앱이 {STARTUP_TIMEOUT_S}초 안에 뜨지 않았습니다.")

    try:
        yield base
    finally:
        proc.terminate()
        proc.wait(timeout=5)


@pytest.fixture(autouse=True)
def _headless_browsers(monkeypatch: pytest.MonkeyPatch) -> None:
    """검증은 **언제나 창 없이** 브라우저를 띄운다.

    제품 기본값은 창을 띄우는 것이다 — 녹화·인수인계는 사람이 조작하는 국면이므로
    옳다 (clarify 결정 3). 하지만 검증이 그 기본값을 그대로 지나면 매 세션마다 창이
    떠서 **개발자의 화면을 빼앗는다.** 전량 실행은 브라우저 세션을 60번 가까이 만들고,
    그동안 다른 작업을 할 수 없다. 초점이 옮겨 가면 `blur` 에 기대는 녹화 검증이
    엉뚱한 사유로 실패하기도 한다.

    개발자가 셸에 `ITB_HEADLESS=0` 을 켜 둔 채 돌려도 여기서 덮는다 — 검증에서 창을
    보고 싶은 경우는 사람이 직접 한 세션을 여는 것이고, 그것은 전량 실행이 아니다.

    창 없이 돌아도 검증하는 것은 같다. 스크린캐스트·recorder.js 주입·hover·끌어다
    놓기 모두 headless 에서 동작한다.
    """
    from itb.execution.session import HEADLESS_ENV

    monkeypatch.setenv(HEADLESS_ENV, "1")


@pytest.fixture(autouse=True)
def _cheap_key_derivation(request: pytest.FixtureRequest) -> Iterator[None]:
    """암호구 파생 비용을 테스트에서 **싼 프로필**로 내린다.

    제품 기본값은 argon2id MODERATE 다 — 회당 약 2.7초. 그 비용은 사람의 비밀키를
    지키기 위한 것이고 제품에서는 옳지만, 테스트가 확인하는 성질(파생 → 봉인 → 개봉이
    맞물리는지, 틀린 암호구가 복호화 실패와 구분되는지)은 비용에 달려 있지 않다.
    측정 결과 이 한 가지가 unit·contract 수행 시간의 절반을 차지했다.

    **파생을 건너뛰지 않는다.** INTERACTIVE 도 진짜 argon2id 파생이다. 값만 싸다.
    제품 기본값이 MODERATE 임은 `test_secrets.py::test_product_derivation_cost_is_moderate`
    가 못 박는다 — 여기서 낮춘 것이 제품으로 새지 않게 하는 잠금이다.

    제품 값 그대로 지나야 하는 테스트는 `@pytest.mark.production_kdf` 를 붙인다.
    """
    if request.node.get_closest_marker("production_kdf"):
        yield
        return

    from nacl import pwhash

    from itb.secrets import keys

    # monkeypatch 픽스처를 쓰지 않는다 — 그것은 함수 스코프이고 이 픽스처도 그렇지만,
    # 여기서 직접 세우고 되돌리면 실패한 테스트가 남긴 상태가 다음으로 새지 않는다.
    saved = (keys.KDF_OPSLIMIT, keys.KDF_MEMLIMIT)
    keys.KDF_OPSLIMIT = pwhash.argon2id.OPSLIMIT_INTERACTIVE
    keys.KDF_MEMLIMIT = pwhash.argon2id.MEMLIMIT_INTERACTIVE
    try:
        yield
    finally:
        keys.KDF_OPSLIMIT, keys.KDF_MEMLIMIT = saved


@pytest.fixture(autouse=True)
def _default_ai_driver(monkeypatch: pytest.MonkeyPatch) -> None:
    """테스트는 **언제나 기본 드라이버(Messages API)를 지난다.**

    개발자가 셸에 `ITB_AI_DRIVER=claude-code` 를 켜 둔 채 pytest 를 돌리면, 가짜 모델이
    받는 도구 표면이 MCP 쪽으로 바뀌어 `tool.call(...)` 대본이 통째로 무너진다. 그 실패는
    원인이 환경 변수라는 것을 드러내지 않는다 — 그래서 여기서 지운다.
    """
    monkeypatch.delenv("ITB_AI_DRIVER", raising=False)


def pin_playwright_browsers(monkeypatch: pytest.MonkeyPatch) -> None:
    """`HOME` 을 바꾸기 **전에** Playwright 브라우저 캐시 위치를 고정한다.

    Playwright 는 설치된 브라우저를 `HOME` 기준으로 찾는다. 홈을 임시 경로로 돌리면
    브라우저가 없다며 실패한다 — 테스트가 검증하려는 것과 무관한 실패다.

    이미 지정돼 있으면 존중한다 (CI 가 캐시를 따로 두는 경우).
    """
    if os.environ.get("PLAYWRIGHT_BROWSERS_PATH"):
        return

    real_home = pathlib.Path(os.path.expanduser("~"))
    cache = (
        real_home / "Library" / "Caches" / "ms-playwright"
        if sys.platform == "darwin"
        else real_home / ".cache" / "ms-playwright"
    )
    if cache.is_dir():
        monkeypatch.setenv("PLAYWRIGHT_BROWSERS_PATH", str(cache))


@pytest.fixture
def isolated_home(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> pathlib.Path:
    """사용자 홈을 임시 경로로 돌린다.

    002 부터 프로젝트가 **도구가 관리하는 위치**(`~/.local/share/itb/projects/`)에
    만들어지고 레지스트리가 `~/.config/itb/` 에 쌓인다 (DR-006). 격리하지 않으면
    테스트가 개발자의 실제 홈에 프로젝트를 남긴다.

    `HOME` 도 함께 돌린다 — `resolve_within_home` 의 경계가 `Path.home()` 이라,
    이것이 없으면 `tmp_path` 가 홈 밖이라 모든 열기가 거절된다.
    """
    pin_playwright_browsers(monkeypatch)

    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))
    monkeypatch.setenv("XDG_DATA_HOME", str(home / ".local" / "share"))
    return home


@pytest.fixture(autouse=True)
def _no_session_leaks_between_tests() -> Iterator[None]:
    """세션 작업 상태를 테스트마다 비운다.

    `routes/sessions._WORK` 는 **모듈 전역**이다. `client` 픽스처가 앱을 새로 만들어도
    그 사전은 프로세스 전체에서 하나이므로, 앞 테스트가 남긴 세션이 다음 테스트의
    `GET /api/sessions` 에 그대로 보인다 — "살아 있는 세션이 없다" 를 전제하는 검증이
    앞 테스트의 잔여물 때문에 실패한다.

    브라우저 정리는 앱의 lifespan 이 이미 맡는다. 여기서는 **사전만** 비운다 —
    닫힌 세션의 껍데기가 남아 있는 것이 문제다.
    """
    yield
    from itb.api.routes.sessions import _WORK

    _WORK.clear()


@pytest.fixture
def client(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, isolated_home: pathlib.Path
) -> Iterator[TestClient]:
    """앱 클라이언트. 키 디렉터리를 임시 경로로 돌려 사용자 홈을 건드리지 않는다."""
    from itb.api import state as state_mod
    from itb.api.app import create_app
    from itb.secrets.keys import KeyPaths

    app = create_app()
    with TestClient(app) as c:
        c.app.state.itb.key_paths = KeyPaths(tmp_path / "keys")
        monkeypatch.setattr(state_mod, "BIND_HOST", "127.0.0.1", raising=False)
        yield c


@pytest.fixture
def project_client(client: TestClient, fixture_app: str) -> TestClient:
    """프로젝트가 열린 클라이언트.

    `path` 를 보내지 않는다 — 002 에서 제거됐다 (DR-001). 사용자가 서버의 실행 경로를
    알 수 없으므로 위치를 묻지 않고 도구가 정한다.
    """
    resp = client.post(
        "/api/project/create",
        json={
            "name": "픽스처 프로젝트",
            "default_start_url": f"{fixture_app}/login.html",
        },
    )
    assert resp.status_code == 201, resp.text
    return client


# ─── US2 (재실행) 공용 픽스처 ──────────────────────────────────────────────


@pytest.fixture
def keyed_client(project_client: TestClient) -> TestClient:
    """비밀키가 준비된 클라이언트. 민감 값 봉인·복호화 경로를 지나는 테스트용."""
    resp = project_client.post("/api/keys/generate", json={"passphrase": None})
    assert resp.status_code == 201, resp.text
    return project_client


@pytest.fixture
def event_log(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, dict]]:
    """세션이 발행한 모든 이벤트를 순서대로 담는다.

    WebSocket 을 열어 읽지 않고 **발행 지점**에서 가로챈다. 세션 생성 즉시 실행이 시작되는
    재실행 모드에서는 소켓을 붙이는 사이에 앞부분 이벤트를 놓칠 수 있기 때문이다.
    소켓 계층(`seq` 부여·유실 허용)은 contract 테스트가 따로 본다.
    """
    from itb.api.ws.session_events import EventBroker

    captured: list[tuple[str, dict]] = []
    original = EventBroker.sink

    def patched(self: EventBroker, session_id: str):  # noqa: ANN202
        inner = original(self, session_id)

        async def send(event_type: str, payload: dict) -> None:
            captured.append((event_type, dict(payload)))
            await inner(event_type, payload)

        return send

    monkeypatch.setattr(EventBroker, "sink", patched)
    return captured
