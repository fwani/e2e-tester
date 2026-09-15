#!/usr/bin/env python3
"""화면 깨짐 순회 — 실제 화면을 띄워 조작이 덮이지 않고 넘치거나 끊기지 않는지 잰다. 017 T016.

계약: specs/017-shadcn-ui-migration/contracts/screen-sweep.md (SW-1~SW-8)

## L2 대조와 무엇이 다른가

L2(`design_compare_ba.py`)는 **전환 전과 같은가**를 잰다. 전환 전 화면이 이미 깨져 있으면 그
깨짐까지 「같다」로 통과시킨다 — B-01(알림이 국면 띠를 덮는다)이 바로 그 경우였다. 이 순회는
**화면이 그 자체로 깨지지 않았는가**를 판정 규칙(SW-6)으로 잰다. 둘은 서로를 대신하지 않는다.

## 실행

    backend/.venv/bin/python scripts/screen_sweep.py            # 전부
    backend/.venv/bin/python scripts/screen_sweep.py --only edit,test-create --viewports 1440

`--only`·`--viewports` 로 좁혀 돌린 결과는 **보고서를 쓰지 않는다** — 일부만 잰 보고서로
`ScreenSweep.test.ts` 를 통과시킬 수 없게 한다. 캡처는 `.sweep/shots/` 에 남는다.

종료 코드: 등록되지 않은 검출 · 닿지 못한 화면 · 고쳐졌는데 등록부에 남은 알려진 깨짐이 있으면 1.

## 격리 (SW-1)

제품 서버는 `.sweep/data` 를 `XDG_DATA_HOME`·`XDG_CONFIG_HOME` 으로 쓴다. 사용자의 실제
프로젝트·키·비밀 값을 읽지도 쓰지도 않는다. 이름을 고정하는 이유는 경로가 화면에 글자로 나오기
때문이다 — 매번 다르면 글자 폭이 달라져 없는 넘침이 생긴다.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
SWEEP = ROOT / ".sweep"
DATA = SWEEP / "data"
SHOTS = SWEEP / "shots"
REPORT = FRONTEND / "tests" / "sweep-report.json"
RESULTS = SWEEP / "results.json"  # 날것의 결과 — `--reclassify` 의 입력 (커밋하지 않는다)
VENV_PY = ROOT / "backend" / ".venv" / "bin" / "python"

sys.path.insert(0, str(ROOT / "scripts"))
from design_compare_ba import free_port, source_digest  # noqa: E402

FIXTURE_PORT = int(os.environ.get("ITB_SWEEP_FIXTURE_PORT", "4300"))
SAMPLE = f"http://127.0.0.1:{FIXTURE_PORT}"

# ── SW-4 폭 ───────────────────────────────────────────────────────────────
VIEWPORTS = [(1280, 800), (1440, 900), (1920, 1080), (2560, 1440)]
WIDE = 1440  # 이보다 넓으면 화면 정책(data·form)을 잰다 (FR-021)


# ── SW-2 시드 ─────────────────────────────────────────────────────────────


def _cand(v: str | None) -> dict | None:
    return {"value": v, "status": "verified"} if v else None


def _loc(*, testid=None, css=None, role=None, name=None, label=None, text=None, tag=None) -> dict:
    return {
        "tag": tag, "test_id": _cand(testid), "role": role, "accessible_name": name,
        "role_status": "verified" if role else None, "label": _cand(label), "text": _cand(text),
        "stable_attr": None, "css": _cand(css or "body"),
    }


def _step(i: int, kind: str, label: str, **kw) -> dict:
    base = {"id": f"step-{i:02d}", "type": kind, "label": label, "author": "human",
            "tab": 0, "frame_url": None, "timeout_ms": 4000}
    base.update(kw)
    return base


def _login_steps(extra_asserts: int = 0, fail: bool = False) -> list[dict]:
    steps = [
        _step(1, "navigate", "로그인 화면으로 이동", url=f"{SAMPLE}/login.html"),
        _step(2, "fill", "이메일 입력", value="qa@example.com",
              target=_loc(testid="login-email", css="#email", label="이메일", tag="input", role="textbox", name="이메일")),
        _step(3, "fill", "비밀번호 입력", value="pw-1234", target=_loc(css="#password", label="비밀번호", tag="input")),
        _step(4, "click", "로그인 버튼 클릭",
              target=_loc(testid="login-submit", css="#submit", role="button", name="로그인", tag="button")),
    ]
    if fail:
        steps.append(_step(5, "assertion", "로그인 실패 문구가 보인다 — 일부러 틀린 기대값", timeout_ms=1500,
                           assertion={"kind": "text", "match": "equals", "value": "존재하지 않는 문구",
                                      "target": _loc(css="#err", tag="div")}))
        return steps
    steps.append(_step(5, "assertion", "프로젝트 화면으로 넘어간다",
                       assertion={"kind": "url", "match": "contains", "value": "projects.html", "target": None}))
    for k in range(extra_asserts):
        steps.append(_step(6 + k, "assertion", f"머리띠 브랜드가 보인다 ({k + 1})",
                           assertion={"kind": "visible", "match": "equals", "value": None,
                                      "target": _loc(css="nav .brand", text="데이터 플랫폼", tag="span")}))
    return steps


def seed() -> Path:
    """프로젝트 1 · 그룹 2 · 테스트 6 · 초안 1. 결과는 `run_replays` 가 실제로 만든다."""
    os.environ["XDG_DATA_HOME"] = str(DATA / "share")
    os.environ["XDG_CONFIG_HOME"] = str(DATA / "config")
    sys.path.insert(0, str(ROOT / "backend" / "src"))
    from itb.domain.draft import Draft, DraftSource  # noqa: PLC0415
    from itb.domain.test_case import Project, Test, TestGroup  # noqa: PLC0415
    from itb.storage import paths  # noqa: PLC0415
    from itb.storage.drafts import DraftStore  # noqa: PLC0415
    from itb.storage.repository import ProjectRepository  # noqa: PLC0415

    root = paths.workspace_dir() / "sweep-fixture"
    root.parent.mkdir(parents=True, exist_ok=True)
    repo = ProjectRepository.create(
        root,
        Project(
            name="순회 프로젝트",
            default_start_url=f"{SAMPLE}/login.html",
            groups=[TestGroup(prefix="LOGIN", name="로그인"),
                    TestGroup(prefix="CART", name="장바구니와 결제 흐름 — 긴 그룹 이름이 줄에서 어떻게 잘리는지")],
        ),
    )
    tests = [
        ("TC-001", "로그인이 된다", _login_steps(extra_asserts=12)),
        ("TC-002", "비밀번호를 틀리면 막히고 오류 문구가 입력칸 아래에 뜬다 — 목록과 국면 띠에서 아주 긴 "
                   "테스트 이름이 어떻게 잘리는지 확인하기 위한 문장", _login_steps()),
        ("TC-003", "실패하는 테스트", _login_steps(fail=True)),
        ("TC-004", "미실행 테스트", _login_steps()),
        ("LOGIN-001", "그룹 안의 로그인", _login_steps()),
        ("CART-001", "장바구니에 담긴다", _login_steps(extra_asserts=2)),
    ]
    for tid, name, steps in tests:
        repo.write_test(Test(id=tid, name=name, authoring_mode="record",
                             start_url=f"{SAMPLE}/login.html", steps=steps))  # type: ignore[arg-type]
    DraftStore(root).write(Draft(
        draft_id="D-0001", name="비밀번호 재설정 메일이 발송된다",
        procedure="1. 로그인 화면에서 비밀번호 찾기를 누른다\n2. 이메일을 입력한다",
        expectation="재설정 메일 발송 안내가 보인다",
        source=DraftSource(file_name="설계서.xlsx", sheet_name="계정", row=2),
    ))
    return root


# ── 프로세스 ──────────────────────────────────────────────────────────────


def _answers(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=1) as r:  # noqa: S310 - 로컬 주소만
            return r.status < 500
    except Exception:  # noqa: BLE001 — 아직 안 떴을 뿐이다
        return False


def _wait(url: str, proc: subprocess.Popen | None, what: str, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc is not None and proc.poll() is not None:
            raise SystemExit(f"{what} 가 종료됐다 (코드 {proc.returncode}) — 로그: {SWEEP / 'logs'}")
        if _answers(url):
            return
        time.sleep(0.3)
    raise SystemExit(f"{what} 가 {timeout:.0f}초 안에 응답하지 않았다 ({url})")


def _log(name: str):
    (SWEEP / "logs").mkdir(parents=True, exist_ok=True)
    return open(SWEEP / "logs" / f"{name}.log", "ab")  # noqa: SIM115


def ensure_fixture() -> subprocess.Popen | None:
    """픽스처 앱. 이미 떠 있으면 재사용한다 — 포트가 시작 주소에 글자로 들어가므로 고정한다."""
    if _answers(f"{SAMPLE}/login.html"):
        return None
    proc = subprocess.Popen([sys.executable, str(ROOT / "fixtures" / "sample-app" / "serve.py"),
                             "--port", str(FIXTURE_PORT)], stdout=_log("fixture"), stderr=subprocess.STDOUT)
    _wait(f"{SAMPLE}/login.html", proc, "픽스처 앱", 20)
    return proc


def _env() -> dict[str, str]:
    env = dict(os.environ)
    env.update(XDG_DATA_HOME=str(DATA / "share"), XDG_CONFIG_HOME=str(DATA / "config"),
               PYTHONPATH=str(ROOT / "backend" / "src"), ITB_HEADLESS="1", PYTHONUNBUFFERED="1")
    return env


def start_backend() -> tuple[subprocess.Popen, str]:
    port = free_port()
    proc = subprocess.Popen([str(VENV_PY), "-m", "uvicorn", "itb.api.app:app", "--host", "127.0.0.1",
                             "--port", str(port), "--log-level", "warning"],
                            env=_env(), stdout=_log("backend"), stderr=subprocess.STDOUT)
    base = f"http://127.0.0.1:{port}"
    _wait(f"{base}/api/health", proc, "제품 서버", 40)
    return proc, base


def start_ui(api_base: str) -> tuple[subprocess.Popen, str]:
    """**개발 서버로 띄운다** (SW-3). 정적 서버는 WebSocket 을 프록시하지 않아 녹화 화면이
    「실시간 연결이 끊겼습니다」로만 그려졌다 — 전환 전 실측이 그 한계를 겪었다."""
    port = free_port()
    env = _env()
    env.update(ITB_API_PORT=api_base.rsplit(":", 1)[1], ITB_UI_PORT=str(port))
    proc = subprocess.Popen(["npm", "run", "dev", "--", "--port", str(port), "--strictPort"],
                            cwd=FRONTEND, env=env, stdout=_log("vite"), stderr=subprocess.STDOUT)
    base = f"http://127.0.0.1:{port}"
    _wait(base, proc, "화면 개발 서버", 90)
    return proc, base


def stop(proc: subprocess.Popen | None) -> None:
    if proc is None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()


def api(base: str, method: str, path: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(base + path, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:  # noqa: S310 - 로컬 주소만
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"{method} {path} → {exc.code}: {exc.read()[:300]!r}") from exc


def run_replays(base: str) -> None:
    """결과를 **실제 재실행으로** 만든다 (SW-2). 손으로 지은 결과는 실제 실패 메시지를 갖지 못한다."""
    want = {"TC-001": "completed", "TC-003": "failed", "LOGIN-001": "completed"}
    for tid, expected in want.items():
        sid = api(base, "POST", "/api/sessions", {"mode": "replay", "test_id": tid})["session_id"]
        state = "starting"
        for _ in range(180):
            state = api(base, "GET", f"/api/sessions/{sid}").get("state", "")
            if state not in {"starting", "replaying"}:
                break
            time.sleep(0.5)
        for tail in ("stop", "discard"):
            try:
                api(base, "POST", f"/api/sessions/{sid}/{tail}")
            except RuntimeError:
                pass
        if state != expected:
            raise SystemExit(f"시드 재실행 {tid}: {state} (기대 {expected}) — 픽스처 앱({SAMPLE})이 떠 있는가")
        print(f"  재실행 {tid}: {state}")


# ── SW-5 화면 ─────────────────────────────────────────────────────────────
#
# `phase`: closed(프로젝트를 열지 않음) → open → session(녹화 세션이 열려 있음). 순서가 결과를
# 바꾸므로 고정한다 — 열기는 서버가 기억하고, 세션은 목록에 띠를 만든다.
#
# 조작(`steps`)과 **닿았다는 증거**(`evidence`)를 함께 적는다. 증거가 없으면 그 화면은 「잰 것」이
# 아니라 실패다 — L2 1회차가 다섯 화면을 같은 32개 요소로 잰 사고를 되풀이하지 않는다.
#
# `measure`·`expect`: 판정 규칙(SW-6)으로 잡히지 않는 수치 요구. 기대를 벗어나면 `metric` 검출이다.

CLOSED, OPEN, SESSION = "closed", "open", "session"

SCENARIOS: list[dict] = [
    {"name": "project-list", "phase": CLOSED, "policy": "form",
     "evidence": [("role", "button", "새 프로젝트 만들기")]},
    {"name": "project-create", "phase": CLOSED, "policy": "form",
     "steps": [("click_role", "button", "새 프로젝트 만들기")], "evidence": [("css", "input")]},
    {"name": "test-list", "phase": OPEN, "policy": "data",
     "evidence": [("count", "[data-test-select]", 6)],
     "measure": "checkboxSizes", "expect": {"checkboxSizes": ("==", 1)}},
    {"name": "test-list-selected", "phase": OPEN, "policy": "data",
     "steps": [("check", "[data-test-select]", 0), ("check", "[data-test-select]", 1)],
     "evidence": [("css", "[data-test-selection-bar]")],
     "measure": "selectionBar", "expect": {"selectionSelectWidth": ("<=", 360)}},
    {"name": "test-list-bulk-confirm", "phase": OPEN, "policy": "data",
     "steps": [("check", "[data-test-select]", 0), ("click_css", "[data-test-bulk-delete]")],
     "evidence": [("css", "[data-test-bulk-confirm]")]},
    {"name": "test-list-row-menu", "phase": OPEN, "policy": "data",
     "steps": [("click_role", "button", "로그인이 된다 추가 동작")],
     "evidence": [("css", "[data-row-menu-item]")]},
    {"name": "test-create", "phase": OPEN, "policy": "data",
     "steps": [("click_role", "button", "테스트 만들기")], "evidence": [("css", "[data-phase-pill]")],
     "measure": "compose", "expect": {"nlInputWidth": (">=", 240)}},
    {"name": "secrets", "phase": OPEN, "policy": "form",
     "steps": [("click_role", "button", "비밀 값")], "evidence": [("url", "screen=secrets")]},
    {"name": "keys", "phase": OPEN, "policy": "form",
     "steps": [("click_role", "button", "키 관리")], "evidence": [("url", "screen=keys")]},
    {"name": "result-pass", "phase": OPEN, "policy": "data", "query": "?screen=result&test=TC-001",
     "evidence": [("css", "[data-phase-pill]")]},
    {"name": "result-fail", "phase": OPEN, "policy": "data", "query": "?screen=result&test=TC-003",
     "evidence": [("css", "[data-phase-pill]"), ("text", "요소를 찾을 수 없습니다")]},
    {"name": "edit", "phase": OPEN, "policy": "data", "query": "?screen=definition&test=TC-001",
     "evidence": [("css", "[data-phase-pill]"), ("count", "[data-step-row]", 17)],
     "measure": "stepRows", "expect": {"stepRowsVisible": (">=", 8)}},
    {"name": "edit-long-name", "phase": OPEN, "policy": "data", "query": "?screen=definition&test=TC-002",
     "evidence": [("css", "[data-phase-pill]")]},
    {"name": "edit-step-detail", "phase": OPEN, "policy": "data",
     "query": "?screen=definition&test=TC-001&step=step-02", "evidence": [("css", "[data-detail-close]")]},
    {"name": "edit-delete-confirm", "phase": OPEN, "policy": "data", "query": "?screen=definition&test=TC-001",
     "steps": [("check", '[data-row-action="step.toggleSelection"]', 0), ("click_role", "button", "고른 것 지우기")],
     "evidence": [("css", "[data-bulk-delete-confirm]")]},
    {"name": "test-list-session", "phase": SESSION, "policy": "data",
     "evidence": [("text", "진행 중인 세션이 있습니다")]},
    {"name": "runner-record", "phase": SESSION, "policy": "data",
     "steps": [("click_role", "button", "이어서 보기")], "wait": 2500,
     "evidence": [("css", "[data-phase-pill]"), ("absent_text", "실시간 연결이 끊겼습니다")]},
    {"name": "runner-disconnected", "phase": SESSION, "policy": "data", "cut_events": True,
     "steps": [("click_role", "button", "이어서 보기")], "wait": 2500,
     "evidence": [("text", "실시간 연결이 끊겼습니다")]},
]

# 닿지 못하는 화면 — 순회되지 않았다는 사실을 보고서에 싣는다 (SW-5).
UNREACHED = [
    ("import-preview", "엑셀 파일 입력이 필요하다"),
    ("runner-paused · runner-ai · runner-takeover", "대상 앱 조작 또는 언어모델이 필요하다"),
]


# ── SW-7 허용 등록부 ───────────────────────────────────────────────────────
# 판정에 걸리지만 깨짐이 아닌 것. **사유 없이 등록하지 않는다.** 여기 없는 검출은 전부 깨짐이다.
ALLOWED: list[dict] = [
    {"where": r"^(project-list|project-create)@", "kind": "console",
     "match": r"404 .*/api/project$|status of 404",
     "reason": "프로젝트를 열지 않은 첫 화면이 「열린 프로젝트 없음」을 404 로 받는다 — 요청 계약의 문제로 017 범위 밖 (spec Assumptions)"},
    {"where": r"^edit-long-name@", "kind": "console",
     "match": r"404 .*/api/tests/TC-002/result$|status of 404",
     "reason": "결과가 없는 테스트의 결과 조회가 404 다 — 같은 이유로 범위 밖"},
    {"where": r"^runner-disconnected@", "kind": "console",
     "match": r"^WebSocket connection to 'ws://127\.0\.0\.1:9/events' failed",
     "reason": "이 화면은 이벤트 소켓을 일부러 닫힌 포트로 보내 연결 끊김을 만든다 — 그 연결 실패가 콘솔에 찍히는 것은 재려는 상황 자체다"},
]


# ── 알려진 깨짐 등록부 ─────────────────────────────────────────────────────
# 전환 전 실측(baseline.md)의 B-01~B-11. 검출이 여기 맞으면 「알려진 깨짐」으로 따로 보고하고
# 실패로 치지 않는다. **어떤 검출과도 맞지 않는 항목은 실패다** — 고쳐졌으면 여기서 지운다.
# 그래야 「고쳤다」가 코드 커밋이 아니라 이 순회에서 사라진 것으로 정의된다 (data-model §9).
KNOWN: list[dict] = [
    # B-01 · B-02 — 017 US1 이 고쳤다 (알림 층 자리를 띠가 정한다 · 세션 토스트 삭제). 여기서 지웠으므로
    # 다시 검출되면 「등록되지 않은 검출」로 실패한다.
    {"id": "B-03", "where": r"^edit@", "kind": "metric", "match": r"^stepRowsVisible"},
    {"id": "B-04", "where": r"^test-create@", "kind": "spillY", "match": r"아직 브라우저를 열지 않았습니다"},
    {"id": "B-05", "where": r"^test-create@", "kind": "wrap", "match": r"TEST STEPS|고른 것 없음|작성"},
    {"id": "B-06", "where": r"^test-create@", "kind": "metric", "match": r"^nlInputWidth"},
    {"id": "B-07", "where": r"^test-list-selected@", "kind": "wrap", "match": r"선택됨|전부 선택"},
    {"id": "B-07", "where": r"^test-list-selected@", "kind": "metric", "match": r"^selectionSelectWidth"},
    {"id": "B-08", "where": r"^test-list", "kind": "metric", "match": r"^checkboxSizes"},
    # 표 머리의 전체 선택 체크박스가 28px 칸을 넘친다 — B-08 의 DOM 쪽 증상 (baseline `div 35>28`).
    {"id": "B-08", "where": r"^test-list", "kind": "spill", "match": r"^div\{\} 3\d>28$"},
    {"id": "B-09", "where": r"^test-list", "kind": "align", "match": r"희망 번호|대상기능|수행자|출처|할 수 있는 일"},
    {"id": "B-10", "where": r"^(test-list[a-z-]*|result-[a-z]+|edit[a-z-]*|test-create|runner-[a-z]+)@(1920|2560)$",
     "kind": "policy", "match": r"^data"},
    {"id": "B-11", "where": r"@1280$", "kind": "shell", "match": r"header"},
]


# ── SW-6 판정 ─────────────────────────────────────────────────────────────

SCAN_JS = r"""
() => {
  const vw = innerWidth, vh = innerHeight;
  const F = [];
  const desc = (el) => {
    const t = (el.getAttribute('aria-label') || el.innerText || el.value || el.getAttribute('placeholder') || '')
      .trim().replace(/\s+/g, ' ').slice(0, 40);
    const slot = el.getAttribute('data-slot');
    const data = slot ? `[data-slot=${slot}]` : (() => {
      const k = Object.keys(el.dataset || {})[0];
      return k ? `[data-${k.replace(/[A-Z]/g, (c) => '-' + c.toLowerCase())}]` : '';
    })();
    return `${el.tagName.toLowerCase()}${data}{${t}}`;
  };
  const shown = (el) => {
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || cs.display === 'contents') return false;
    const r = el.getBoundingClientRect();
    return r.width > 0 && r.height > 0;
  };
  const clippedAt = (el, x, y) => {
    for (let p = el.parentElement; p && p !== document.body; p = p.parentElement) {
      const cs = getComputedStyle(p);
      if (cs.overflowX !== 'visible' || cs.overflowY !== 'visible') {
        const pr = p.getBoundingClientRect();
        if (x < pr.left || x > pr.right || y < pr.top || y > pr.bottom) return true;
      }
    }
    return false;
  };
  const lines = (el) => {
    // 글자 조각 사각형을 **세로로 절반 이상 겹치는 것끼리** 한 줄로 묶는다 — 크기가 다른
    // 개수 글자(「전체 6」)를 두 줄로 세던 전환 전 오탐을 막는다 (SW-6).
    const range = document.createRange();
    range.selectNodeContents(el);
    const rects = [...range.getClientRects()].filter((q) => q.width > 1 && q.height > 1).sort((a, b) => a.top - b.top);
    const out = [];
    for (const q of rects) {
      const hit = out.find((l) => Math.min(l.bottom, q.bottom) - Math.max(l.top, q.top) > 0.5 * Math.min(l.bottom - l.top, q.height));
      if (hit) { hit.top = Math.min(hit.top, q.top); hit.bottom = Math.max(hit.bottom, q.bottom); }
      else out.push({ top: q.top, bottom: q.bottom });
    }
    return out.length;
  };
  const CONTROL = 'button, a[href], input:not([type=hidden]), select, textarea, [role=button], [role=tab], [role=menuitem], [role=radio], [role=checkbox]';
  const all = [...document.querySelectorAll('body *')];
  for (const el of all) {
    if (!shown(el)) continue;
    const cs = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    if (cs.display !== 'inline' && el.clientWidth > 1 && el.scrollWidth > el.clientWidth + 1) {
      const d = `${el.scrollWidth}>${el.clientWidth}`;
      if (cs.overflowX === 'visible') F.push(['spill', desc(el), d]);
      else if ((cs.overflowX === 'hidden' || cs.overflowX === 'clip') && cs.textOverflow !== 'ellipsis') F.push(['cut', desc(el), d]);
    }
    if (cs.display !== 'inline' && cs.overflowY === 'visible' && el.clientHeight > 0 && el.scrollHeight > el.clientHeight + 8) {
      F.push(['spillY', desc(el), `${el.scrollHeight}>${el.clientHeight}`]);
    }
    // 줄바꿈 — 짧은 이름표(조작·칩·머리·라벨)가 두 줄이 되는가. 문단(24자 초과)은 보지 않는다.
    const text = (el.innerText || '').trim();
    const leaf = [...el.children].every((c) => getComputedStyle(c).display.startsWith('inline'));
    if (cs.display !== 'inline' && leaf && text.length > 0 && text.length <= 24 && !text.includes('\n') && lines(el) > 1) {
      F.push(['wrap', desc(el), `lines=${lines(el)}`]);
    }
  }
  // 머리띠는 창 폭 안에 있어야 한다 (B-11 · layout-contract-v3 L3).
  for (const el of document.querySelectorAll('[data-shell=header]')) {
    if (!shown(el)) continue;
    const r = el.getBoundingClientRect();
    if (r.left < -1 || r.right > vw + 1) F.push(['shell', 'header', `x=${Math.round(r.left)}..${Math.round(r.right)} vw=${vw}`]);
  }
  // 덮임 — 조작의 **보이는 중심점**을 다른 것이 차지하는가.
  for (const el of document.querySelectorAll(CONTROL)) {
    if (!shown(el)) continue;
    const cs = getComputedStyle(el);
    if (cs.opacity === '0' || cs.pointerEvents === 'none') continue;
    const r = el.getBoundingClientRect();
    if (r.width <= 1 || r.height <= 1) continue;
    const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
    if (cx < 0 || cy < 0 || cx >= vw || cy >= vh || clippedAt(el, cx, cy)) continue;
    const hit = document.elementFromPoint(cx, cy);
    if (!hit || hit === el || el.contains(hit) || hit.contains(el)) continue;
    const label = hit.closest('label');
    if (label && label.contains(el)) continue;
    if (el.labels && [...el.labels].some((l) => l.contains(hit))) continue;
    // 대화상자·겹침 판·가림막·**떠 있는 메뉴와 목록**이 뒤를 가리는 것은 그 부품의 목적이다 (SW-7).
    // 메뉴는 1회차 순회가 오탐으로 알려 줬다 — 열린 행 메뉴가 아래 행의 「실행」을 가린 것을 덮임으로 셌다.
    // 수제 행 메뉴(`[data-row-menu]`)는 역할이 없어 따로 적는다. Radix 로 옮기면 `[role=menu]` 가 된다.
    const layer = hit.closest('[role=dialog], [role=alertdialog], [role=menu], [role=listbox], [role=tooltip], ' +
      '[data-strength], [data-slot$=overlay], [data-row-menu], [data-radix-popper-content-wrapper]');
    if (layer && !layer.contains(el)) continue;
    F.push(['covered', desc(el), `by ${desc(hit)}`]);
  }
  // 표 — 머리 칸과 본문 칸의 정렬, 머리 글꼴 (B-09).
  for (const t of document.querySelectorAll('table')) {
    if (!shown(t)) continue;
    const ths = [...t.querySelectorAll('thead tr:first-child > th')];
    const row = t.querySelector('tbody tr');
    const tds = row ? [...row.children] : [];
    const norm = (a) => (a === 'start' ? 'left' : a === 'end' ? 'right' : a);
    ths.forEach((th, i) => {
      const td = tds[i];
      // 글자가 없는 머리 칸(보조기술 전용 이름 포함)의 정렬은 화면에 나타나지 않는다 — 1회차 오탐.
      if (!td || !(th.innerText || '').trim()) return;
      const a = norm(getComputedStyle(th).textAlign), b = norm(getComputedStyle(td).textAlign);
      if (a !== b) F.push(['align', desc(th), `${a}≠${b}`]);
    });
    const fonts = new Set(ths.map((th) => `${getComputedStyle(th).fontFamily}|${getComputedStyle(th).fontSize}`));
    if (fonts.size > 1) F.push(['align', `table{${ths.map((x) => x.innerText.trim()).join('/')}}`, `head fonts=${fonts.size}`]);
  }
  // 화면 정책의 재료 — **본문의** 글자·조작이 차지하는 가로 범위.
  // 고정 위치(알림 층)와 머리띠(`[data-shell]`)는 뺀다. 머리띠는 창 폭 전체라 왼쪽 끝의 제품
  // 표시가 「가운데가 아니다」를 만들었다 — 가운데 선 폼 화면을 1회차 순회가 그렇게 오판했다.
  let L = 1e9, R = -1e9;
  for (const el of all) {
    const cs = getComputedStyle(el);
    if (cs.position === 'fixed' || !shown(el) || el.closest('[data-shell]')) continue;
    const bearing = el.matches('button, input, select, textarea') || [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim());
    if (!bearing) continue;
    const r = el.getBoundingClientRect();
    L = Math.min(L, r.left); R = Math.max(R, r.right);
  }
  return { vw, vh, docW: document.documentElement.scrollWidth, findings: F, extent: { left: L, right: R } };
}
"""

MEASURE_JS = {
    "stepRows": r"""
