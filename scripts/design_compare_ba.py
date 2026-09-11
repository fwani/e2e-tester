#!/usr/bin/env python3
"""L2 대조 — **전환 전 화면과 전환 후 화면**을 렌더해서 잰다. 015 T013·T074 (FR-011 · SC-001).

## L1 과 무엇이 다른가

L1(`design_render.py`)은 **시트끼리** 비교한다 — 확정 디자인의 `<style>` 과 정본
`tokens.css` 를 같은 마크업에 각각 적용해 잰다. 그것이 보증하는 것은 「정본이 확정
디자인과 같다」이고, **화면이 그 정본을 제대로 쓰는지는 보지 못한다.**

015 는 바로 그 「쓰는 방법」을 통째로 바꾼다. 의미 클래스를 부품과 유틸리티로 풀고
인라인 배치를 클래스로 옮긴다. 정본은 한 글자도 안 바뀌므로 L1 은 내내 초록이고,
그러는 동안 화면이 조용히 달라질 수 있다 — 실제로 그랬다 (2026-09-11 「버튼과 글자가
모두 흰색」).

L2 는 **제품 화면 자체**를 전·후로 재서 그 구멍을 막는다.

    기준  전환 전 코드 (git worktree, merge-base) 를 빌드한 것
    관측  지금 코드를 빌드한 것

같은 백엔드·같은 데이터·같은 뷰포트에서 같은 화면을 열고, DOM 을 같은 순서로 훑어
`getComputedStyle` 을 읽는다. **마크업 구조는 015 가 건드리지 않으므로** 두 쪽의 요소가
1:1 로 짝지어진다. 짝이 어긋나면 그것 자체를 보고한다 (구조가 바뀌었다는 뜻이다).

## 왜 브라우저인가

L1 과 같은 이유다. 표기 차이(`#FFF` / `rgb(255,255,255)`)에 걸리지 않고, 캐스케이드와
레이어 순서를 브라우저가 실제로 풀어 준다 — 015 가 깨뜨린 것이 바로 그 순서였으므로
(`.bg-panel` 이 `.bg-ink` 를 이기는 것) 종이 위에서는 볼 수 없다.

## 데이터는 어디서 오나

임시 `XDG_DATA_HOME`·`XDG_CONFIG_HOME` 에 백엔드를 띄우고 거기에 시드를 심는다.
**사용자의 실제 프로젝트를 건드리지 않는다** — 읽지도 쓰지도 않고, 화면에 실제
프로젝트 이름이 나올 일도 없다.

백엔드는 이 분기에서 한 줄도 바뀌지 않았으므로 (`git diff backend` 가 비어 있다)
**한 인스턴스가 양쪽을 먹인다.** 데이터가 같음이 구조로 보장된다.

## 실행

    backend/.venv/bin/python scripts/design_compare_ba.py --baseline   # 전 쪽만 뜬다
    backend/.venv/bin/python scripts/design_compare_ba.py --compare    # 대조하고 보고서를 쓴다

`--compare` 는 불일치가 있으면 종료 코드 1 로 끝난다. 보고서는
`frontend/tests/l2-report.json` 에 쓰이고 양쪽 소스의 digest 를 함께 담는다 —
`frontend/tests/BeforeAfterParity.test.ts` 가 그 digest 로 **보고서가 낡았는지** 판정한다.
낡은 보고서로 통과할 수 없다.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import http.server
import json
import os
import shutil
import socket
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BEFORE_WT = ROOT / ".l2-before"
DATA_HOME = ROOT / ".l2-data"
REPORT = ROOT / "frontend" / "tests" / "l2-report.json"
BASELINE = ROOT / "frontend" / "tests" / "l2-baseline.json"
VENV_PY = ROOT / "backend" / ".venv" / "bin" / "python"

VIEWPORT = {"width": 1600, "height": 950}

# ── 무엇을 재는가 ──────────────────────────────────────────────────────────
# 시각 언어(색·타이포·모서리·그림자)와 배치(자리·크기)를 함께 본다. 015 는 둘 다
# 건드렸다 — 008 계약(시각)과 007 계약(배치)을 한꺼번에 옮기는 작업이기 때문이다.
PROPS = [
    # 색
    "color", "background-color",
    "border-top-color", "border-right-color", "border-bottom-color", "border-left-color",
    "outline-color",
    # 선과 모서리
    "border-top-width", "border-right-width", "border-bottom-width", "border-left-width",
    "border-top-style", "border-left-style",
    "border-radius", "outline-width", "outline-style", "box-shadow",
    # 타이포
    "font-family", "font-size", "font-weight", "font-style",
    "line-height", "letter-spacing", "text-transform", "text-align",
    "white-space", "text-overflow", "text-decoration-line",
    # 배치
    "display", "position", "flex-grow", "flex-shrink", "flex-basis",
    "flex-direction", "align-items", "justify-content", "gap",
    "grid-template-columns",
    "width", "height", "min-width", "min-height", "max-width",
    "padding-top", "padding-right", "padding-bottom", "padding-left",
    "margin-top", "margin-right", "margin-bottom", "margin-left",
    "overflow-x", "overflow-y", "opacity", "z-index", "visibility",
]

# ── 어느 화면을 대조하는가 ────────────────────────────────────────────────
# **무엇을 대조했는지가 기록으로 남아야 한다** (FR-011). 여기 없는 화면은 대조되지
# 않았다는 뜻이고, 보고서가 그 사실을 함께 싣는다.
#
# `steps` 는 화면에 닿기 위한 조작이다. 조작이 필요한 화면(폼·확인 상태)도 대조
# 대상이며, 조작 없이 닿는 화면만 보면 정작 상태가 있는 곳을 놓친다.
# `opened` 는 **프로젝트가 열린 상태에서 시작하는가**다. 열기는 서버가 기억하므로
# (`/api/health` 의 `project_open`), 한 화면에서 열면 그다음 화면은 이미 열린 채로
# 시작한다. 그 사실을 시나리오마다 적어 두지 않으면 순서에 따라 결과가 달라진다 —
# 1회차에 다섯 화면이 「열기 버튼이 없다」로 줄줄이 실패한 원인이 그것이었다.
SCENARIOS = [
    {"name": "project-list", "opened": False, "steps": []},
    {"name": "project-create", "opened": False, "steps": [{"button": "+ 새 프로젝트 만들기"}]},
    {"name": "test-list", "opened": True, "steps": []},
    {"name": "test-list-unrun", "opened": True, "steps": [{"button": "미실행"}]},
    {"name": "test-list-passed", "opened": True, "steps": [{"button": "통과"}]},
    {"name": "secrets", "opened": True, "steps": [{"button": "비밀 값"}]},
    {"name": "keys", "opened": True, "steps": [{"button": "키 관리"}]},
    {"name": "test-create", "opened": True, "steps": [{"button": "테스트 만들기"}]},
]

# **「기존 프로젝트 열기」는 일부러 뺐다.** 그 화면은 파일 탐색기이고 사용자의 홈
# 디렉터리 목록을 그린다 — 대조 보고서에 개인 경로가 남고, 기계마다 내용이 달라
# 재현되지도 않는다. 그 화면의 시각 회귀는 다른 화면과 같은 부품을 쓰므로 여기서
# 놓치는 것은 그 화면 고유의 배치뿐이다. 남은 몫은 손 검증에 있다
# (docs/PENDING-HUMAN-VERIFICATION.md).


# ── 의도된 차이 ───────────────────────────────────────────────────────────
# **불일치를 지우는 곳이 아니라 판단을 적는 곳이다** (T063 · SC-001). 여기 없는 차이는
# 전부 회귀로 본다. 이유 없이 등록할 수 없도록 `reason` 을 필수로 둔다.
INTENDED: list[dict[str, str]] = [
    {
        "screen": "test-create",
        "path": "BODY/DIV[0]/DIV[0]/DIV[0]/DIV[1]/DIV[0]",
        "reason": (
            "국면 표시가 `<div class=\"chip\">` 에서 부품 `ui/Chip` 으로 바뀌었고, 그 부품은 "
            "`<span>` 을 그린다. **계산된 스타일은 한 칸도 다르지 않다** — 요소 이름만 "
            "바뀌었고 둘 다 `inline-flex` 다. 칩은 글 안에 놓이는 표식이므로 `<span>` 이 "
            "맞는 요소이며, 검사와 실측은 클래스가 아니라 `data-phase-pill` 로 이 자리를 "
            "집는다. 사람이 보는 화면에는 차이가 없다 (SC-001)."
        ),
    },
]


def is_intended(m: dict) -> str | None:
    for row in INTENDED:
        if row["screen"] == m["screen"] and row.get("path") == m.get("path"):
            if "prop" not in row or row.get("prop") == m.get("prop"):
                return row["reason"]
    return None


def digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def source_digest(frontend: Path) -> str:
    """화면 코드와 테마의 digest. 이것이 바뀌면 보고서는 낡은 것이다."""
    parts: list[str] = []
    for rel in sorted((p for p in (frontend / "src").rglob("*") if p.suffix in {".tsx", ".ts", ".css"}), key=str):
        parts.append(str(rel.relative_to(frontend)))
        parts.append(rel.read_text(encoding="utf-8"))
    return digest("\n".join(parts))


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


# ── 전환 전 코드 ──────────────────────────────────────────────────────────


def merge_base() -> str:
    out = subprocess.run(
        ["git", "merge-base", "main", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True
    )
    return out.stdout.strip()


def ensure_before(rebuild: bool = False) -> Path:
    """전환 전 코드를 `git worktree` 로 꺼내 빌드한다 (research R5).

    **복사하지 않고 worktree 를 쓰는 이유**는 그것이 git 이 보증하는 그 시점의 트리이기
    때문이다. 손으로 되돌린 파일 묶음은 무엇이 빠졌는지 알 수 없다.
    """
    base = merge_base()
    if BEFORE_WT.exists() and rebuild:
        subprocess.run(["git", "worktree", "remove", "--force", str(BEFORE_WT)], cwd=ROOT, check=False)
    if not BEFORE_WT.exists():
        subprocess.run(
            ["git", "worktree", "add", "--detach", str(BEFORE_WT), base], cwd=ROOT, check=True
        )
    fe = BEFORE_WT / "frontend"
    modules = fe / "node_modules"
    if not modules.exists():
        modules.symlink_to(ROOT / "frontend" / "node_modules")
    dist = fe / "dist"
    if rebuild and dist.exists():
        shutil.rmtree(dist)
    if not (dist / "index.html").exists():
        # `tsc -b` 는 건너뛴다 — 옛 트리의 타입을 지금 다시 검사할 이유가 없고,
        # 재는 것은 산출물이다.
        subprocess.run(["npx", "vite", "build"], cwd=fe, check=True)
    return dist


def ensure_after() -> Path:
    dist = ROOT / "frontend" / "dist"
    subprocess.run(["npx", "vite", "build"], cwd=ROOT / "frontend", check=True)
    return dist


# ── 백엔드 ────────────────────────────────────────────────────────────────


def seed(data_home: Path) -> None:
    """대조용 프로젝트를 심는다. **사용자 자산을 건드리지 않는다.**

    화면이 비어 있으면 대조할 것도 없다. 목록 행·결말 표식·조작 단추가 나오도록
    결말이 서로 다른 테스트 넷을 넣는다 — 통과·실패·미실행·중지. 표식이 결말마다
    다른 것이 008 이 세운 규율이므로, 하나만 넣으면 나머지 셋의 회귀를 못 본다.
    """
    sys.path.insert(0, str(ROOT / "backend" / "src"))
    os.environ["XDG_DATA_HOME"] = str(data_home / "share")
    os.environ["XDG_CONFIG_HOME"] = str(data_home / "config")

    from itb.domain.test_case import Project, Test  # noqa: PLC0415
    from itb.storage.repository import ProjectRepository  # noqa: PLC0415
    from itb.storage import paths  # noqa: PLC0415

    root = paths.workspace_dir() / "l2-fixture"
    root.parent.mkdir(parents=True, exist_ok=True)
    repo = ProjectRepository.create(
        root,
        Project(name="대조용 프로젝트", default_start_url="http://127.0.0.1:4300/login.html"),
    )
    # Step 이 비면 도메인이 거절한다 (테스트는 적어도 하나의 동작을 갖는다).
    step = [{"type": "close_tab", "id": "step-01", "label": "탭 닫기"}]
    for number, name in enumerate(
        ["로그인이 된다", "비밀번호를 틀리면 막힌다", "장바구니에 담긴다", "결제가 끝난다"], start=1
    ):
        repo.write_test(
            Test(
                id=f"TC-{number:03d}",
                name=name,
                authoring_mode="record",
                start_url="http://127.0.0.1:4300/login.html",
                steps=step,  # type: ignore[arg-type]
            )
        )
    return None


def start_backend(data_home: Path) -> tuple[subprocess.Popen[bytes], str]:
    port = free_port()
    env = dict(os.environ)
    env["XDG_DATA_HOME"] = str(data_home / "share")
    env["XDG_CONFIG_HOME"] = str(data_home / "config")
    env["PYTHONPATH"] = str(ROOT / "backend" / "src")
    proc = subprocess.Popen(
        [str(VENV_PY), "-m", "uvicorn", "itb.api.app:app", "--host", "127.0.0.1", "--port", str(port)],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}"
    for _ in range(120):
        try:
            import urllib.request  # noqa: PLC0415

            urllib.request.urlopen(f"{base}/api/health", timeout=1).read()
            return proc, base
        except Exception:  # noqa: BLE001 — 아직 안 떴을 뿐이다
            time.sleep(0.25)
    proc.kill()
    raise SystemExit("백엔드가 뜨지 않았다")


def serve(directory: Path, backend: str) -> tuple[socketserver.TCPServer, str]:
    """SPA 정적 서버 + `/api` 역프록시.

    **같은 출처에서 내보내는 것이 요점이다.** 브라우저 쪽에서 요청을 가로채 다른
    출처로 돌리면 CORS 가 끼어들고, 그것은 재려는 것(화면의 모습)과 아무 상관이 없는
    실패다. 개발 서버(`vite.config.ts` 의 proxy)가 하는 일을 그대로 흉내 낸다.

    없는 경로는 `index.html` 로 돌린다 (클라이언트 라우팅).
    """

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a: object, **kw: object) -> None:
            super().__init__(*a, directory=str(directory), **kw)  # type: ignore[arg-type]

        def log_message(self, *a: object) -> None:  # 조용히
            return

        def _proxy(self, method: str) -> None:
            import urllib.error  # noqa: PLC0415
            import urllib.request  # noqa: PLC0415

            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else None
            req = urllib.request.Request(backend + self.path, data=body, method=method)
            for k, v in self.headers.items():
                if k.lower() not in {"host", "content-length", "connection"}:
                    req.add_header(k, v)
            try:
                with urllib.request.urlopen(req, timeout=30) as up:
                    payload, status, headers = up.read(), up.status, up.headers
            except urllib.error.HTTPError as exc:
                payload, status, headers = exc.read(), exc.code, exc.headers
            self.send_response(status)
            for k, v in headers.items():
                if k.lower() in {"content-type", "cache-control"}:
                    self.send_header(k, v)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self) -> None:  # noqa: N802
            if self.path.startswith("/api/"):
                self._proxy("GET")
                return
            super().do_GET()

        def do_POST(self) -> None:  # noqa: N802
            self._proxy("POST")

        def do_PUT(self) -> None:  # noqa: N802
            self._proxy("PUT")

        def do_PATCH(self) -> None:  # noqa: N802
            self._proxy("PATCH")

        def do_DELETE(self) -> None:  # noqa: N802
            self._proxy("DELETE")

        def send_head(self):  # type: ignore[no-untyped-def]
            path = self.translate_path(self.path)
            if not os.path.exists(path):
                self.path = "/index.html"
            return super().send_head()

    class Server(socketserver.ThreadingTCPServer):
        allow_reuse_address = True
        daemon_threads = True

    srv = Server(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


# ── 재기 ──────────────────────────────────────────────────────────────────

COLLECT_JS = """
(props) => {
  const out = [];
  const walk = (el, path) => {
    const style = getComputedStyle(el);
    const row = { path, tag: el.tagName };
    for (const p of props) row[p] = style.getPropertyValue(p);
    out.push(row);
    let i = 0;
    for (const child of el.children) {
      walk(child, `${path}/${child.tagName}[${i}]`);
      i += 1;
    }
  };
  walk(document.body, "BODY");
  return out;
}
"""


def open_project(backend: str) -> None:
    """프로젝트를 연다 — 화면의 조작이 아니라 API 로. 재는 것은 **그 뒤의 화면**이다."""
    import urllib.request  # noqa: PLC0415

    root = str(DATA_HOME / "share" / "itb" / "projects" / "l2-fixture")
    req = urllib.request.Request(
        backend + "/api/project/open",
        data=json.dumps({"path": root}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    urllib.request.urlopen(req, timeout=20).read()


def measure(page_url: str, backend: str, pw, scenarios: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    browser = pw.chromium.launch()
    ctx = browser.new_context(viewport=VIEWPORT)

    # 닫힌 상태의 화면을 먼저 전부 재고, 그다음 열고 나머지를 잰다. 순서를 고정해야
    # 양쪽이 같은 조건에서 재어진다.
    ordered = [s for s in scenarios if not s["opened"]] + [s for s in scenarios if s["opened"]]
    opened = False
    for sc in ordered:
        if sc["opened"] and not opened:
            open_project(backend)
            opened = True
        page = ctx.new_page()
        page.goto(page_url, wait_until="networkidle")
        page.wait_for_timeout(700)
        failed = None
        for step in sc["steps"]:
            # **역할로 집는다.** 글자로 집으면 그 글자를 품은 바깥 요소가 잡혀 눌러도
            # 아무 일이 없고, 검사는 「조작했다」고 믿은 채 같은 화면을 잰다. 1회차에
            # 화면 다섯이 전부 같은 32개 요소로 나온 원인이 그것이었다.
            loc = page.get_by_role("button", name=step["button"], exact=bool(step.get("exact"))).first
            try:
                loc.click(timeout=5000)
            except Exception as exc:  # noqa: BLE001
                failed = f"{step['button']}: {type(exc).__name__}"
                break
            page.wait_for_timeout(900)
        if failed is not None:
            print(f"  ! [{sc['name']}] 조작 실패 — {failed}")
            out[sc["name"]] = []
            page.close()
            continue
        out[sc["name"]] = page.evaluate(COLLECT_JS, PROPS)
        page.close()
    ctx.close()
    browser.close()
    return out


def collect(dist: Path, backend: str, pw) -> dict[str, list[dict]]:
    srv, url = serve(dist, backend)
    try:
        return measure(url, backend, pw, SCENARIOS)
    finally:
        srv.shutdown()


# ── 대조 ──────────────────────────────────────────────────────────────────


ZERO_SHADOW = "rgba(0, 0, 0, 0) 0px 0px 0px 0px"


def normalize(prop: str, value: str, row: dict | None = None) -> str:
    """**표기 차이를 지운다. 시각 차이는 지우지 않는다.**

    `box-shadow` 만 다룬다. Tailwind 의 그림자 유틸리티는 링·안쪽그림자·바깥그림자를
    한 속성에 **여러 겹**으로 싣고 쓰지 않는 겹은 투명 0 으로 채운다. 그래서 정본의
    `0 1px 2px rgba(20,23,28,.07)` 이

        rgba(0,0,0,0) 0 0 0 0, …(투명 넷)…, rgba(20,23,28,.07) 0 1px 2px 0

    으로 나온다 — **화면은 글자 하나 다르지 않은데** 문자열은 다르다. 투명 0 겹을
    걷어내고 비교한다. 걷어낸 뒤에도 다르면 그것은 진짜 차이다.
    """
    # **보이지 않는 값은 화면에 없다.** 테두리 폭이 0 이면 그 변의 색과 선 종류는
    # 무엇이든 그려지지 않는다 — `border:0` 과 `border-width:0; border-style:solid` 는
    # 같은 화면을 만든다. 윤곽선도 마찬가지다. 폭 자체가 다르면 폭이 따로 보고한다.
    if row is not None:
        m = re.fullmatch(r"border-(top|right|bottom|left)-(color|style)", prop)
        if m is not None and row.get(f"border-{m.group(1)}-width") == "0px":
            return "<보이지 않음>"
        if prop == "outline-color" and row.get("outline-style") in {"none", ""}:
            return "<보이지 않음>"

    # 쓰기 방식만 다른 것들. **값이 같음이 분명한 것만** 넣는다.
    if prop == "text-align":
        # LTR 에서 `start`·`end` 는 `left`·`right` 로 계산된다. 브라우저가 어느 쪽
        # 이름으로 돌려주는지는 원래 선언이 논리 속성이었는지에 달려 있을 뿐이다.
        return {"start": "left", "end": "right"}.get(value, value)
    if prop == "flex-basis" and value in {"0%", "0px"}:
        # `flex-1`(0%)과 인라인 `flex:1 1 0`(0px). 남는 자리를 나눌 때 결과가 같다.
        return "0"
    if prop != "box-shadow":
        return value
    parts = [p.strip() for p in re.split(r",(?![^(]*\))", value)]
    kept = [p for p in parts if p and p != ZERO_SHADOW]
    return ", ".join(kept) if kept else "none"


def compare(before: dict, after: dict) -> tuple[list[dict], int]:
    mismatches: list[dict] = []
    compared = 0
    for name in sorted(set(before) | set(after)):
        b = before.get(name, [])
        a = after.get(name, [])
        if not b or not a:
            mismatches.append({"screen": name, "kind": "missing", "before": len(b), "after": len(a)})
            continue
        if len(b) != len(a):
            mismatches.append(
                {"screen": name, "kind": "structure", "before": len(b), "after": len(a)}
            )
        by_path = {row["path"]: row for row in a}
        for row in b:
            other = by_path.get(row["path"])
            if other is None:
                mismatches.append({"screen": name, "kind": "unpaired", "path": row["path"]})
                continue
            if other["tag"] != row["tag"]:
                mismatches.append(
                    {"screen": name, "kind": "tag", "path": row["path"],
                     "before": row["tag"], "after": other["tag"]}
                )
                continue
            for p in PROPS:
                compared += 1
                if normalize(p, row.get(p, ""), row) != normalize(p, other.get(p, ""), other):
                    mismatches.append(
                        {"screen": name, "kind": "prop", "path": row["path"], "tag": row["tag"],
                         "prop": p, "before": row.get(p), "after": other.get(p)}
                    )
    return mismatches, compared


def main() -> int:
    ap = argparse.ArgumentParser(description="L2 — 전환 전후 화면 대조")
    ap.add_argument("--baseline", action="store_true", help="전 쪽만 재서 기준선을 뜬다")
    ap.add_argument("--compare", action="store_true", help="양쪽을 재고 보고서를 쓴다")
    ap.add_argument("--rebuild", action="store_true", help="전 쪽 worktree 와 빌드를 다시 만든다")
    args = ap.parse_args()
    if not (args.baseline or args.compare):
        ap.error("--baseline 또는 --compare 중 하나가 필요하다")

    from playwright.sync_api import sync_playwright  # noqa: PLC0415

    before_dist = ensure_before(rebuild=args.rebuild)
    after_dist = ensure_after() if args.compare else None

    # **데이터 루트를 고정한다.** 임시 디렉터리 이름이 화면에 경로 글자로 나오므로,
    # 매번 다른 이름을 쓰면 글자 폭이 달라져 없는 불일치가 생긴다.
    if DATA_HOME.exists():
        shutil.rmtree(DATA_HOME)
    seed(DATA_HOME)

    def side(dist: Path, pw) -> dict[str, list[dict]]:
        # **쪽마다 백엔드를 새로 띄운다.** 「프로젝트를 열었다」는 서버가 기억하므로,
        # 같은 인스턴스를 이어 쓰면 뒤쪽 쪽이 닫힌 상태의 화면을 볼 수 없다.
        proc, backend = start_backend(DATA_HOME)
        try:
            return collect(dist, backend, pw)
        finally:
            proc.terminate()
            proc.wait(timeout=10)

    with sync_playwright() as pw:
        before = side(before_dist, pw)
        after = side(after_dist, pw) if after_dist is not None else None

    before_digest = source_digest(BEFORE_WT / "frontend")
    after_digest = source_digest(ROOT / "frontend")

    if args.baseline:
        BASELINE.write_text(
            json.dumps({"beforeDigest": before_digest, "screens": before}, ensure_ascii=False),
            encoding="utf-8",
        )
        counts = {k: len(v) for k, v in before.items()}
        print(f"기준선을 떴다: {BASELINE}")
        print(f"  화면 {len(before)}개 · 요소 {counts}")
        return 0

    assert after is not None
    raw, compared = compare(before, after)
    intended = [{**m, "reason": is_intended(m)} for m in raw if is_intended(m) is not None]
    mismatches = [m for m in raw if is_intended(m) is None]
    REPORT.write_text(
        json.dumps(
            {
                "beforeDigest": before_digest,
                "afterDigest": after_digest,
                "mergeBase": merge_base(),
                        # **무엇을 대조했는지가 남아야 한다** (FR-011). 여기 없는 화면은
                # 대조되지 않았다는 뜻이다.
                "screens": [s["name"] for s in SCENARIOS],
                "props": len(PROPS),
                "compared": compared,
                "mismatches": mismatches,
                # 판단이 적힌 차이. 통과 조건에서 빠지지만 **보고서에서 사라지지는 않는다.**
                "intended": intended,
            },
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )
    print(f"화면 {len(SCENARIOS)}개 · 속성 {len(PROPS)}개 · 대조 {compared}칸")
    print(f"불일치 {len(mismatches)}건 (의도된 차이 {len(intended)}건 제외) → {REPORT}")
    for m in mismatches[:40]:
        if m["kind"] == "prop":
            print(f"  ✗ [{m['screen']}] {m['path']} {m['prop']}: {m['before']!r} → {m['after']!r}")
        else:
            print(f"  ✗ [{m['screen']}] {m['kind']}: {m}")
    if len(mismatches) > 40:
        print(f"  … 그 밖 {len(mismatches) - 40}건은 보고서에 있다")
    return 1 if mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())
