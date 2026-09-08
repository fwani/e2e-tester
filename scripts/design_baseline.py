#!/usr/bin/env python3
"""디자인 `docs/design/008-visual-language/*.dc.html` 에서 대조 기준값을 기계적으로 뽑는다.

DC-012 의 대조 기록은 "보고 비슷한가" 가 아니라 **디자인에서 뽑은 값과의 대조**여야
한다. 이 스크립트는 그 기준값 칸만 채운다.

**판정하지 않는다.** `관측값`·`판정` 칸은 리뷰어 소유다
(contracts/design-conformance.md §4).

## 2026-09-08 (US4) — 축을 통계에서 규칙으로 바꿨다

**이전 축은 사람이 채울 수 없는 형태였다.** 화면당 26칸 × 18장 = 509칸을 사람이 눈으로
채워야 했고, 같은 구조를 001·002 가 두 번 시도해 두 번 다 미완으로 남았다 (001 T156 ·
002 T099 · SC-108 은 지금도 미충족).

그리고 그 축은 `div 141개`·`#1A7F45 5회` 같은 텍스트 통계라 **원리적으로** 놓치는 것이
있었다 — 행 결말 마커가 빠져도, 필터가 없어도, 격자가 grid 에서 flex 로 바뀌어도 세지지
않는다 (spec V-10).

이제 셋으로 나눈다 (`contracts/design-conformance.md` §2).

    L1 값     정본 시트 ↔ 확정 디자인 시트   기계 (scripts/design_render.py)
    L2 소비   화면 코드 ↔ 정본                기계 (frontend/scripts/count-violations.mjs)
    L3 구조   화면 ↔ 확정 디자인              사람, **화면당 3항목**

L1 이 참이고 L2 가 참이면 색·기하·타이포는 **구성상** 화면 = 디자인이다. 사람이 볼 것은
L3 만 남는다 — 509칸이 54칸이 된다.

## 2026-09-08 — 기준이 008 로 옮겨졌다

이전 기준(`docs/design/*.dc.html` 8종 · `007-rework/` 11장)은 폐기했고
`docs/design/_retired/` 로 옮겼다. **이 스크립트는 그 디렉터리를 읽지 않는다** —
남아 있는 이유는 002·007 의 과거 판정을 다시 읽기 위해서이지 기준으로 쓰기 위해서가
아니다 (`_retired/README.md`).

시각 언어가 v1「브루탈리스트」에서 v2「계기판」으로 바뀌었다. `assert_baseline` 의
단언도 함께 뒤집혔다 — 아래 주석을 보라.

    python3 scripts/design_baseline.py --json     # 사실만 JSON 으로
    python3 scripts/design_baseline.py --write    # 대조표 + 미정의 상태 파일 생성

기준이 바뀌면(디자인 파일이 갱신되면) 다시 돌린다.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DESIGN = ROOT / "docs" / "design" / "008-visual-language"
CANVAS = DESIGN / "canvas.json"
OUT_DIR = DESIGN / "conformance"

# 화면 식별자 → (dc.html 파일, 제품의 대응 파일).
#
# 통합 작업 화면의 여덟 국면은 **같은 껍데기의 상태**이므로 대응 파일이 겹친다 —
# 그것이 007 이 만든 구조이고, 겹치는 것이 정상이다 (SC-001 · 구현 1벌).
SCREENS: dict[str, tuple[str, str]] = {
    "ProjectSetup": ("ProjectSetup.dc.html", "frontend/src/pages/ProjectSetup.tsx"),
    "EmptyList": ("EmptyList.dc.html", "frontend/src/pages/TestList.tsx (테스트 0개)"),
    "TestList": ("TestList.dc.html", "frontend/src/pages/TestList.tsx"),
    "Create": ("Create.dc.html", "frontend/src/pages/ComposeView.tsx"),
    "Record": ("Record.dc.html", "frontend/src/pages/SessionScreen.tsx (REC)"),
    "AiWriting": ("AiWriting.dc.html", "frontend/src/pages/SessionScreen.tsx (AI)"),
    "AiBlocked": ("AiBlocked.dc.html", "frontend/src/pages/SessionScreen.tsx (AI 차단)"),
    "Takeover": ("Takeover.dc.html", "frontend/src/pages/SessionScreen.tsx (TKO)"),
    "Run": ("Run.dc.html", "frontend/src/pages/SessionScreen.tsx (RUN)"),
    "Paused": ("Paused.dc.html", "frontend/src/pages/SessionScreen.tsx (PAU)"),
    "Finished": ("Finished.dc.html", "frontend/src/pages/SessionScreen.tsx (실행 종료)"),
    "Result": ("Result.dc.html", "frontend/src/pages/ResultView.tsx"),
    "Edit": ("Main.dc.html", "frontend/src/pages/EditView.tsx"),
    "StepDetail": ("StepDetail.dc.html", "frontend/src/components/workbench/StepDetail.tsx"),
    "Keys": ("Keys.dc.html", "frontend/src/pages/KeyManagement.tsx"),
    "Secrets": ("Secrets.dc.html", "frontend/src/pages/SecretValues.tsx"),
    "Language": ("Language.dc.html", "frontend/src/theme/tokens.css"),
    "States": (
        "States.dc.html",
        "frontend/src/components/{ErrorNotice,SessionLostBanner,"
        "LiveConnectionBanner,StartingIndicator}.tsx",
    ),
}

# 라운드별 기록 분기는 더 이상 필요 없다 — 기준이 한 벌이다. 과거 라운드의 기록은
# `specs/00{2,7}-*/design-conformance/` 에 그대로 있고 그 파일들이 가리키는 디자인은
# `docs/design/_retired/` 에 있다.


# 국면 화면 → 그 국면의 이름. 국면이 아닌 화면(목록·설정·언어 시트)은 여기 없다.
PHASE_OF: dict[str, str] = {
    "Create": "만들기",
    "Record": "녹화",
    "AiWriting": "AI 작성",
    "AiBlocked": "AI 작성 · 막힘",
    "Takeover": "사람이 이어받기",
    "Run": "실행 중",
    "Paused": "일시정지",
    "Finished": "실행 종료",
    "Result": "결과",
    "Edit": "편집",
}


L1_REPORT = ROOT / "frontend" / "tests" / "l1-report.json"


def read_l1() -> dict[str, Any] | None:
    """L1 대조 결과. `scripts/design_render.py --compare` 가 남긴다."""
    if not L1_REPORT.exists():
        return None
    return json.loads(L1_REPORT.read_text(encoding="utf-8"))


def read_l2() -> dict[str, Any] | None:
    """L2 소비 대조 결과. 가드와 **같은 함수**를 부른다 — 규칙을 두 곳에 두지 않는다."""
    counter = ROOT / "frontend" / "scripts" / "count-violations.mjs"
    if not counter.exists():
        return None
    try:
        out = subprocess.run(
            ["node", str(counter), "--json"], capture_output=True, text=True, check=True
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    return json.loads(out)


def l2_for(report: dict[str, Any] | None, target: str) -> dict[str, int] | None:
    """한 화면의 대상 파일들만 골라 센다. `target` 은 `{a,b}` 중괄호 묶음일 수 있다."""
    if report is None:
        return None
    files = _expand_target(target)
    rows = [r for r in report["rows"] if r["file"] in files]
    return {
        "color": sum(r["color"] for r in rows),
        "inline": sum(r["inline"] for r in rows),
        "offPalette": sum(len(r["offPalette"]) for r in rows),
    }


def _expand_target(target: str) -> set[str]:
    """`components/{A,B}.tsx (설명)` 같은 표기를 실제 경로 집합으로 편다."""
    path = target.split(" (")[0].strip()
    m = re.search(r"\{([^}]*)\}", path)
    if m is None:
        return {path}
    return {path.replace(m.group(0), part.strip()) for part in m.group(1).split(",")}


def out_dir_for(name: str) -> Path:
    """화면 식별자 → 대조 기록을 쓸 디렉터리. 지금은 한 곳이다."""
    return OUT_DIR


# ─── 추출 ───────────────────────────────────────────────────────────────────


def _counted(pattern: str, text: str) -> list[tuple[str, int]]:
    """등장 횟수 내림차순. 같은 횟수면 값 순으로 — 실행마다 결과가 흔들리면 안 된다."""
    found: dict[str, int] = {}
    for m in re.findall(pattern, text):
        found[m] = found.get(m, 0) + 1
    return sorted(found.items(), key=lambda kv: (-kv[1], kv[0]))


def extract(path: Path) -> dict[str, Any]:
    """한 dc.html 의 시각적 사실을 뽑는다. 해석하지 않는다."""
    text = path.read_text(encoding="utf-8")

    # 최상위 컨테이너의 선언 폭·최소 높이. 아트보드의 기준 치수다.
    # 008 의 아트보드는 `width:1440px;height:900px` 로 쓴다. 이전 판은 `min-height` 만
    # 받아서 008 을 읽으면 전부 None 이 됐다 — 둘 다 받는다.
    root = re.search(r"width:\s*(\d+)px;\s*(?:min-)?height:\s*(\d+)px", text)

    return {
        "file": path.name,
        "root_width": int(root.group(1)) if root else None,
        "root_min_height": int(root.group(2)) if root else None,
        "div_count": len(re.findall(r"<div", text)),
        "svg_count": len(re.findall(r"<svg", text)),
        "colors": _counted(r"#[0-9A-Fa-f]{6}", text.upper()),
        "borders": _counted(r"border(?:-[a-z]+)?:\s*(\d+px solid [^;\"]*)", text),
        "border_widths": _counted(r"border(?:-[a-z]+)?:\s*(\d+px) solid", text),
        "shadows": _counted(r"box-shadow:\s*([^;\"]+)", text),
        "fonts": _counted(r"font-family:\s*('[^']+')", text),
        # 고정 높이가 선언된 영역 — 헤더 바 등. 치수 대조의 핵심 항목이 된다.
        "fixed_heights": _counted(r"(?:flex:\s*0 0 (\d+)px|height:\s*(\d+)px)", text),
        "radius_occurrences": len(re.findall(r"radius", text, re.IGNORECASE)),
    }


def collect() -> dict[str, Any]:
    if not DESIGN.is_dir():
        sys.exit(f"확정 디자인 디렉터리가 없습니다: {DESIGN}")

    canvas = json.loads(CANVAS.read_text(encoding="utf-8")) if CANVAS.exists() else {}
    frames = {a["file"]: a for a in canvas.get("artboards", [])}

    screens: dict[str, Any] = {}
    for name, (dc_name, target) in SCREENS.items():
        path = DESIGN / dc_name
        if not path.exists():
            # 기준이 한 벌이므로 빠진 파일은 언제나 오류다. 이전 판에는 "초안이 아직
            # 없을 수 있다" 는 예외가 있었는데, 그 예외가 필요했던 라운드는 끝났다.
            sys.exit(f"디자인 파일이 없습니다: {path}")
        facts = extract(path)
        frame = frames.get(dc_name, {})
        facts["artboard_w"] = frame.get("w")
        facts["artboard_h"] = frame.get("h")
        facts["title"] = frame.get("title", name)
        facts["target"] = target
        screens[name] = facts

    total_radius = sum(s["radius_occurrences"] for s in screens.values())
    return {
        "screens": screens,
        "totals": {
            "div": sum(s["div_count"] for s in screens.values()),
            "svg": sum(s["svg_count"] for s in screens.values()),
            "radius_occurrences": total_radius,
        },
    }


def assert_baseline(data: dict[str, Any]) -> None:
    """기준이 바뀌면 즉시 드러나야 한다.

    ## 2026-09-08 — 이 단언은 뒤집혔다

    이전 판은 `radius` 가 **0회**여야 한다고 단언했다. 그것이 v1「브루탈리스트」의
    정의였고, 그 주석은 이렇게 예고하고 있었다 — "확정 디자인이 나중에 둥근 모서리를
    도입하면 구현 쪽 회귀 가드가 거꾸로 틀린 것이 된다. 그 순간을 조용히 지나치지
    않도록 여기서 막는다."

    그 순간이 왔다. v2「계기판」은 모서리 2·3·6px 를 **의도적으로** 쓰고, 1px 실선
    테두리를 기본으로 쓰며, 하드 오프셋 그림자를 쓰지 않는다. 그래서 단언을 뒤집는다 —
    없어야 할 것을 세는 대신 **있어야 할 것**을 센다. 다음에 언어가 또 바뀌면 이 함수가
    다시 멈춘다. 그것이 이 함수의 일이다.

    `frontend/tests/DesignTokens.test.tsx` 가 아직 v1 을 단언하고 있다 — 코드 전환의
    첫 관문이다.
    """
    radius = data["totals"]["radius_occurrences"]
    if radius == 0:
        sys.exit(
            "기준이 바뀌었습니다: 디자인에 'radius' 가 0회입니다. v2「계기판」은 모서리를 "
            "씁니다. v1 로 되돌린 것이라면 DesignTokens.test.tsx 와 함께 재검토하세요."
        )

    # 하드 오프셋 그림자(흐림 반경 0)는 v1 의 서명이었다. v2 에 남아 있으면 두 언어가
    # 섞인 것이다.
    #
    # `Language` 만 예외다 — 그 시트는 v1 버튼과 v2 버튼을 **나란히 놓아 왜 바꿨는지**
    # 보여준다. 표본으로 그린 것이지 이 언어의 일부가 아니다. 예외를 이름으로 못 박아
    # 두면 다른 화면에 섞여 들어올 때는 그대로 걸린다.
    SPECIMEN = {"Language"}
    hard = [
        (name, v)
        for name, s in data["screens"].items()
        if name not in SPECIMEN
        for v, _ in s["shadows"]
        if re.match(r"^\s*\d+px \d+px 0(\s|$)", v)
    ]
    if hard:
        sys.exit(f"v1 의 하드 오프셋 그림자가 남아 있습니다: {hard[:5]}")

    missing = [n for n, s in data["screens"].items() if not s["colors"]]
    if missing:
        sys.exit(f"색을 추출하지 못한 화면이 있습니다: {missing}. 추출 규칙을 확인하세요.")


# ─── 대조표 생성 ────────────────────────────────────────────────────────────

AXES_NOTE = """\
| 층 | 무엇을 대조하나 | 판정 | 어떻게 |
|---|---|---|---|
| **L1 값** | 정본 시트 ↔ 확정 디자인 시트 | 기계 | chromium 계산값 비교 (`scripts/design_render.py`) |
| **L2 소비** | 화면 코드 ↔ 정본 | 기계 | `frontend/scripts/count-violations.mjs` |
| **L3 구조** | 화면 ↔ 확정 디자인 | **사람** | 확정 디자인을 열고 제품과 나란히 본다 |

