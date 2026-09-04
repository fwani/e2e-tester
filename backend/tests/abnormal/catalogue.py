"""이상 조작 시나리오 목록을 읽고 판정 3축으로 재는 장치.

목록의 **유일한 권위 위치**는 `specs/003-error-path-hardening/contracts/abnormal-scenarios.json`
이다. 여기에 복사본을 두지 않는다 — 두 벌이 되면 조합 커버리지가 갈라진다 (research R3).

시나리오마다 검증 함수를 쓰지 않는다. 면(surface)마다 실행기 하나가 목록을 읽어 펼치고,
시나리오 하나는 식별자로 등록된 **실행 수단(driver)** 하나에 대응한다 (research R8).

    @driver("AS-001")
    def _empty_project_name(ctx: ApiContext) -> Attempt:
        resp = ctx.client.post("/api/project/create", json={"name": "   "})
        return Attempt.from_response(resp, preserved=ctx.registry_intact())

**등록되지 않은 시나리오는 건너뛰기가 아니라 실패다** (RG-106). 조용히 건너뛰면
"전건 통과"(SC-201)가 거짓이 된다.
"""

from __future__ import annotations

import json
import pathlib
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

# ─── 목록 위치 ──────────────────────────────────────────────────────────────
#
# backend/tests/abnormal/catalogue.py 에서 저장소 루트까지 세 층 위다.

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
CATALOGUE_PATH = (
    REPO_ROOT / "specs" / "003-error-path-hardening" / "contracts" / "abnormal-scenarios.json"
)

FAULTS = ("invalid-input", "order-violation", "external-failure", "concurrency")
SURFACES = ("api", "ui", "boundary")


@dataclass(frozen=True)
class Scenario:
    """목록의 항목 하나. 기대 응답은 담지 않는다 — 판정은 3축이 한다."""

    id: str
    fault: str
    surface: str
    target: str
    operation: str
    must_be_rejected: bool
    preserves: str | None

    def __str__(self) -> str:  # 실패 메시지에 그대로 실린다
        return f"{self.id} [{self.fault}/{self.surface}] {self.operation} ({self.target})"


def load_catalogue() -> dict[str, Any]:
    if not CATALOGUE_PATH.exists():
        raise FileNotFoundError(
            f"시나리오 목록이 없습니다: {CATALOGUE_PATH}\n"
            "목록은 specs 아래 한 곳에만 있다. 복사본을 만들지 말고 원본을 확인하세요."
        )
    return json.loads(CATALOGUE_PATH.read_text(encoding="utf-8"))


def scenarios(surface: str | None = None) -> list[Scenario]:
    raw = load_catalogue()["scenarios"]
    items = [
        Scenario(
            id=s["id"],
            fault=s["fault"],
            surface=s["surface"],
            target=s["target"],
            operation=s["operation"],
            must_be_rejected=s["must_be_rejected"],
            preserves=s["preserves"],
        )
        for s in raw
    ]
    return [s for s in items if surface is None or s.surface == surface]


# ─── 실행 수단 레지스트리 ───────────────────────────────────────────────────

Driver = Callable[..., "Attempt"]
DRIVERS: dict[str, Driver] = {}


def driver(scenario_id: str) -> Callable[[Driver], Driver]:
    """시나리오 하나의 실행 수단을 등록한다."""

    def register(fn: Driver) -> Driver:
        if scenario_id in DRIVERS:
            raise RuntimeError(f"{scenario_id} 의 실행 수단이 이미 등록돼 있습니다")
        DRIVERS[scenario_id] = fn
        return fn

    return register


# ─── 조작 결과 ──────────────────────────────────────────────────────────────


@dataclass
class Attempt:
    """이상 조작 하나를 가한 결과. 판정 3축이 이것을 읽는다."""

    rejected: bool
    """조작이 거부되었는가. `must_be_rejected` 와 맞춰 "조용한 성공"을 판별한다."""

    error: dict[str, Any] | None = None
    """계약 형태 오류 본문(`{code, category, message, next_action, detail}`). 없으면 ``None``."""

    surfaced: str | None = None
    """사용자에게 드러난 내용. 화면 면은 화면 텍스트, 그 밖은 ``None``(오류 본문으로 판정)."""

    preserved: bool | None = None
    """`preserves` 가 가리키는 것이 남아 있는가. 보존 대상이 없는 시나리오는 ``None``."""

    crashed: bool = False
    """처리되지 않은 오류로 무너졌는가 (분류가 ``broken``)."""

    no_response: bool = False
    """응답이 오지 않았는가 (시간 초과·연결 끊김)."""

    notes: list[str] = field(default_factory=list)

    @classmethod
    def from_response(cls, resp: Any, *, preserved: bool | None = None) -> Attempt:
        """요청 응답 하나에서 결과를 만든다. 요청 경계·외부 경계가 쓴다."""
        body: dict[str, Any] | None = None
        if resp.status_code != 204 and resp.content:
            try:
                parsed = resp.json()
            except ValueError:
                parsed = None
            if isinstance(parsed, dict):
                body = parsed.get("error")

        return cls(
            rejected=resp.status_code >= 400,
            error=body,
            preserved=preserved,
            crashed=bool(body and body.get("category") == "broken"),
        )


