#!/usr/bin/env python3
"""확정 디자인 `docs/design/*.dc.html` 의 마크업을 JSX 로 **기계적으로** 옮긴다. DC-001.

전사에서 가장 위험한 것은 사람이 옮기면서 값을 바꾸는 것이다 — 002 라운드의 원인이
정확히 그것이었다(`border-radius: 10px` 는 확정 디자인 어디에도 없다). 이 변환기는
인라인 `style` 의 **값을 건드리지 않는다.** 속성 이름만 JSX 규칙으로 바꾼다.

    python3 scripts/dc_to_jsx.py TestList > /tmp/TestList.jsx

**이 스크립트는 화면을 완성하지 않는다.** 정적 마크업만 낸다. 데이터에서 오는 문자열을
props 로 바꾸고 상호작용을 붙이는 일은 사람이 한다 — 무엇이 데이터이고 무엇이 확정
디자인의 고정 문구인지는 판단이 필요하고, 그 판단은 자동화할 수 없다.

옮기지 않는 것: `<helmet>` 안의 전역 스타일. 그것은 `frontend/src/theme/tokens.css`
가 담당한다.
"""

from __future__ import annotations

import argparse
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DESIGN = ROOT / "docs" / "design"

VOID = {"br", "img", "hr", "input", "meta", "link", "path", "circle", "rect", "line", "polyline", "polygon", "ellipse", "use", "stop"}

# JSX 에서 이름이 다른 속성. 값은 건드리지 않는다.
RENAME = {
    "class": "className",
    "for": "htmlFor",
    "tabindex": "tabIndex",
    "colspan": "colSpan",
    "rowspan": "rowSpan",
    "maxlength": "maxLength",
    "autofocus": "autoFocus",
    "readonly": "readOnly",
    "srcset": "srcSet",
    "viewbox": "viewBox",
    "xmlns:xlink": "xmlnsXlink",
    "xlink:href": "xlinkHref",
}


def _attr_name(name: str) -> str:
    if name in RENAME:
        return RENAME[name]
    # SVG 의 kebab-case 속성 → camelCase (stroke-width → strokeWidth)
    if "-" in name and not name.startswith("data-") and not name.startswith("aria-"):
        head, *rest = name.split("-")
        return head + "".join(p.capitalize() for p in rest)
    return name


def _style_object(css: str) -> str:
    """`style="a: 1; b: 2"` → `{{ a: "1", b: "2" }}`.

    **값을 그대로 문자열로 옮긴다.** 단위를 벗기거나 숫자로 바꾸지 않는다 — 그 순간
    확정 디자인의 값과 대조할 수 없게 된다.
    """
    parts: list[str] = []
    for chunk in css.split(";"):
        if ":" not in chunk:
            continue
        prop, _, value = chunk.partition(":")
        prop, value = prop.strip(), value.strip()
        if not prop or not value:
            continue
        head, *rest = prop.split("-")
        key = head + "".join(p.capitalize() for p in rest)
        if not key.isidentifier():
            key = f'"{prop}"'
        parts.append(f'{key}: "{value}"')
    return "{{ " + ", ".join(parts) + " }}"


class Converter(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.depth = 0
        self.skip = 0  # <helmet> 안은 건너뛴다

    def _pad(self) -> str:
        return "  " * self.depth

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "helmet":
            self.skip += 1
            return
        if self.skip:
            return

        rendered: list[str] = []
        for name, value in attrs:
            if value is None:
                rendered.append(_attr_name(name))
            elif name == "style":
                rendered.append(f"style={_style_object(value)}")
            else:
                escaped = value.replace('"', "&quot;")
                rendered.append(f'{_attr_name(name)}="{escaped}"')

        joined = (" " + " ".join(rendered)) if rendered else ""
        if tag in VOID:
            self.out.append(f"{self._pad()}<{tag}{joined} />")
        else:
            self.out.append(f"{self._pad()}<{tag}{joined}>")
            self.depth += 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in VOID and not self.skip:
            self.depth -= 1
            self.out[-1] = self.out[-1][:-1] + " />"

    def handle_endtag(self, tag: str) -> None:
        if tag == "helmet":
            self.skip = max(0, self.skip - 1)
            return
        if self.skip or tag in VOID:
            return
        self.depth = max(0, self.depth - 1)
        self.out.append(f"{self._pad()}</{tag}>")

    def handle_data(self, data: str) -> None:
        if self.skip:
            return
        text = data.strip()
        if not text:
            return
        # JSX 에서 중괄호는 식이 된다. 확정 디자인의 문자 그대로를 지킨다.
        if "{" in text or "}" in text:
            text = "{" + repr(text).replace("'", '"', 2) + "}"
        self.out.append(f"{self._pad()}{text}")


def convert(name: str) -> str:
    path = DESIGN / f"{name}.dc.html"
    if not path.exists():
        sys.exit(f"확정 디자인 파일이 없습니다: {path}")

    html = path.read_text(encoding="utf-8")
    body = re.search(r"<x-dc>(.*)</x-dc>", html, re.DOTALL)
    if body is None:
        sys.exit(f"<x-dc> 본문을 찾지 못했습니다: {path}")

    parser = Converter()
    parser.feed(body.group(1))
    return "\n".join(parser.out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("screen", help="화면 이름 (TestList, CreateTest, Main, …)")
    args = ap.parse_args()
    print(convert(args.screen))


if __name__ == "__main__":
    main()