**L1 이 참이고 L2 가 참이면 색·기하·타이포는 구성상 화면 = 디자인이다.** 사람이 볼 것은
L3 셋뿐이다. DC 요구사항은 하나도 버리지 않았고 넷이 사람에게서 기계로 옮겨졌다
(`contracts/design-conformance.md` §7).
"""

# L3 — 사람이 보는 셋. **화면당 이 셋을 넘지 않는다** (FR-282 · DC-B).
L3_ITEMS: list[tuple[str, str, str]] = [
    (
        "L3-1 가감",
        "확정 디자인에 있는 요소가 전부 있는가. 없는 것을 더하지 않았는가",
        "DC-003 · DC-007",
    ),
    ("L3-2 구조", "영역 분할·순서·계층이 확정 디자인과 같은가", "DC-002"),
    (
        "L3-3 상태",
        "각 상태가 확정 디자인의 표현으로 구분되는가. **색만으로 구분하지 않는가**",
        "DC-006",
    ),
]


def _l1_rows(l1: dict[str, Any] | None) -> list[tuple[str, str, str]]:
    """L1 은 화면마다 같다 — 정본 시트 하나가 18장 전부의 기준이기 때문이다."""
    if l1 is None:
        return [("계산값 대조", "아직 재지 않았다", "미판정")]
    n = len(l1["mismatches"])
    rows = [
        (
            f"형태 {l1['forms']} × 속성 {l1['props']}",
            f"{l1['compared']}칸 — chromium 계산값",
            "일치" if n == 0 else f"불일치 {n}건",
        )
    ]
    for m in l1["mismatches"][:10]:
        rows.append((f".{m['form']} {m['prop']}", str(m["expected"]), f"불일치 — {m['observed']}"))
    return rows


def _l2_rows(l2: dict[str, int] | None) -> list[tuple[str, str, str]]:
    if l2 is None:
        return [("소비 대조", "아직 재지 않았다", "미판정")]
    return [
        ("색 리터럴", "0", "일치" if l2["color"] == 0 else f"불일치 — {l2['color']}건"),
        ("인라인 시각 언어 선언", "0", "일치" if l2["inline"] == 0 else f"불일치 — {l2['inline']}건"),
        ("정본 팔레트 밖의 색", "0종", "일치" if l2["offPalette"] == 0 else f"불일치 — {l2['offPalette']}종"),
    ]


def write_tables(data: dict[str, Any], only: str | None = None) -> list[Path]:
    """대조표를 쓴다.

    `only` 를 주면 그 화면 하나만 쓴다. **이것이 없으면 기준값을 다시 뽑을 때 사람이 채운
    L3 판정까지 함께 지워진다** — 판정은 사람의 것이고 되살릴 수 없다.

    L1·L2 칸은 **검사가 채운다.** 사람이 손으로 적지 않는다 (DC-A).
    """
    written: list[Path] = []
    l1 = read_l1()
    l2_all = read_l2()

    for name, s in data["screens"].items():
        if only is not None and name != only:
            continue
        target_dir = out_dir_for(name)
        target_dir.mkdir(parents=True, exist_ok=True)

        l1_body = "\n".join(f"| {a} | {b} | {c} |" for a, b, c in _l1_rows(l1))
        l2_body = "\n".join(
            f"| {a} | {b} | {c} |" for a, b, c in _l2_rows(l2_for(l2_all, s["target"]))
        )
        l3_body = "\n".join(f"| {n} | {q} | {dc} |  |  |" for n, q, dc in L3_ITEMS)

        phase = PHASE_OF.get(name)
        phase_note = (
            f"\n> 이 아트보드는 통합 작업 화면의 **「{phase}」 국면** 하나다. 껍데기는 다른 국면과 "
            f"같아야 하고(FR-217) 담는 것만 다르다.\n"
            if phase is not None
            else ""
        )

        out = target_dir / f"{name}.md"
        out.write_text(
            f"""# 디자인 대조 — {name} ({s["title"]})

