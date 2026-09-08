#!/usr/bin/env python3
"""L1 대조 — 정본 시트와 확정 디자인 시트를 **렌더해서** 잰다. 008 T006.

## 왜 렌더인가

002 가 세운 대조 축은 텍스트 통계였다 — `div 141개` · `#1A7F45 5회`. 그 축은 "행 결말
마커가 빠졌다"·"격자가 grid 에서 flex 로 바뀌었다"를 **원리적으로** 잡지 못한다
(spec V-10). 그리고 사람이 509칸을 채워야 해서 001·002 가 두 번 다 미완으로 남았다.

확정 디자인이 chromium 에서 정상 렌더된다는 것을 확인했으므로(research R2) 축을 바꿀 수
있다. 브라우저가 계산한 값을 비교하면 표기 차이(`#FFF` / `#ffffff` / `rgb(255,255,255)`)에
걸리지 않고, 사람이 채울 칸이 사라진다.

## 무엇을 비교하나

    기준  docs/design/008-visual-language/Language.dc.html 의 <style> 시트
    관측  frontend/src/theme/tokens.css

**같은 마크업**에 두 시트를 각각 적용해 형태 27종의 `getComputedStyle` 을 읽는다. 시트만
다르고 나머지는 같으므로 차이가 나면 그것은 시트의 차이다.

## 실행

    backend/.venv/bin/python scripts/design_render.py --json      # 사실만
    backend/.venv/bin/python scripts/design_render.py --compare   # 대조하고 보고서를 쓴다

`--compare` 는 불일치가 있으면 종료 코드 1 로 끝난다. 보고서는
`frontend/tests/l1-report.json` 에 쓰이고, 입력 두 개의 digest 를 함께 담는다 —
`frontend/tests/CanonMatchesDesign.test.ts` 가 그 digest 로 **보고서가 낡았는지** 판정한다.
낡은 보고서로 통과할 수 없다.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DESIGN = ROOT / "docs" / "design" / "008-visual-language"
TOKENS = ROOT / "frontend" / "src" / "theme" / "tokens.css"
REPORT = ROOT / "frontend" / "tests" / "l1-report.json"

# 확정 디자인이 정의한 재사용 형태 27종. 이름과 뜻은 디자인 그대로다 (C-4).
#
# `.body`·`.left` 는 부모의 flex 안에서만 의미를 갖는 배치 구획이므로 계산값 비교 대상이
# 아니다 — 여기 넣으면 부모 없는 렌더에서 둘 다 같은 값이 나와 대조가 무의미해진다.
FORMS = [
    "lbl", "mono", "pane", "why",
    "btn", "btn primary", "btn danger", "btn off", "btn sm",
    "chip", "chip pass", "chip fail", "chip warn", "chip run", "chip ai",
    "hdr", "phase", "notice", "steps", "steps-hd",
    "srow", "srow pass", "srow fail", "srow run", "srow sel",
]

# 재는 속성. `contracts/design-conformance.md` §3 의 목록이다.
PROPS = [
    "height", "min-height", "padding", "gap",
    "border-top-width", "border-right-width", "border-bottom-width", "border-left-width",
    "border-top-style", "border-left-style",
    "border-top-color", "border-right-color", "border-bottom-color", "border-left-color",
    "border-radius", "background-color", "color", "box-shadow",
    "font-family", "font-size", "font-weight", "letter-spacing", "text-transform",
    "display", "align-items",
]

STYLE = re.compile(r"<style>(.*?)</style>", re.S)


def design_sheet() -> str:
    m = STYLE.search((DESIGN / "Language.dc.html").read_text(encoding="utf-8"))
    if m is None:
        sys.exit("Language.dc.html 에 <style> 블록이 없다")
    return m.group(1)


def page(sheet: str) -> str:
    """두 시트에 **똑같이** 적용할 마크업. 형태마다 상자 하나."""
    boxes = "".join(
        f'<div class="{cls}" data-form="{cls}">텍스트 Ag 09</div>' for cls in FORMS
    )
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<style>{sheet}</style>"
        # 배치 영향을 없앤다 — 각 상자를 독립적으로 세운다. 시각 언어만 남긴다.
        "<style>body{margin:0}[data-form]{width:240px;margin:8px}</style>"
        f"</head><body>{boxes}</body></html>"
    )


def measure(pw, sheet: str) -> dict[str, dict[str, str]]:
    browser = pw.chromium.launch()
    pg = browser.new_page(viewport={"width": 1440, "height": 900})
    pg.set_content(page(sheet), wait_until="load")
    out = pg.evaluate(
        """(props) => {
            const r = {};
            for (const el of document.querySelectorAll('[data-form]')) {
                const cs = getComputedStyle(el);
                const one = {};
                for (const p of props) one[p] = cs.getPropertyValue(p).trim();
                r[el.dataset.form] = one;
            }
            return r;
        }""",
        PROPS,
    )
    browser.close()
    return out


def digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def run() -> dict:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit(
            "playwright 가 없다. backend/.venv/bin/python 으로 실행한다:\n"
            "  backend/.venv/bin/python scripts/design_render.py --compare"
        )

    design = design_sheet()
    canon = TOKENS.read_text(encoding="utf-8")
    with sync_playwright() as pw:
        expected = measure(pw, design)
        observed = measure(pw, canon)

    mismatches = []
    for form in FORMS:
        want, got = expected.get(form, {}), observed.get(form, {})
        for prop in PROPS:
            if want.get(prop) != got.get(prop):
                mismatches.append(
                    {"form": form, "prop": prop, "expected": want.get(prop), "observed": got.get(prop)}
                )

    return {
        "designDigest": digest(design),
        "canonDigest": digest(canon),
        "forms": len(FORMS),
        "props": len(PROPS),
        "compared": len(FORMS) * len(PROPS),
        "mismatches": mismatches,
        "expected": expected,
        "observed": observed,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--json", action="store_true", help="계산값을 그대로 낸다")
    ap.add_argument("--compare", action="store_true", help="대조하고 보고서를 쓴다")
    args = ap.parse_args()

    result = run()

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        json.dumps(
            {k: v for k, v in result.items() if k not in ("expected", "observed")},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    n = len(result["mismatches"])
    print(f"L1 대조 — 형태 {result['forms']} × 속성 {result['props']} = {result['compared']}칸")
    if n == 0:
        print("불일치 0건. 정본 시트가 확정 디자인 시트와 같다.")
        return 0
    print(f"불일치 {n}건:")
    for m in result["mismatches"][:40]:
        print(f"  .{m['form']} {m['prop']}: 기준 {m['expected']!r} ≠ 관측 {m['observed']!r}")
    if n > 40:
        print(f"  … 그 외 {n - 40}건")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
