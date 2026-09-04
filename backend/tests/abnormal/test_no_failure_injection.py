"""T031 — 이 라운드가 들여온 실패 대역이 **검증 코드에만** 있다는 증거.

헌법 원칙 II(NON-NEGOTIABLE)는 저장된 테스트의 재실행 경로에서 언어모델 호출이 **코드
구조상 도달 불가능**할 것을 요구한다. 이 라운드는 AI 실패·쓰기 중단·대상 사이트 이상을
재현하는 대역을 새로 들여왔다. 그것이 제품 코드로 새어 들어가면 원칙이 무너진다.

`.importlinter` 가 임포트 경계를 빌드에서 강제한다. 이 파일은 그것이 잡지 못하는 것을
본다 — **런타임 스위치**다. 임포트를 늘리지 않고 환경 변수 하나로 실패를 흉내 내는 분기는
계약 검사를 통과하면서 원칙을 깬다.

세 가지를 확인한다.

1. 제품 코드에 검증 대역의 이름이 하나도 없다
2. 제품 코드에 실패를 켜는 런타임 스위치가 없다
3. 대역이 바꿔치는 지점을 **제품이 아니라 검증 코드만** 만진다
"""

from __future__ import annotations

import pathlib
import re

SRC = pathlib.Path(__file__).resolve().parents[2] / "src" / "itb"
TESTS = pathlib.Path(__file__).resolve().parents[1]

PRODUCT_FILES = sorted(SRC.rglob("*.py"))

FAKE_NAMES = (
    "ai_failing",
    "ai_timing_out",
    "ai_returning_garbage",
    "ai_asking_for_unknown_step",
    "ai_transport_failing",
    "writes_interrupted",
    "_HalfWriter",
    "BoundaryContext",
    "ApiContext",
    "UiContext",
    "_PassthroughResolver",
)
"""검증 대역의 이름. 제품 코드에서 하나라도 보이면 대역이 새어 나온 것이다."""

# 실패를 켜는 런타임 스위치. 이름이 아니라 **모양**으로 찾는다 — 새 이름으로 들어와도
# 걸리도록. 환경 변수를 읽어 실패·지연·대역을 고르는 분기가 대상이다.
SWITCH = re.compile(
    r"""(
        (?:getenv|environ(?:\.get)?)\s*[(\[]\s*["'][A-Z_]*
            (?:FAIL|FAULT|CHAOS|SIMULAT|INJECT|MOCK|FAKE|STUB|BREAK)[A-Z_]*["']
      | \b(?:simulate|inject)_(?:failure|error|fault|timeout)\b
      | \bfail_injection\b
    )""",
    re.VERBOSE | re.IGNORECASE,
)


def test_product_code_has_no_test_double_names() -> None:
    """제품 코드가 검증 대역의 이름을 하나도 모른다."""
    found: list[str] = []
    for path in PRODUCT_FILES:
        body = path.read_text(encoding="utf-8")
        for name in FAKE_NAMES:
            if name in body:
                found.append(f"{path.relative_to(SRC)} 에 {name}")
    assert not found, (
        "검증 대역의 이름이 제품 코드에 있다 — 대역이 제품으로 새어 나왔다 "
        f"(헌법 원칙 II): {found}"
    )


def test_product_code_has_no_failure_switch() -> None:
    """제품 코드에 실패를 켜는 런타임 스위치가 없다.

    임포트 계약은 이것을 잡지 못한다 — 새 임포트가 필요 없기 때문이다. 그래서 따로 본다.
    """
    found: list[str] = []
    for path in PRODUCT_FILES:
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if SWITCH.search(line):
                found.append(f"{path.relative_to(SRC)}:{lineno} — {line.strip()[:100]}")
    assert not found, f"제품 코드에 실패 주입 스위치가 있다 (헌법 원칙 II): {found}"


def test_only_test_code_swaps_the_llm_boundary() -> None:
    """대역이 바꿔치는 지점을 제품이 아니라 **검증 코드만** 만진다.

    `itb.llm.client.create_client` 와 `itb.authoring.agent._sdk_driver` 가 그 지점이다.
    제품이 스스로를 바꿔치면 그것은 대역이 아니라 제품의 기능이 된다.
    """
    swappers = [
        path
        for path in PRODUCT_FILES
        if "monkeypatch" in path.read_text(encoding="utf-8")
        or "setattr(itb" in path.read_text(encoding="utf-8")
    ]
    assert not swappers, (
        f"제품 코드가 다른 모듈을 바꿔치고 있다: {[str(p.relative_to(SRC)) for p in swappers]}"
    )

    # 검증 코드 쪽에는 실제로 있어야 한다. 없다면 대역이 동작하지 않는 것이므로
    # AS-013·AS-014·AS-034·AS-035·AS-042 는 아무것도 재지 않는다.
    test_bodies = "\n".join(
        p.read_text(encoding="utf-8") for p in TESTS.rglob("*.py")
    )
    assert "itb.llm.client.create_client" in test_bodies, (
        "AI 경계를 바꿔치는 대역이 검증 코드에 없다 — 외부 실패 시나리오가 재는 것이 없다"
    )
    assert "itb.authoring.agent._sdk_driver" in test_bodies, (
        "도구 루프를 바꿔치는 대역이 검증 코드에 없다 (AS-013·AS-014)"
    )


def test_the_replay_path_still_cannot_reach_the_llm() -> None:
    """재실행 경로가 언어모델 경계에 닿지 못한다.

    `.importlinter` 가 빌드에서 강제하지만, 이 라운드가 `execution` 에 `domain.error`
    임포트를 더했으므로 여기서도 확인해 둔다 — 계약이 깨진 순간을 검증이 먼저 잡는다.
    """
    import importlib

    replay_path = (
        "itb.execution.session",
        "itb.execution.runner",
        "itb.execution.step_executor",
        "itb.storage.repository",
        "itb.storage.atomic",
        "itb.domain.error",
    )
    for name in replay_path:
        module = importlib.import_module(name)
        reached = {
            getattr(value, "__module__", "") or "" for value in vars(module).values()
        }
        offenders = sorted(
            n
            for n in reached
            if n.startswith(("itb.llm", "itb.authoring", "anthropic"))
        )
        assert not offenders, f"{name} 이 언어모델 경계에 닿는다: {offenders}"
