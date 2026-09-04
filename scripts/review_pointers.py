#!/usr/bin/env python3
"""design-review.md 의 각 CHK 항목이 가리키는 근거 위치를 실제 `파일:라인` 으로 해석한다.

리뷰어가 항목마다 문서를 뒤지지 않고 바로 근거를 열 수 있게 하는 보조 도구다.
**판정은 하지 않는다.** `[x]` 표시는 리뷰어 소유다 (design-review.md §Review Ownership).

    python3 scripts/review_pointers.py > docs/review/design-review-pointers.md

라인 번호는 실행 시점 기준이다. 문서가 바뀌면 다시 돌린다.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FEATURE = ROOT / "specs" / "001-interactive-ai-test-builder"
CHECKLIST = FEATURE / "checklists" / "design-review.md"

# 체크리스트가 쓰는 문서 이름 → 실제 파일
DOCS = {
    "spec": FEATURE / "spec.md",
    "plan": FEATURE / "plan.md",
    "research": FEATURE / "research.md",
    "data-model": FEATURE / "data-model.md",
    "quickstart": FEATURE / "quickstart.md",
    "contracts": FEATURE / "contracts",
    "checklists": FEATURE / "checklists",
    "tasks": FEATURE / "tasks.md",
}

# 체크리스트가 쓴 절 이름과 문서의 실제 제목이 다른 경우 — 이름이 바뀐 것을 리뷰어가
# 다시 찾아 헤매지 않게 여기에 적는다. 불일치 자체는 체크리스트 갱신 대상이다.
ALIASES = {
    ("spec", "디자인 차이 1"): "디자인과의 차이 (1)",
    ("spec", "디자인 차이 2"): "디자인과의 차이 (2)",
    ("spec", "디자인 차이 3"): "디자인과의 차이 (3)",
}

ITEM_RE = re.compile(r"^- \[( |x|X)\] (CHK\d+) (.*)$")
TAIL_RE = re.compile(r"\[([^\[\]]*)\]\s*$")
REQ_RE = re.compile(r"^(FR|SC)-[0-9a-z-]+$")

# 근거를 문서로 해석할 수 없는 품질 차원 이름 — 참조가 아니라 검토 관점이다
DIMENSIONS = {
    "Completeness", "Clarity", "Consistency", "Coverage", "Traceability",
    "Measurability", "Ambiguity", "Gap", "Edge Case", "Assumption",
    "Dependency", "Duplication", "Conflict",
}


def read(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def find_line(path: Path, patterns: list[re.Pattern[str]]) -> int | None:
    """패턴을 순서대로 시도해 처음 맞는 라인 번호(1-base)를 준다."""
    lines = read(path)
    for pattern in patterns:
        for idx, line in enumerate(lines, start=1):
            if pattern.search(line):
                return idx
    return None


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def resolve(doc: str, anchor: str) -> str:
    """`doc §anchor` 를 `파일:라인` 문자열로 바꾼다. 못 찾으면 이유를 붙인다."""
    target = DOCS.get(doc)
    if target is None:
        return f"(문서 미상: {doc})"

    anchor = ALIASES.get((doc, anchor), anchor)

    # 범위 표기(R1~R8, FR-030a~g, SC-001~SC-005)는 첫 항목으로 해석한다
    head = re.split(r"[~–]", anchor)[0].strip()

    if doc == "contracts":
        # §rest-api · §step-dsl · §websocket · §README
        name = head.lstrip("§").strip()
        candidate = target / f"{name}.md"
        if candidate.exists():
            return f"{rel(candidate)}:1"
        return f"{rel(target)}/ (절 미상: {anchor})"

    if doc == "checklists":
        name = head.split()[0] if head.split() else head
        candidate = target / name
        if candidate.exists():
            return f"{rel(candidate)}:1"
        return f"{rel(target)}/ ({anchor})"

    if not target.exists():
        return f"(파일 없음: {doc})"

    patterns: list[re.Pattern[str]] = []
    if REQ_RE.match(head):
        # 요구사항 id — spec.md 의 굵은 표기가 정의 지점이다
        patterns.append(re.compile(rf"^- \*\*{re.escape(head)}\*\*"))
        patterns.append(re.compile(rf"\*\*{re.escape(head)}\*\*"))
    elif doc == "research" and re.fullmatch(r"R\d+", head):
        patterns.append(re.compile(rf"^## {re.escape(head)}\."))
    elif doc == "data-model" and re.fullmatch(r"\d+", head):
        patterns.append(re.compile(rf"^## {re.escape(head)}\."))
    elif doc == "quickstart" and re.fullmatch(r"\d+", head):
        patterns.append(re.compile(rf"^## {re.escape(head)}\."))
    else:
        # 절 제목 — 제목 줄 우선, 없으면 본문 첫 등장
        escaped = re.escape(head)
        patterns.append(re.compile(rf"^#{{1,4}} .*{escaped}", re.IGNORECASE))
        patterns.append(re.compile(escaped, re.IGNORECASE))

    line = find_line(target, patterns)
    if line is None:
        return f"{rel(target)} (앵커 미해결: {anchor})"
    return f"{rel(target)}:{line}"


def parse_refs(tail: str) -> tuple[list[str], list[str]]:
    """`[Completeness, Spec §FR-010]` 의 꼬리를 (품질 차원, 해석된 근거) 로 나눈다."""
    dims: list[str] = []
    refs: list[str] = []
    current_doc: str | None = None

    # `Spec §FR-044 vs Plan §Constitution Check` 처럼 대조 형태로 쓰인 참조는 양쪽 다 근거다
    tail = re.sub(r"\s+vs\.?\s+", ", ", tail)

    for token in (t.strip() for t in tail.split(",")):
        if not token:
            continue
        if token in DIMENSIONS:
            dims.append(token)
            continue
        if token.startswith("§"):
            if current_doc is None:
                refs.append(f"(문서 미지정: {token})")
            else:
                refs.append(resolve(current_doc, token[1:].strip()))
            continue
        # `Spec §FR-010` 처럼 문서 이름과 앵커가 붙어 오는 경우
        parts = token.split("§", 1)
        doc_name = parts[0].strip().lower()
        if doc_name in DOCS:
            current_doc = doc_name
            if len(parts) == 2 and parts[1].strip():
                refs.append(resolve(current_doc, parts[1].strip()))
            else:
                refs.append(f"{rel(DOCS[current_doc])} (문서 전체)")
        else:
            dims.append(token)
    return dims, refs


def main() -> int:
    if not CHECKLIST.exists():
        print(f"체크리스트를 찾을 수 없다: {CHECKLIST}", file=sys.stderr)
        return 1

    section = "(제목 없음)"
    out: list[str] = []
    out.append("# design-review 근거 위치표 (T156 리뷰어 보조)")
    out.append("")
    out.append(
        "`scripts/review_pointers.py` 가 "
        "`specs/001-interactive-ai-test-builder/checklists/design-review.md` 에서 생성했다. "
        "**판정은 들어 있지 않다** — 각 항목이 가리키는 근거가 어느 파일 몇 번째 줄에 있는지만 해석한다."
    )
    out.append("")
    out.append("라인 번호는 생성 시점 기준이다. 문서가 바뀌면 다시 생성한다:")
    out.append("")
    out.append("```bash")
    out.append("python3 scripts/review_pointers.py > docs/review/design-review-pointers.md")
    out.append("```")
    out.append("")

    total = 0
    unresolved = 0
    for raw in read(CHECKLIST):
        if raw.startswith("## "):
            section = raw[3:].strip()
            out.append("")
            out.append(f"## {section}")
            out.append("")
            out.append("| 항목 | 검토 관점 | 근거 위치 | 판정 |")
            out.append("|---|---|---|---|")
            continue
        m = ITEM_RE.match(raw)
        if not m:
            continue
        total += 1
        _, chk, body = m.groups()
        tail = TAIL_RE.search(body)
        dims, refs = parse_refs(tail.group(1)) if tail else ([], [])
        if not refs:
            refs = ["(문서 참조 없음 — 전체를 대상으로 판단하는 항목)"]
        for r in refs:
            if "미해결" in r or "미상" in r or "없음:" in r:
                unresolved += 1
        out.append(
            f"| {chk} | {' · '.join(dims) or '—'} "
            f"| {'<br>'.join(f'`{r}`' for r in refs)} |  |"
        )

    out.append("")
    out.append(
        f"**항목 {total}건 · 앵커 미해결 {unresolved}건.** "
        "미해결은 체크리스트가 가리키는 절이 문서에 없거나 이름이 바뀐 것이므로, "
        "그 자체가 검토 대상이다."
    )
    out.append("")
    print("\n".join(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