**기준**: `docs/design/008-visual-language/{s["file"]}` — 아트보드 {s["artboard_w"]}×{s["artboard_h"]}
**대상**: `{s["target"]}`
**요구사항**: DC-002 ~ DC-007 · 완료 판정 **SC-401**

> **채택 2026-09-08** — 이 아트보드가 이 화면의 대조 기준이다. 이전 기준(`docs/design/_retired/`)은 폐기됐다.
{phase_note}
{AXES_NOTE}
## L1 — 값 (기계가 채운다)

정본 시트와 확정 디자인 시트를 **같은 마크업에 적용해 렌더한** 계산값 비교다. 표기 차이
(`#FFF` / `#ffffff` / `rgb(255,255,255)`)에 걸리지 않는다. 화면마다 같은 값인 이유는 정본이
한 벌이고 18장이 그 한 벌을 공유하기 때문이다.

| 항목 | 기준값 | 판정 |
|---|---|---|
{l1_body}

## L2 — 소비 (기계가 채운다)

이 화면의 대상 파일이 정본만 쓰는가. 규칙은 `contracts/visual-language.md` §4 가 정하고
가드(`frontend/tests/VisualLanguage.test.tsx`)가 같은 함수로 강제한다.

| 항목 | 기준값 | 판정 |
|---|---|---|
{l2_body}

