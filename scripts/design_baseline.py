#!/usr/bin/env python3
"""확정 디자인 `docs/design/*.dc.html` 에서 대조 기준값을 기계적으로 추출한다.

DC-012 의 대조 기록은 "보고 비슷한가" 가 아니라 **확정 디자인에서 뽑은 값과의 대조**여야
한다. 이 스크립트는 그 기준값 칸만 채운다.

**판정하지 않는다.** `관측값`·`판정` 칸은 리뷰어 소유다
(contracts/design-conformance.md §4). 구현자가 자기 구현을 판정하면 대조가 아니라
자기 확인이 되고, 001 T156 이 정확히 그 이유로 미완으로 남아 있다.

    python3 scripts/design_baseline.py --json     # 사실만 JSON 으로
    python3 scripts/design_baseline.py --write    # 대조표 8개 + 미정의 상태 파일 생성

기준이 바뀌면(디자인 파일이 갱신되면) 다시 돌린다.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DESIGN = ROOT / "docs" / "design"
CANVAS = DESIGN / "canvas.json"
OUT_DIR = ROOT / "specs" / "002-defect-fix-design-conformance" / "design-conformance"

# 화면 식별자 → (dc.html 파일, 제품의 대응 파일). contracts/design-conformance.md §1
SCREENS: dict[str, tuple[str, str]] = {
    "TestList": ("TestList.dc.html", "frontend/src/pages/TestList.tsx"),
    "CreateTest": ("CreateTest.dc.html", "frontend/src/pages/CreateTest.tsx"),
    "AiRecord": ("AiRecord.dc.html", "frontend/src/pages/AiRecord.tsx"),
    "Main": ("Main.dc.html", "frontend/src/pages/Runner.tsx"),
    "RunnerPaused": ("RunnerPaused.dc.html", "frontend/src/pages/RunnerPaused.tsx"),
    "Takeover": ("Takeover.dc.html", "frontend/src/pages/Takeover.tsx"),
    "RunResult": ("RunResult.dc.html", "frontend/src/pages/RunResult.tsx"),
    "StepInspector": ("StepInspector.dc.html", "frontend/src/pages/StepInspector.tsx"),
    # 007 — 통합 작업 화면. 위 6종(TestList·CreateTest 제외)을 대체한다.
    # 이 항목의 대조 기록은 007 의 디렉터리로 나간다 (OUT_DIR_007) — 002 의 기록은
    # 그 라운드의 판정이므로 덮어쓰지 않는다.
    "Workbench": ("Workbench.dc.html", "frontend/src/components/workbench/Workbench.tsx"),
}

# 007 의 대조 기록 위치. `Workbench` 만 여기로 나간다.
OUT_DIR_007 = ROOT / "specs" / "007-unify-test-screens" / "design-conformance"
SCREENS_007 = {"Workbench"}


def out_dir_for(name: str) -> Path:
    """화면 식별자 → 대조 기록을 쓸 디렉터리.

    라운드마다 기록이 갈리는 이유는 판정이 그 라운드의 것이기 때문이다. 002 의
    `RunResult.md` 판정을 007 이 덮어쓰면 왜 그렇게 정했는지의 이력이 사라진다.
    """
    return OUT_DIR_007 if name in SCREENS_007 else OUT_DIR


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
    root = re.search(r"width:\s*(\d+)px;\s*min-height:\s*(\d+)px", text)

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
            if name in SCREENS_007:
                # 007 의 통합 화면 artboard 는 초안이 만들어지기 전까지 없다. 없는
                # 것을 오류로 세우면 002 의 8종 기준값 추출까지 함께 막힌다.
                continue
            sys.exit(f"확정 디자인 파일이 없습니다: {path}")
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
    """T004 — 기준이 바뀌면 즉시 드러나야 한다.

    `border-radius` 0회는 이 라운드 디자인 준수의 근거 중 하나다(DC-004). 확정 디자인이
    나중에 둥근 모서리를 도입하면 구현 쪽 회귀 가드(`DesignTokens.test.tsx`)가 거꾸로
    틀린 것이 된다. 그 순간을 조용히 지나치지 않도록 여기서 막는다.
    """
    radius = data["totals"]["radius_occurrences"]
    if radius != 0:
        sys.exit(
            f"기준이 바뀌었습니다: 확정 디자인에 'radius' 가 {radius}회 등장합니다. "
            "DC-004 와 frontend/tests/DesignTokens.test.tsx 를 함께 재검토하세요."
        )

    missing = [n for n, s in data["screens"].items() if not s["colors"]]
    if missing:
        sys.exit(f"색을 추출하지 못한 화면이 있습니다: {missing}. 추출 규칙을 확인하세요.")


# ─── 대조표 생성 ────────────────────────────────────────────────────────────

AXES_NOTE = """\
| 축 | 요구사항 |
|---|---|
| 구조 | DC-002 — 영역 분할·순서·계층 |
| 컴포넌트 | DC-003 — 종류·개수·배치 순서 |
| 치수 | DC-004 — 폭·높이·간격·여백·테두리 두께 |
| 타이포·색 | DC-005 — 글꼴 가족·크기·굵기·자간, 색 |
| 상태 | DC-006 — 선택·통과·실패·일시정지 등의 시각 표현 |
| 가감 | DC-007 — 없는 것을 더하지 않고, 있는 것을 빼지 않는다 |
"""


def _rows(name: str, s: dict[str, Any]) -> list[tuple[str, str, str]]:
    """(축, 항목, 기준값). 기준값은 전부 dc.html 에서 뽑은 것이다."""
    rows: list[tuple[str, str, str]] = [
        ("구조", "아트보드 기준 크기", f"{s['artboard_w']}×{s['artboard_h']}"),
        (
            "치수",
            "최상위 컨테이너",
            f"width {s['root_width']}px / min-height {s['root_min_height']}px"
            if s["root_width"]
            else "최상위에 명시적 치수 선언 없음 — 부모 아트보드 크기를 따른다",
        ),
        ("컴포넌트", "요소 총계 (div)", str(s["div_count"])),
        ("컴포넌트", "인라인 아이콘 (svg)", str(s["svg_count"])),
    ]

    for w, n in s["border_widths"][:4]:
        rows.append(("치수", f"테두리 두께 {w}", f"{n}회 등장"))

    if s["shadows"]:
        for v, n in s["shadows"][:4]:
            rows.append(("치수", "그림자", f"{v} ({n}회)"))
    else:
        rows.append(("치수", "그림자", "없음"))

    for c, n in s["colors"][:8]:
        rows.append(("타이포·색", f"색 {c}", f"{n}회 등장"))

    for f, n in s["fonts"][:3]:
        rows.append(("타이포·색", f"글꼴 {f}", f"{n}회 등장"))

    heights = [h for pair in s["fixed_heights"][:6] for h in pair[0] if h]
    for h in heights[:6]:
        rows.append(("치수", f"고정 높이 {h}px", "확정 디자인 선언값"))

    rows += [
        ("치수", "border-radius", "0회 — 모든 모서리 직각"),
        ("상태", "확정 디자인이 보여주는 상태", "리뷰어가 dc.html 을 열어 확인한다"),
        ("가감", "dc.html 에 없는 요소", "0개여야 한다"),
        ("가감", "dc.html 에 있는데 빠진 요소", "0개여야 한다"),
    ]
    return rows


def write_tables(data: dict[str, Any]) -> list[Path]:
    written: list[Path] = []

    for name, s in data["screens"].items():
        target_dir = out_dir_for(name)
        target_dir.mkdir(parents=True, exist_ok=True)
        rows = _rows(name, s)
        body = "\n".join(f"| {a} | {i} | {v} |  | 미판정 |  |" for a, i, v in rows)
        out = target_dir / f"{name}.md"
        out.write_text(
            f"""# 디자인 대조 — {name} ({s["title"]})