() => {
  const rows = [...document.querySelectorAll('[data-step-row]')];
  if (!rows.length) return { stepRowsVisible: 0 };
  let box = rows[0].parentElement;
  while (box && !['auto', 'scroll'].includes(getComputedStyle(box).overflowY)) box = box.parentElement;
  const b = (box || document.documentElement).getBoundingClientRect();
  const top = Math.max(b.top, 0), bottom = Math.min(b.bottom, innerHeight);
  return { stepRowsVisible: rows.filter((r) => { const q = r.getBoundingClientRect(); return q.top >= top - 1 && q.bottom <= bottom + 1; }).length };
}""",
    "compose": r"""
() => {
  const el = document.querySelector('input[aria-label="자연어로 Step 추가"], textarea[aria-label="자연어로 Step 추가"]');
  return { nlInputWidth: el ? Math.round(el.getBoundingClientRect().width) : -1 };
}""",
    "selectionBar": r"""
() => {
  const el = document.querySelector('[data-test-selection-bar] select');
  return { selectionSelectWidth: el ? Math.round(el.getBoundingClientRect().width) : -1 };
}""",
    "checkboxSizes": r"""
() => {
  const boxes = [...document.querySelectorAll('[data-test-head] input[type=checkbox], [data-test-select]')];
  const sizes = new Set(boxes.map((b) => { const r = b.getBoundingClientRect(); return `${Math.round(r.width)}x${Math.round(r.height)}`; }));
  return { checkboxSizes: sizes.size, checkboxSizeList: [...sizes].sort().join(' ') };
}""",
}

OPS = {"==": lambda a, b: a == b, ">=": lambda a, b: a >= b, "<=": lambda a, b: a <= b}


def _reach(page, sc: dict) -> str | None:
    for step in sc.get("steps", []):
        kind = step[0]
        try:
            if kind == "click_role":
                page.get_by_role(step[1], name=step[2]).first.click(timeout=6000)
            elif kind == "click_css":
                page.locator(step[1]).first.click(timeout=6000)
            elif kind == "check":
                page.locator(step[1]).nth(step[2]).check(timeout=6000)
        except Exception as exc:  # noqa: BLE001
            return f"조작 실패 {step}: {type(exc).__name__}"
        page.wait_for_timeout(700)
    page.wait_for_timeout(sc.get("wait", 0))
    for ev in sc.get("evidence", []):
        kind = ev[0]
        try:
            if kind == "role":
                page.get_by_role(ev[1], name=ev[2]).first.wait_for(state="visible", timeout=10000)
            elif kind == "css":
                page.locator(ev[1]).first.wait_for(state="visible", timeout=10000)
            elif kind == "text":
                page.get_by_text(ev[1]).first.wait_for(state="visible", timeout=15000)
            elif kind == "absent_text":
                if page.get_by_text(ev[1]).count() > 0:
                    return f"증거 실패 — 있으면 안 되는 글자: {ev[1]}"
            elif kind == "count":
                page.locator(ev[1]).nth(ev[2] - 1).wait_for(state="attached", timeout=10000)
            elif kind == "url":
                if ev[1] not in page.url:
                    return f"증거 실패 — 주소에 {ev[1]} 없음 ({page.url})"
        except Exception as exc:  # noqa: BLE001
            return f"증거 실패 {ev}: {type(exc).__name__}"
    return None


def capture(pw, ui: str, scenarios: list[dict], viewports: list[tuple[int, int]], results: dict) -> None:
    browser = pw.chromium.launch()
    try:
        for w, h in viewports:
            ctx = browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=1)
            for sc in scenarios:
                key = f"{sc['name']}@{w}"
                page = ctx.new_page()
                console: list[str] = []
                page.on("console", lambda m, c=console: c.append(m.text[:200]) if m.type == "error" else None)
                page.on("pageerror", lambda e, c=console: c.append(f"pageerror: {e}"[:200]))
                page.on("response", lambda r, c=console: c.append(f"{r.status} {r.url.split('?')[0]}") if r.status >= 400 else None)
                if sc.get("cut_events"):
                    # 이벤트 소켓이 **연결되지 못하게** 한다 — 실제 연결 끊김 알림이 뜨는 화면을 잰다.
                    #
                    # `page.route_web_socket(…, lambda ws: ws.close())` 로 먼저 했는데, 동기 API 의
                    # 처리기 안에서 `close()` 를 부르자 **순회 전체가 멈췄다**(1회차 · 10분 무응답).
                    # 여기서는 페이지가 뜨기 전에 `WebSocket` 을 감싸 `/events` 만 닫힌 포트로 보낸다.
                    # 브라우저가 실제로 연결 실패를 겪으므로 화면이 받는 사건은 진짜 끊김과 같다.
                    page.add_init_script(
                        "(() => { const Real = window.WebSocket;"
                        " window.WebSocket = class extends Real {"
                        "  constructor(url, protocols) {"
                        "   super(String(url).endsWith('/events') ? 'ws://127.0.0.1:9/events' : url, protocols); } }; })();"
                    )
                page.goto(ui + sc.get("query", "/"), wait_until="networkidle")
                page.wait_for_timeout(900)
                failed = _reach(page, sc)
                SHOTS.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(SHOTS / f"{key}.png"))
                scan = page.evaluate(SCAN_JS)
                metrics = page.evaluate(MEASURE_JS[sc["measure"]]) if "measure" in sc and failed is None else {}
                findings = [{"kind": k, "element": e, "detail": d} for k, e, d in scan["findings"]]
                for name, (op, want) in sc.get("expect", {}).items():
                    got = metrics.get(name)
                    if got is not None and not OPS[op](got, want):
                        extra = metrics.get("checkboxSizeList", "")
                        findings.append({"kind": "metric", "element": f"{name}={got}", "detail": f"기대 {op} {want} {extra}".strip()})
                if w > WIDE and failed is None:
                    left, right = scan["extent"]["left"], scan["extent"]["right"]
                    if sc["policy"] == "data" and right < w - 60:
                        findings.append({"kind": "policy", "element": "data", "detail": f"내용이 {round(right)}px 에서 끝난다 (창 {w})"})
                    if sc["policy"] == "form" and abs(left - (w - right)) > 40:
                        findings.append({"kind": "policy", "element": "form", "detail": f"좌 {round(left)} · 우 {round(w - right)} — 가운데가 아니다"})
                findings += [{"kind": "console", "element": c, "detail": ""} for c in dict.fromkeys(console)]
                uniq = {json.dumps(f, ensure_ascii=False, sort_keys=True): f for f in findings}
                results[key] = {"reached": failed is None, "failure": failed, "metrics": metrics,
                                "findings": sorted(uniq.values(), key=lambda f: (f["kind"], f["element"], f["detail"]))}
                status = "닿음" if failed is None else f"✗ {failed}"
                print(f"  {key:30s} 검출 {len(findings):3d}  {status}", flush=True)
                # 화면마다 날것의 결과를 남긴다 — 순회가 도중에 죽어도 잰 것을 잃지 않고,
                # `--reclassify` 가 등록부만 바꿔 다시 가를 수 있다.
                RESULTS.write_text(json.dumps({"digest": source_digest(FRONTEND), "results": results},
                                              ensure_ascii=False), encoding="utf-8")
                page.close()
            ctx.close()
    finally:
        browser.close()


def classify(results: dict) -> tuple[list, list, list, list]:
    allowed, pending, unallowed = [], [], []
    matched_known: set[int] = set()
    for key, res in sorted(results.items()):
        for f in res["findings"]:
            text = f"{f['element']} {f['detail']}".strip()
            row = {"where": key, **f}
            rule = next((a for a in ALLOWED if re.search(a["where"], key) and a["kind"] == f["kind"]
                         and re.search(a["match"], text)), None)
            if rule is not None:
                allowed.append({**row, "reason": rule["reason"]})
                continue
            idx = next((i for i, k in enumerate(KNOWN) if re.search(k["where"], key) and k["kind"] == f["kind"]
                        and re.search(k["match"], text)), None)
            if idx is not None:
                matched_known.add(idx)
                pending.append({**row, "id": KNOWN[idx]["id"]})
                continue
            unallowed.append(row)
    stale = [f"{k['id']} {k['kind']} {k['where']} /{k['match']}/" for i, k in enumerate(KNOWN) if i not in matched_known]
    return allowed, pending, unallowed, stale


def write_report(results: dict, screens: list[str], viewports: list[str], partial: bool) -> int:
    allowed, pending, unallowed, stale = classify(results)
    unreached = [k for k, r in results.items() if not r["reached"]]
    if partial:
        stale = []  # 일부만 돌렸으면 알려진 깨짐이 「안 맞았다」고 말할 수 없다
    print(f"\n화면 × 폭 {len(results)} · 허용 {len(allowed)} · 알려진 깨짐 {len(pending)} · "
          f"등록되지 않은 검출 {len(unallowed)} · 닿지 못함 {len(unreached)} · 고쳐졌는데 등록부에 남음 {len(stale)}")
    for row in unallowed[:80]:
        print(f"  ✗ [{row['where']}] {row['kind']:8s} {row['element']} {row['detail']}")
    for k in unreached:
        print(f"  ✗ [{k}] {results[k]['failure']}")
    for s in stale:
        print(f"  ✗ 등록부에서 지워라 — {s}")
    if partial:
        print("\n(--only · --viewports 로 좁혀 돌렸으므로 보고서를 쓰지 않았다)")
    else:
        REPORT.write_text(json.dumps({
            "digest": source_digest(FRONTEND),
            "viewports": viewports,
            "screens": screens,
            "unreached": [{"screen": n, "why": why} for n, why in UNREACHED],
            "counts": {"allowed": len(allowed), "pending": len(pending), "unallowed": len(unallowed),
                       "unreachedRuns": len(unreached), "staleKnown": len(stale)},
            "known": sorted({k["id"] for k in KNOWN}),
            "staleKnown": stale,
            "unreachedRuns": {k: results[k]["failure"] for k in unreached},
            "unallowed": unallowed,
            "pending": pending,
            "allowed": allowed,
            "metrics": {k: r["metrics"] for k, r in sorted(results.items()) if r["metrics"]},
        }, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"보고서 → {REPORT.relative_to(ROOT)} · 캡처 → {SHOTS.relative_to(ROOT)}")
    return 1 if (unallowed or unreached or stale) else 0


def reclassify() -> int:
    """브라우저를 다시 띄우지 않고 **지난 순회의 날것의 결과를 지금 등록부로 다시 가른다.**

    허용·알려진 깨짐 등록부를 고칠 때마다 20분짜리 순회를 다시 돌리지 않으려는 것이다. 대신
    **화면 코드가 그대로이고 전체 순회였을 때만** 한다 — digest 가 다르면 검출 자체가 낡았다.
    판정 규칙(SCAN_JS)이나 화면 목록을 바꿨다면 이 방법으로는 반영되지 않는다 — 순회를 다시 돈다.
    """
    if not RESULTS.exists():
        raise SystemExit("다시 가를 결과가 없다 — 먼저 순회를 돈다")
    raw = json.loads(RESULTS.read_text(encoding="utf-8"))
    if raw["digest"] != source_digest(FRONTEND):
        raise SystemExit("화면 코드가 순회 뒤에 바뀌었다 — 검출이 낡았으므로 순회를 다시 돈다")
    results = raw["results"]
    screens = [s["name"] for s in SCENARIOS]
    viewports = [f"{w}x{h}" for w, h in VIEWPORTS]
    missing = [f"{s}@{w}" for w, _ in VIEWPORTS for s in screens if f"{s}@{w}" not in results]
    if missing:
        raise SystemExit(f"지난 순회가 전체가 아니다 (빠진 {len(missing)}: {missing[:5]}…) — 순회를 다시 돈다")
    return write_report(results, screens, viewports, partial=False)


def main() -> int:
    ap = argparse.ArgumentParser(description="017 화면 깨짐 순회")
    ap.add_argument("--only", default="", help="쉼표로 가른 화면 이름")
    ap.add_argument("--viewports", default="", help="쉼표로 가른 폭 (예: 1280,1440)")
    ap.add_argument("--reclassify", action="store_true", help="지난 보고서의 검출을 지금 등록부로 다시 가른다")
    args = ap.parse_args()
    if args.reclassify:
        return reclassify()
    only = {n for n in args.only.split(",") if n}
    widths = {int(n) for n in args.viewports.split(",") if n}
    partial = bool(only or widths)
    scenarios = [s for s in SCENARIOS if not only or s["name"] in only]
    viewports = [v for v in VIEWPORTS if not widths or v[0] in widths]

    from playwright.sync_api import sync_playwright  # noqa: PLC0415

    if DATA.exists():
        shutil.rmtree(DATA)
    if SHOTS.exists() and not partial:
        # 좁혀 돌릴 때는 지난 캡처를 남긴다 — 결과를 합치듯 캡처도 그 화면만 새로 찍는다.
        shutil.rmtree(SHOTS)
    DATA.mkdir(parents=True)
    fixture = ensure_fixture()
    root = seed()
    results: dict = {}
    if partial and RESULTS.exists():
        # 좁혀 돌린 결과는 **지난 전체 결과에 덮어 합친다** — 화면 몇 개만 다시 재고 `--reclassify` 로
        # 보고서를 쓸 수 있게. 화면 코드가 그 뒤에 바뀌었으면 합치지 않는다 (섞인 결과가 된다).
        previous = json.loads(RESULTS.read_text(encoding="utf-8"))
        if previous.get("digest") == source_digest(FRONTEND):
            results = previous["results"]
            print(f"  지난 결과 {len(results)}개에 합친다")
    backend = ui = None
    try:
        backend, base = start_backend()
        api(base, "POST", "/api/project/open", {"path": str(root)})
        run_replays(base)
        stop(backend)
        # 새 제품 서버 — 프로젝트를 연 기억이 없어야 닫힌 화면을 잴 수 있다.
        backend, base = start_backend()
        ui, ui_base = start_ui(base)
        with sync_playwright() as pw:
            for phase in (CLOSED, OPEN, SESSION):
                group = [s for s in scenarios if s["phase"] == phase]
                if phase == OPEN:
                    api(base, "POST", "/api/project/open", {"path": str(root)})
                if phase == SESSION:
                    if not group:
                        continue
                    api(base, "POST", "/api/project/open", {"path": str(root)})
                    session = api(base, "POST", "/api/sessions", {"mode": "record", "start_url": f"{SAMPLE}/login.html"})
                    # **세션이 실제로 녹화 상태가 될 때까지 기다린다.** 고정 3초로 했더니 첫 폭(1280)에서
                    # 세션이 아직 `starting` 이라 작업 화면 대신 준비 표시가 그려졌고, 「이어서 보기」를
                    # 누르고도 국면 표시가 뜨지 않아 그 화면을 재지 못했다 (2회차 순회).
                    for _ in range(120):
                        if api(base, "GET", f"/api/sessions/{session['session_id']}").get("state") not in {"starting", ""}:
                            break
                        time.sleep(0.5)
                    else:
                        raise SystemExit("녹화 세션이 60초 안에 시작되지 않았다")
                if group:
                    capture(pw, ui_base, group, viewports, results)
                if phase == SESSION:
                    try:
                        api(base, "POST", f"/api/sessions/{session['session_id']}/discard")
                    except RuntimeError:
                        pass
    finally:
        stop(ui)
        stop(backend)
        stop(fixture)

    return write_report(results, [s["name"] for s in scenarios], [f"{w}x{h}" for w, h in viewports], partial)


if __name__ == "__main__":
    raise SystemExit(main())
