#!/usr/bin/env python3
"""확정 디자인에서 시각 언어 정본을 뽑는다 — 008 T003.

`docs/design/008-visual-language/*.dc.html` 의 `<style>` 블록이 정본의 유일한 출처다
(`specs/008-visual-language/contracts/visual-language.md` C-2).

## 왜 추출인가 — 판단이 아니라

007→008 의 방침은 **전사**였다: 사람이 dc.html 을 읽고 인라인 값을 컴포넌트에 옮겨
적는다. 그 방침이 결함이 됐다. 전사는 1회성이라 다음 개정에서 즉시 깨지고, 실제로
v1→v2 전환에서 기하는 옮겨졌으나 색과 구조는 v1 이 남았다 (spec V-01~V-08).

18장이 **글자 하나까지 같은** 시트를 공유하므로(research R1) 사람이 고를 것이 없다.
이 스크립트가 그 사실을 먼저 단언하고, 다르면 멈춘다.

## 하지 않는 것

**값을 변형하지 않는다.** 축약도 정리도 "더 나은" 반올림도 하지 않는다 — 그것이
002 라운드가 고친 결함이다(디자인에 `border-radius` 가 0회인데 `--radius: 10px` 를 두었다).

바꾸는 것은 **토큰 이름 하나뿐**이며 그것도 대응표에 적힌 것만이다. dc.html 은 축약형
(`--r`·`--sans`)을 쓰고 코드는 서술형(`--radius`·`--font-sans`)을 쓴다. 이름을 바꾸면
이미 옳게 쓰이는 참조가 함께 깨지는데, 대조 대상은 이름이 아니라 값이다.

    python3 scripts/extract_canon.py            # 정본 CSS 를 표준 출력으로
    python3 scripts/extract_canon.py --check    # 18장 동일 여부만 확인
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DESIGN = ROOT / "docs" / "design" / "008-visual-language"

# dc.html 축약 토큰명 → 코드의 서술 토큰명.
#
# **값은 건드리지 않는다.** 이 표는 이름만 옮긴다. 여기 없는 이름은 그대로 나간다.
RENAME = {
    "--surface": "--panel",
    "--r": "--radius",
    "--r-chip": "--radius-chip",
    "--r-lg": "--radius-lg",
    "--sans": "--font-sans",
    "--mono": "--font-mono",
}

STYLE = re.compile(r"<style>(.*?)</style>", re.S)


def sheets() -> dict[str, str]:
    """18장의 `<style>` 블록. 파일명 → 원문."""
    out: dict[str, str] = {}
    for path in sorted(DESIGN.glob("*.dc.html")):
        m = STYLE.search(path.read_text(encoding="utf-8"))
        if m is None:
            sys.exit(f"{path.name}: <style> 블록이 없다")
        out[path.name] = m.group(1)
    if not out:
        sys.exit(f"{DESIGN} 에 dc.html 이 없다")
    return out


def assert_identical(found: dict[str, str]) -> str:
    """18장이 같은 시트를 갖는지 단언하고 그 시트를 돌려준다.

    research R1 이 확인한 사실이며, 이 스크립트의 **전제**다. 하나라도 다르면 정본을
    기계적으로 뽑을 수 없고 사람이 어느 값을 고를지 정해야 한다 — 그 순간 전사로
    돌아간다. 그래서 다르면 진행하지 않고 멈춘다.
    """
    digests: dict[str, list[str]] = {}
    for name, text in found.items():
        digests.setdefault(hashlib.md5(text.encode()).hexdigest(), []).append(name)
    if len(digests) != 1:
        lines = ["확정 디자인 18장의 스타일 시트가 서로 다르다. 정본을 뽑을 수 없다.\n"]
        for digest, names in digests.items():
            lines.append(f"  {digest[:10]}  {' '.join(names)}")
        lines.append("\n디자인을 먼저 한 벌로 맞춰야 한다 (research R1).")
        sys.exit("\n".join(lines))
    return next(iter(found.values()))


def rename_tokens(css: str) -> str:
    """대응표에 있는 토큰 이름만 바꾼다. 선언부와 참조부 양쪽."""
    for old, new in RENAME.items():
        # `--r` 이 `--r-chip` 의 앞부분과 겹치므로 경계를 명시한다.
        css = re.sub(rf"(?<![\w-]){re.escape(old)}(?![\w-])", new, css)
    return css


def canon() -> str:
    return rename_tokens(assert_identical(sheets())).strip("\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="18장 동일 여부만 확인한다")
    args = ap.parse_args()

    found = sheets()
    if args.check:
        assert_identical(found)
        digest = hashlib.md5(next(iter(found.values())).encode()).hexdigest()[:10]
        print(f"확정 디자인 {len(found)}장이 같은 시트를 공유한다 — {digest}")
        return 0

    print(canon())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
