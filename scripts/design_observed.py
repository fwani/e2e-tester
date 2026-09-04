#!/usr/bin/env python3
"""대조표의 `관측값` 칸을 **구현 소스에서** 채운다. DC-012 · T049.

`design_baseline.py` 가 확정 디자인에서 기준값을 뽑았다면, 이쪽은 같은 항목을 제품
소스에서 뽑는다. 리뷰어가 두 값을 나란히 놓고 판정할 수 있게 하는 것이 목적이다.

**판정하지 않는다.** `판정` 칸은 비운 채로 둔다 — 구현자가 자기 구현을 판정하면 대조가
아니라 자기 확인이 된다 (contracts/design-conformance.md §4).

**이 스크립트가 보는 것은 소스 텍스트다.** 실제로 브라우저에 그려진 화면이 아니다.
그래서 "구조·컴포넌트 개수" 처럼 소스에서 셀 수 있는 것만 채우고, 눈으로 봐야 하는
것(상태 표현이 맞는지, 배치가 같은지)은 비운다. 리뷰어가 그쪽을 본다.

    python3 scripts/design_observed.py --write
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "specs" / "002-defect-fix-design-conformance" / "design-conformance"

# 화면 → 제품 소스. 공용 조각을 쓰는 화면은 함께 읽는다.
CHROME = "frontend/src/components/design/Chrome.tsx"
FRAME = "frontend/src/components/design/BrowserFrame.tsx"
STEPS = "frontend/src/components/design/DesignStepList.tsx"
# 확정 디자인의 `<helmet>` 전역 스타일에 해당한다. 기준값 추출기는 helmet 도 읽으므로
# 여기서도 함께 봐야 짝이 맞는다 (예: `a:hover` 의 #5A31B8).
TOKENS = "frontend/src/theme/tokens.css"

SOURCES: dict[str, list[str]] = {
    "TestList": [TOKENS, "frontend/src/pages/TestList.tsx", CHROME],
    "CreateTest": [TOKENS, "frontend/src/pages/CreateTest.tsx"],
    "AiRecord": [TOKENS, "frontend/src/pages/AiRecord.tsx", CHROME],
    "Main": [TOKENS, "frontend/src/pages/Runner.tsx", CHROME, FRAME, STEPS],
    "RunnerPaused": [TOKENS, "frontend/src/pages/RunnerPaused.tsx", CHROME, FRAME, STEPS],
    "Takeover": [TOKENS, "frontend/src/pages/Takeover.tsx", CHROME, FRAME, STEPS],
    "RunResult": [TOKENS, "frontend/src/pages/RunResult.tsx", CHROME],
    "StepInspector": [TOKENS, "frontend/src/pages/StepInspector.tsx", "frontend/src/components/LocatorPriorityTable.tsx"],
}


def _read(screen: str) -> str:
    parts = []
    for rel in SOURCES[screen]:
        path = ROOT / rel
        if not path.exists():
            sys.exit(f"구현 파일이 없습니다: {rel}")
        parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts)


def observe(screen: str, axis: str, item: str, expected: str) -> str:
    """항목 하나를 소스에서 관측한다. 소스로 볼 수 없으면 빈 칸."""
    src = _read(screen)
    # 주석의 설명 문구가 관측값을 만들어 내면 안 된다.
    code = re.sub(r"/\*[\s\S]*?\*/|//[^\n]*", "", src)

    if item.startswith("색 #"):
        color = item.removeprefix("색 ").lower()
        n = len(re.findall(re.escape(color), code, re.IGNORECASE))
        return f"{n}회 사용" if n else "쓰이지 않음"

    if item.startswith("테두리 두께 "):
        width = item.removeprefix("테두리 두께 ")
        n = len(re.findall(rf"border[A-Za-z]*:\s*\"{re.escape(width)} solid", code))
        return f"{n}회 사용" if n else "쓰이지 않음"

    if item == "border-radius":
        n = len(re.findall(r"borderRadius|border-radius", code))
        return "0회 — 모든 모서리 직각" if n == 0 else f"{n}회 — 위반"

    if item == "인라인 아이콘 (svg)":
        return f"{len(re.findall(r'<svg', code))}"

    if item.startswith("글꼴 "):
        family = item.removeprefix("글꼴 ").strip("'")
        n = len(re.findall(re.escape(family), code))
        return f"{n}회 사용" if n else "쓰이지 않음"

    if item == "그림자":
        shadow = expected.split(" (")[0]
        n = len(re.findall(re.escape(shadow), code))
        return f"{n}회 사용" if n else "쓰이지 않음"

    if item.startswith("고정 높이 "):
        px = item.removeprefix("고정 높이 ").removesuffix("px")
        n = len(re.findall(rf"(?:minHeight|height|flex):\s*\"(?:0 0 )?{px}px", code))
        return f"{n}회 사용" if n else "쓰이지 않음"

    if item == "최상위 컨테이너":
        m = re.search(r"<Artboard\s+width=\{(\d+)\}\s+(minHeight|height)=\{(\d+)\}", code)
        if m:
            return f"Artboard width {m.group(1)}px / {m.group(2)} {m.group(3)}px"
        m = re.search(r'width:\s*"(\d+)px",\s*minHeight:\s*"(\d+)px"', code)
        return f"width {m.group(1)}px / min-height {m.group(2)}px" if m else ""

    # 요소 총계·구조·상태·가감은 렌더된 화면을 봐야 한다. 리뷰어 몫으로 비운다.
    return ""


ROW = re.compile(r"^\| ([^|]+) \| ([^|]+) \| ([^|]+) \|([^|]*)\| ([^|]+) \|([^|]*)\|$")


def fill(screen: str) -> tuple[int, int]:
    path = OUT_DIR / f"{screen}.md"
    if not path.exists():
        sys.exit(f"대조표가 없습니다: {path}. 먼저 design_baseline.py --write 를 돌리세요.")

    filled = total = 0
    out: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = ROW.match(line)
        if m is None or m.group(1).strip() in {"축", "---"}:
            out.append(line)
            continue
        axis, item, expected = (g.strip() for g in m.groups()[:3])
        verdict, note = m.group(5).strip(), m.group(6)
        total += 1
        observed = observe(screen, axis, item, expected)
        if observed:
            filled += 1
        out.append(f"| {axis} | {item} | {expected} | {observed} | {verdict} |{note}|")

    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return filled, total


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--write", action="store_true", help="대조표의 관측값 칸을 채운다")
    args = ap.parse_args()
    if not args.write:
        print(__doc__)
        return

    grand_filled = grand_total = 0
    for screen in SOURCES:
        filled, total = fill(screen)
        grand_filled += filled
        grand_total += total
        print(f"{screen}: 관측값 {filled}/{total}")

    print(f"\n합계 {grand_filled}/{grand_total} 항목을 소스에서 관측했다.")
    print("나머지는 렌더된 화면을 봐야 하는 항목이다 — 리뷰어가 채운다.")
    print("판정 칸은 전부 비어 있다 (T099).")


if __name__ == "__main__":
    main()
