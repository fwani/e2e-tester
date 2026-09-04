#!/usr/bin/env python3
"""수동 측정 기록 시트(CSV)를 SC-001·002·004·005·009 집계로 바꾼다 (T155).

    python3 scripts/mvp_metrics_report.py docs/measurement/recording-sheet.csv

기록 시트가 아직 비어 있으면 "미측정"을 그대로 보고한다. **빈칸을 0이나 실패로 세지 않는다** —
재지 않은 것과 재서 나쁜 것은 다르다. 그 둘을 섞으면 측정하지 않은 지표가 측정된 것처럼 보인다.

표준 출력은 `docs/mvp-metrics.md` §결과 에 붙일 수 있는 마크다운 표다.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

SCREEN_KINDS = {"목록", "폼", "모달", "새탭"}
DIFFICULTIES = {"단순클릭", "조건부UI", "hover메뉴"}
OPERATORS = {"숙련", "처음"}
BOOLS = {"yes", "no"}

# 판정에 쓰는 열과 그 허용값. 오타를 조용히 흘리면 분모가 틀어진다.
ENUM_COLUMNS = {
    "screen_kind": SCREEN_KINDS,
    "difficulty": DIFFICULTIES,
    "operator": OPERATORS,
    "code_edited": BOOLS,
    "completed": BOOLS,
    "nl_attempted": BOOLS,
    "nl_success": BOOLS,
    "takeover_attempted": BOOLS,
    "takeover_completed": BOOLS,
    "failure_diagnosed": BOOLS,
}

NUMERIC_COLUMNS = ("baseline_code_seconds", "build_seconds", "diagnose_seconds")


class SheetError(Exception):
    pass


def load(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        rows = [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(fh)]
    if not rows:
        raise SheetError("기록 시트에 행이 없다")
    return rows


def validate(rows: list[dict[str, str]]) -> list[str]:
    """치명적이지 않은 문제는 경고로 모아 돌려준다. 빈칸은 문제가 아니라 미측정이다."""
    problems: list[str] = []
    seen: set[str] = set()

    for row in rows:
        sid = row.get("scenario_id") or "(id 없음)"
        if sid in seen:
            problems.append(f"{sid}: scenario_id 가 중복이다")
        seen.add(sid)

        for column, allowed in ENUM_COLUMNS.items():
            value = row.get(column, "")
            if value and value not in allowed:
                problems.append(f"{sid}.{column}: '{value}' 는 허용값이 아니다 ({'/'.join(sorted(allowed))})")

        for column in NUMERIC_COLUMNS:
            value = row.get(column, "")
            if value:
                try:
                    if float(value) < 0:
                        problems.append(f"{sid}.{column}: 음수다")
                except ValueError:
                    problems.append(f"{sid}.{column}: '{value}' 는 숫자가 아니다")

        if row.get("nl_success") == "yes" and row.get("nl_attempted") == "no":
            problems.append(f"{sid}: 자연어를 시도하지 않았는데 성공으로 적혔다")
        if row.get("takeover_completed") == "yes" and row.get("takeover_attempted") == "no":
            problems.append(f"{sid}: Takeover 를 시도하지 않았는데 완료로 적혔다")
        if row.get("nl_success") == "no" and row.get("nl_attempted") == "yes" and not row.get("nl_failure_reason"):
            problems.append(f"{sid}: 자연어 변환 실패에 이유가 없다 (왜 실패했는지가 지표보다 쓸모 있다)")

    return problems


def composition(rows: list[dict[str, str]], column: str, expected: set[str]) -> list[str]:
    """표본이 한쪽으로 몰렸는지 본다. 쉬운 것만 고르면 지표가 아니라 표본을 재게 된다."""
    counts = {value: 0 for value in expected}
    for row in rows:
        value = row.get(column, "")
        if value in counts:
            counts[value] += 1
    missing = [k for k, v in counts.items() if v == 0]
    notes = [f"{column}: " + " · ".join(f"{k} {v}건" for k, v in counts.items())]
    if missing:
        notes.append(f"  ⚠ 표본에 없는 값: {', '.join(missing)}")
    return notes


def ratio(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "미측정"
    return f"{numerator / denominator * 100:.0f}% ({numerator}/{denominator})"


def numbers(rows: list[dict[str, str]], column: str) -> list[float]:
    """읽을 수 있는 값만 모은다. 잘못 적힌 값은 집계에서 빼고 validate 가 따로 보고한다 —
    집계에 섞으면 오타가 지표를 움직인다."""
    out: list[float] = []
    for row in rows:
        value = row.get(column, "")
        if not value:
            continue
        try:
            parsed = float(value)
        except ValueError:
            continue
        if parsed >= 0:
            out.append(parsed)
    return out


def report(rows: list[dict[str, str]]) -> str:
    lines: list[str] = []

    # SC-001 — 코드를 직접 수정하지 않고 작성을 완료한 비율 (목표 80%)
    judged = [r for r in rows if r.get("completed") in BOOLS and r.get("code_edited") in BOOLS]
    sc001_ok = sum(1 for r in judged if r["completed"] == "yes" and r["code_edited"] == "no")

    # SC-002 — 자연어 → 결정적 테스트 변환 성공률 (목표 70%)
    nl = [r for r in rows if r.get("nl_attempted") == "yes" and r.get("nl_success") in BOOLS]
    sc002_ok = sum(1 for r in nl if r["nl_success"] == "yes")

    # SC-004 — AI 실패분에 대한 Takeover 완료율 (목표 80%)
    to = [r for r in rows if r.get("takeover_attempted") == "yes" and r.get("takeover_completed") in BOOLS]
    sc004_ok = sum(1 for r in to if r["takeover_completed"] == "yes")

    # SC-005 — 코드 직접 작성 대비 작성 시간 단축률 (목표 50%)
    paired = [
        r for r in rows
        if numbers([r], "baseline_code_seconds") and numbers([r], "build_seconds")
    ]
    baseline_total = sum(numbers(paired, "baseline_code_seconds"))
    build_total = sum(numbers(paired, "build_seconds"))
    if paired and baseline_total > 0:
        sc005 = f"{(1 - build_total / baseline_total) * 100:.0f}% 단축 (표본 {len(paired)}건)"
    else:
        sc005 = "미측정"

    # SC-009 — 실패 원인을 1분 이내에 파악한 비율
    diag = [r for r in rows if r.get("failure_diagnosed") in BOOLS and numbers([r], "diagnose_seconds")]
    sc009_ok = sum(
        1 for r in diag
        if r["failure_diagnosed"] == "yes" and numbers([r], "diagnose_seconds")[0] <= 60
    )

    lines.append("| 지표 | 목표 | 측정값 | 표본 |")
    lines.append("|------|------|--------|------|")
    lines.append(f"| SC-001 | ≥ 80% | {ratio(sc001_ok, len(judged))} | 판정 가능한 시나리오 {len(judged)}건 |")
    lines.append(f"| SC-002 | ≥ 70% | {ratio(sc002_ok, len(nl))} | 자연어 시도 {len(nl)}건 |")
    lines.append(f"| SC-004 | ≥ 80% | {ratio(sc004_ok, len(to))} | Takeover 시도 {len(to)}건 |")
    lines.append(f"| SC-005 | ≥ 50% 단축 | {sc005} | 대조군 쌍 {len(paired)}건 |")
    lines.append(f"| SC-009 | 1분 이내 | {ratio(sc009_ok, len(diag))} | 실패 진단 {len(diag)}건 |")

    if nl:
        reasons: dict[str, int] = {}
        for r in nl:
            if r.get("nl_success") == "no":
                reasons[r.get("nl_failure_reason") or "(이유 없음)"] = (
                    reasons.get(r.get("nl_failure_reason") or "(이유 없음)", 0) + 1
                )
        if reasons:
            lines.append("")
            lines.append("**SC-002 변환 실패 사유**: " + " · ".join(f"{k} {v}건" for k, v in sorted(reasons.items())))

    return "\n".join(lines)


def main(argv: list[str]) -> int:
    path = Path(argv[1]) if len(argv) > 1 else Path("docs/measurement/recording-sheet.csv")
    if not path.exists():
        print(f"기록 시트를 찾을 수 없다: {path}", file=sys.stderr)
        return 1

    try:
        rows = load(path)
    except (SheetError, csv.Error) as exc:
        print(f"기록 시트를 읽을 수 없다: {exc}", file=sys.stderr)
        return 1

    print(f"# 수동 측정 집계 — {path} (시나리오 {len(rows)}건)")
    print()

    problems = validate(rows)
    if problems:
        print("## 기록 오류 — 집계 전에 고친다")
        print()
        for p in problems:
            print(f"- {p}")
        print()

    print("## 표본 구성")
    print()
    print("```")
    for column, expected in (("screen_kind", SCREEN_KINDS), ("difficulty", DIFFICULTIES), ("operator", OPERATORS)):
        for line in composition(rows, column, expected):
            print(line)
    print("```")
    print()

    print("## 결과")
    print()
    print(report(rows))
    print()
    print("측정값이 `미측정` 인 지표는 재지 않은 것이다. 목표 미달과 구분한다.")
    return 2 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