# ─── 판정 3축 ───────────────────────────────────────────────────────────────
#
# data-model.md §2.3. **세 축을 모두 통과해야 그 시나리오가 통과다.**

# 오류에 새어 나오면 안 되는 것 — 내부 경로와 호출 스택 (003 EC-005)
_LEAK = re.compile(
    r"""(
        /Users/ | /home/ | [A-Z]:\\        # 절대 경로
      | Traceback\ \(most\ recent          # 호출 스택
      | \bFile\ "[^"]+",\ line\ \d+        # 스택 프레임
      | site-packages/ | \bsrc/itb/        # 내부 모듈 경로
    )""",
    re.VERBOSE,
)

REQUIRED_ERROR_FIELDS = {"code", "category", "message", "next_action", "detail"}


class AxisFailure(AssertionError):
    """판정축 하나가 어긋났다. 메시지에 시나리오와 축을 함께 싣는다."""

    def __init__(self, scenario: Scenario, axis: str, why: str) -> None:
        super().__init__(f"{scenario}\n  판정축 {axis} 실패 — {why}")


def check_axis1_shape(sc: Scenario, at: Attempt) -> None:
    """① 응답의 형태 — 구조화된 거부인가, 조용한 성공·무응답·깨짐이 아닌가."""
    if at.no_response:
        raise AxisFailure(sc, "①", "응답이 오지 않았다")

    if sc.must_be_rejected and not at.rejected:
        raise AxisFailure(
            sc, "①", "허용되어서는 안 되는 조작이 성공했다 (조용한 성공). EC-007"
        )

    if not sc.must_be_rejected and at.crashed:
        raise AxisFailure(sc, "①", "정상 조작인데 제품이 깨졌다 (category=broken)")

    if at.error is None:
        if at.rejected:
            raise AxisFailure(sc, "①", "거부되었는데 계약 형태 오류 본문이 없다")
        return

    missing = REQUIRED_ERROR_FIELDS - set(at.error)
    if missing:
        raise AxisFailure(sc, "①", f"오류 본문에 필드가 없다: {sorted(missing)}")

    if at.error["category"] not in ("blocked", "broken"):
        raise AxisFailure(sc, "①", f"분류가 알 수 없는 값이다: {at.error['category']!r}")

    if not str(at.error["message"]).strip():
        raise AxisFailure(sc, "①", "message 가 비어 있다")

    blob = json.dumps(at.error, ensure_ascii=False)
    leak = _LEAK.search(blob)
    if leak:
        raise AxisFailure(sc, "①", f"내부 경로·스택이 노출됐다: {leak.group(0)!r}. EC-005")


def check_axis2_user(sc: Scenario, at: Attempt) -> None:
    """② 사용자 관점 — 무엇이 잘못됐는지와 다음 행동이 사용자에게 닿는가.

    문구의 **품질**은 재지 않는다 (명세의 가정). 존재 여부만 본다.
    """
    if at.error is not None:
        if not str(at.error.get("next_action", "")).strip():
            raise AxisFailure(sc, "②", "다음 행동이 비어 있다. EC-004")

    if sc.surface != "ui":
        return

    if at.surfaced is None:
        raise AxisFailure(sc, "②", "화면 면인데 화면에 드러난 내용이 수집되지 않았다")
    if not at.surfaced.strip():
        raise AxisFailure(sc, "②", "화면에 아무것도 드러나지 않았다 (조작이 삼켜졌다). AP-003")


def check_axis3_preserved(sc: Scenario, at: Attempt) -> None:
    """③ 상태 보존 — 조작 뒤에도 직전까지의 작업이 남아 이어서 할 수 있는가."""
    if sc.preserves is None:
        return
    if at.preserved is None:
        raise AxisFailure(
            sc, "③", f"'{sc.preserves}' 의 보존 여부가 확인되지 않았다 (수단이 재지 않았다)"
        )
    if not at.preserved:
        raise AxisFailure(sc, "③", f"'{sc.preserves}' 가 유실됐다. AP-002")


def judge(sc: Scenario, at: Attempt) -> None:
    """세 축을 모두 재고, 하나라도 어긋나면 그 자리에서 실패한다."""
    check_axis1_shape(sc, at)
    check_axis2_user(sc, at)
    check_axis3_preserved(sc, at)
