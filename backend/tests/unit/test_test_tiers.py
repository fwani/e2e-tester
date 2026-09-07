"""테스트 계층 분류가 낡지 않게 잠근다.

`-m "not browser"` 는 개발 루프의 기본 계층이다. 그 계층에 실제 스택을 띄우는 검증이
섞이면 루프가 다시 느려지고, **원인이 분류라는 것은 드러나지 않는다** — 그냥 느려질
뿐이다. 그래서 분류 자체를 검증한다.
"""

from __future__ import annotations

import ast
import pathlib
import re

from tests.tiers import HEAVY_FIXTURES, TIMING_MODULES

TESTS_DIR = pathlib.Path(__file__).resolve().parents[1]

# 픽스처가 "무겁다" 는 판정의 근거. 프로세스를 띄우거나 브라우저를 여는 호출이다.
HEAVY_CALLS = re.compile(r"subprocess\.Popen|chromium\.launch|async_playwright\(")


def _fixture_defs(path: pathlib.Path) -> dict[str, str]:
    """파일에 정의된 픽스처 이름 → 그 함수의 소스."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        decorated = any(
            "fixture" in ast.unparse(d) for d in node.decorator_list
        )
        if decorated:
            found[node.name] = ast.unparse(node)
    return found


def test_heavy_fixtures_list_is_complete() -> None:
    """프로세스·브라우저를 띄우는 픽스처가 `HEAVY_FIXTURES` 에 다 들어 있다.

    새 픽스처가 uvicorn 이나 Chromium 을 띄우면서 목록에 들어가지 않으면, 그것을
    쓰는 검증이 조용히 빠른 계층에 남는다. 이 검증이 그때 실패한다.
    """
    missing: dict[str, str] = {}
    for path in sorted(TESTS_DIR.rglob("*.py")):
        if path.name.startswith("test_"):
            continue  # 픽스처는 conftest·support 모듈에 둔다
        for name, source in _fixture_defs(path).items():
            if name in HEAVY_FIXTURES:
                continue
            if HEAVY_CALLS.search(source):
                missing[name] = str(path.relative_to(TESTS_DIR.parent))

    assert not missing, (
        "프로세스·브라우저를 띄우는 픽스처가 `HEAVY_FIXTURES` 에 없습니다. "
        f"이것을 쓰는 검증이 `-m \"not browser\"` 계층에 섞입니다: {missing}"
    )


def test_heavy_fixtures_all_exist() -> None:
    """목록의 이름이 실제로 정의돼 있다. 이름이 바뀌면 분류가 조용히 멈춘다."""
    defined: set[str] = set()
    for path in sorted(TESTS_DIR.rglob("*.py")):
        defined |= set(_fixture_defs(path))

    unknown = HEAVY_FIXTURES - defined
    assert not unknown, (
        f"`HEAVY_FIXTURES` 의 {unknown} 가 어디에도 정의돼 있지 않습니다. "
        "픽스처 이름이 바뀌었다면 목록도 함께 고치세요 — 그러지 않으면 그 픽스처를 "
        "쓰는 검증이 빠른 계층에 섞입니다."
    )


# 경과 시간을 단언하는 모양. `assert` 와 같은 줄에 시간에서 온 이름이 있는 경우다.
_ELAPSED_ASSERT = re.compile(
    r"assert\b[^\n]*\b(elapsed|elapsed_ms|p95|worst|median)\b"
)
_CLOCK_READ = re.compile(r"time\.(monotonic|perf_counter)\(\)")


def test_timing_modules_list_is_complete() -> None:
    """벽시계를 읽어 단언하는 모듈이 `TIMING_MODULES` 에 다 들어 있다.

    빠지면 그 검증이 병렬 실행에 섞여 **부하를 제품의 느림으로 보고한다**. 실측:
    8분할에서 녹화 반영 지연이 p95 737ms(목표 200ms)로 나왔다.

    새 검증이 시간을 재기 시작하면 이 검증이 먼저 실패하고, 고치는 방법은
    `TIMING_MODULES` 에 경로를 한 줄 넣는 것이다.
    """
    backend = TESTS_DIR.parent
    missing: list[str] = []
    for path in sorted(TESTS_DIR.rglob("test_*.py")):
        text = path.read_text(encoding="utf-8")
        if not (_CLOCK_READ.search(text) and _ELAPSED_ASSERT.search(text)):
            continue
        rel = path.relative_to(backend).as_posix()
        if rel not in TIMING_MODULES:
            missing.append(rel)

    assert not missing, (
        "벽시계를 읽어 단언하는 모듈이 `TIMING_MODULES` 에 없습니다. 병렬 실행에 섞이면 "
        f"부하를 제품의 느림으로 보고합니다: {missing}"
    )


def test_timing_modules_all_exist() -> None:
    """목록의 경로가 실제로 있다. 파일 이름이 바뀌면 분류가 조용히 멈춘다."""
    backend = TESTS_DIR.parent
    gone = [rel for rel in sorted(TIMING_MODULES) if not (backend / rel).is_file()]
    assert not gone, (
        f"`TIMING_MODULES` 의 {gone} 가 없습니다. 파일을 옮겼다면 목록도 함께 고치세요 — "
        "그러지 않으면 그 검증이 병렬 실행에 섞입니다."
    )


def test_headless_is_off_by_default_in_the_product() -> None:
    """제품 기본값은 **창을 띄우는 것**이다.

    검증은 창 없이 돈다 (`tests/conftest.py` 의 `_headless_browsers`). 그 편의가
    제품 기본값으로 새면 녹화·인수인계에서 사람이 조작할 창이 사라지고, 그때의 실패는
    원인이 이 설정이라는 것을 드러내지 않는다.

    환경 변수가 **켜져 있지 않을 때** 창을 띄우는지를 본다 — 픽스처가 켜 둔 값을
    잠시 걷어내고 판정한다.
    """
    import os

    from itb.execution.session import HEADLESS_ENV, headless_default

    saved = os.environ.pop(HEADLESS_ENV, None)
    try:
        assert headless_default() is False
    finally:
        if saved is not None:
            os.environ[HEADLESS_ENV] = saved


def test_unknown_headless_value_keeps_the_window() -> None:
    """알 수 없는 값을 창 없음으로 읽지 않는다.

    오타 하나로 사람이 조작할 창이 사라지면 안 된다 — 그 실패는 원인이 오타라는 것을
    드러내지 않는다.
    """
    import os

    from itb.execution.session import HEADLESS_ENV, headless_default

    saved = os.environ.get(HEADLESS_ENV)
    try:
        for value in ("", "0", "no", "off", "ture", "yes please"):
            os.environ[HEADLESS_ENV] = value
            assert headless_default() is False, f"{value!r} 를 창 없음으로 읽었다"
        for value in ("1", "true", "TRUE", " yes ", "on"):
            os.environ[HEADLESS_ENV] = value
            assert headless_default() is True, f"{value!r} 를 창 없음으로 읽지 못했다"
    finally:
        if saved is None:
            os.environ.pop(HEADLESS_ENV, None)
        else:
            os.environ[HEADLESS_ENV] = saved


def test_ci_runs_the_timing_tier() -> None:
    """CI 가 **순차 계층을 반드시 돈다.**

    병렬 실행에서 `-m "not timing"` 로 42건이 빠진다. 그 42건을 돌리는 단계가 CI 에서
    사라지면 아무도 알려 주지 않고 **재지 않은 것이 통과로 보인다** (헌법 품질 게이트 4).
    그래서 워크플로 파일에서 그 단계의 존재를 확인한다.

    파일 내용을 문자열로 본다 — YAML 파서를 끌어오면 검증이 파서 버전에 묶인다.
    """
    ci = TESTS_DIR.parents[1] / ".github" / "workflows" / "ci.yml"
    assert ci.is_file(), f"CI 워크플로가 없습니다: {ci}"
    text = ci.read_text(encoding="utf-8")

    # 병렬 계층이 timing 을 빼면, 그것을 다시 도는 단계가 있어야 한다.
    excludes = "not timing" in text
    runs_timing = "-m timing" in text or 'timing and not browser' in text
    assert not excludes or runs_timing, (
        "CI 가 `not timing` 으로 42건을 빼면서 그것을 다시 도는 단계가 없습니다. "
        "재지 않은 것이 통과로 보입니다 — `-m timing ... -n 0` 단계를 되살리세요."
    )

    # 순차 계층은 프로세스 하나로 돌아야 한다.
    if runs_timing:
        assert "-n 0" in text, (
            "순차 계층 단계가 `-n 0` 없이 돕니다. 나눠 돌면 재는 값이 그 순간의 "
            "부하가 되고, 그 실패는 원인이 분배라는 것을 드러내지 않습니다."
        )