## L3 — 구조·가감 (사람이 채운다)

**셋뿐이다.** 넷째가 필요하면 기계로 옮길 수 있는지 먼저 검토한다 (FR-282 · DC-B).

판정은 `일치` / `불일치` / `미판정` 중 하나. `불일치` 면 `비고` 에 차이를 적는다.
**구현자가 자기 구현을 판정하지 않는다** (DC-C · 002 가 세운 규칙).

| 항목 | 묻는 것 | 요구사항 | 판정 | 비고 |
|---|---|---|---|---|
{l3_body}

## 대조 방법

```bash
open docs/design/008-visual-language/{s["file"]}    # 확정 디자인 (그대로 열린다)
# 제품의 같은 화면을 나란히 띄우고 L3 셋을 본다
```

**완료 조건: `불일치`·`미판정` 이 각각 0건** (SC-401).
""",
            encoding="utf-8",
        )
        written.append(out)

    return written


def write_undefined_states() -> Path:
    """DC-009 — 확정 디자인이 정의하지 않아 구현자가 결정해야 했던 상태.

    한 파일에 모은다. 화면별로 흩어 두면 SC-110("기록 없는 임의 결정 0건")을 셀 수 없다.
    """
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / "undefined-states.md"
    if out.exists():
        return out  # 이미 기록이 쌓였으면 덮지 않는다

    out.write_text(
        """# 확정 디자인이 정의하지 않은 상태 기록