**기준**: `docs/design/{s["file"]}` — 아트보드 {s["artboard_w"]}×{s["artboard_h"]}
**대상**: `{s["target"]}`
**요구사항**: DC-002 ~ DC-007 · 완료 판정 SC-108

> **`기준값` 칸은 `scripts/design_baseline.py` 가 확정 디자인에서 기계적으로 뽑았다.**
> `관측값`·`판정`·`비고` 는 **리뷰어가 채운다.** 구현자가 자기 구현을 판정하면 대조가
> 아니라 자기 확인이 된다 (contracts/design-conformance.md §4).
>
> **완료 조건: `불일치`·`미판정` 이 0건.**

{AXES_NOTE}
## 대조표

| 축 | 항목 | 기준값 | 관측값 | 판정 | 비고 |
|---|---|---|---|---|---|
{body}

## 리뷰 방법

```bash
open docs/design/{s["file"]}    # 확정 디자인
# 제품의 같은 화면을 나란히 띄우고 위 항목을 하나씩 대조한다
```

판정은 `일치` / `불일치` / `미판정` 중 하나로 적는다. `불일치` 면 `비고` 에 차이를 적는다.
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
    ap.add_argument("--write", action="store_true", help="대조표 8개와 미정의 상태 파일 생성")
    args = ap.parse_args()

    data = collect()
    assert_baseline(data)

    if args.write:
        tables = write_tables(data)
        states = write_undefined_states()
        for p in tables:
            print(f"생성: {p.relative_to(ROOT)}")
        print(f"생성: {states.relative_to(ROOT)}")
        t = data["totals"]
        print(f"\n확정 디자인 8종 — div {t['div']} / svg {t['svg']} / radius {t['radius_occurrences']}회")
        print("판정 칸은 비어 있다. 리뷰어가 채운다 (T099).")
        return

    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