**요구사항**: DC-009 · 완료 판정 SC-110 (기록 없는 임의 결정 0건)

확정 디자인은 화면당 한 상태만 보여준다. 실제 동작에 필요한 나머지 상태(로딩·빈 목록·
오류·긴 목록·텍스트 넘침)는 구현자가 정해야 한다. **그 결정을 전부 여기 남긴다.**

`근거` 는 필수다. "가장 가까운 확정 디자인 표현을 따른다"(DC-009)를 지켰다는 증거가
근거 없이는 성립하지 않는다. **근거를 댈 수 없는 결정은 해석이고 DC-001 위반이다.**

| 화면 | 상태 | 근거 (어느 확정 디자인의 어느 표현) | 결정 |
|---|---|---|---|
""",
        encoding="utf-8",
    )
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="추출한 사실을 JSON 으로 출력")
    ap.add_argument("--write", action="store_true", help="대조표와 미정의 상태 파일 생성")
    ap.add_argument(
        "--only",
        metavar="NAME",
        help="그 화면 하나만 다시 쓴다 (예: Workbench). 다른 라운드의 리뷰 판정을 지키려면 필요하다",
    )
    args = ap.parse_args()

    data = collect()
    assert_baseline(data)

    if args.write:
        tables = write_tables(data, only=args.only)
        states = write_undefined_states()
        for p in tables:
            print(f"생성: {p.relative_to(ROOT)}")
        print(f"생성: {states.relative_to(ROOT)}")
        t = data["totals"]
        n = len(data["screens"])
        print(
            f"\n디자인 {n}종 — div {t['div']} / svg {t['svg']} / "
            f"radius {t['radius_occurrences']}회"
        )
        print("판정 칸은 비어 있다. 리뷰어가 채운다.")
        return

    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
