"""프로젝트·테스트 → 묶음, 그리고 내보내기 검토 요약 (기능 019 · US1·US4).

**프로젝트의 어떤 파일도 바꾸지 않는다** (FR-008). 읽기만 한다.

**묶음은 메모리에서 완성된 뒤에야 바이트가 된다** (FR-024 와 같은 성질). 실패는 언제나
"파일이 없다" 이지 "파일이 이상하다" 가 아니다 — 014 의 `export_project` 가 같은 판단이다.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

import yaml

from itb.domain.test_case import (
    VARIABLE_REFERENCE_PATTERN,
    VARIABLE_VALUE_FIELDS,
    Project,
    Test,
    step_field_text,
)
from itb.sharing.bundle import (
    BundleProject,
    RequiredValue,
    ShareBundle,
    collect_required_values,
)
from itb.sharing.limits import BUNDLE_VERSION, MAX_PLAINTEXT_PREVIEW_CHARS

BUNDLE_NOTICE = """\
# 이 파일에는 비밀번호·API 키 등 민감 값이 들어 있지 않습니다.
# 가져온 뒤 필요한 값은 받는 분이 직접 입력합니다. (required_values 참고)
"""
"""파일 머리의 안내.

**파일을 열어 본 사람이 가장 먼저 읽을 것**이다. 묶음을 받은 사람은 대개 "이거 열어 봐도
되나" 부터 생각하고, 그 답이 파일 안에 있어야 한다. 형식을 YAML 로 고른 이유 하나가
이 주석을 넣을 수 있다는 것이었다 (research R1).
"""


def _group_prefix(test_id: str) -> str:
    """식별자에서 그룹 접두어를 읽는다. 접두어가 곧 소속이다 (013 data-model §3)."""
    return test_id.split("-", 1)[0]


def build_bundle(
    project: Project,
    tests: list[Test],
    *,
    generator: str = "itb",
    whole_project: bool = True,
    created_at: dt.datetime | None = None,
) -> ShareBundle:
    """묶음을 만든다. 프로젝트를 읽기만 한다 (FR-008).

    ``whole_project`` 가 거짓이면 **실제로 쓰이는 접두어의 그룹만** 싣는다. 고른 테스트만
    내보내면서 빈 그룹을 함께 옮기면 받는 쪽에 테스트 없는 그룹이 생긴다 (data-model §2.2).

    각 테스트의 ``imported_from`` 을 비운다 — 전달이 이어질 때 앞 사람의 가져오기 기록과
    파일 이름이 따라가고, 그 이름이 사내 경로를 흘릴 수 있다 (research R9).
    """
    used = {_group_prefix(t.id) for t in tests}
    groups = [
        g for g in project.groups if whole_project or g.prefix in used
    ]

    return ShareBundle(
        bundle_version=BUNDLE_VERSION,
        generator=generator,
        created_at=created_at or dt.datetime.now(dt.UTC),
        project=BundleProject(
            name=project.name,
            default_start_url=project.default_start_url,
            browser=project.browser,
            test_id_attribute=project.test_id_attribute,
            max_tabs=project.max_tabs,
            groups=groups,
        ),
        required_values=collect_required_values(tests),
        tests=[t.model_copy(update={"imported_from": None}) for t in tests],
    )


def dump_bundle(bundle: ShareBundle) -> bytes:
    """묶음을 파일 바이트로 만든다.

    ``sort_keys=False`` 로 매니페스트의 키 순서를 모델 정의 순서에 맞춘다 — 경고가 맨 위,
    그다음이 형식 버전이다. 알파벳순으로 정렬하면 `bundle_version` 이 `created_at` 뒤로
    가고, 파일을 열어 본 사람이 가장 먼저 보는 것이 만든 시각이 된다.

    ``allow_unicode=True`` 는 한글을 이스케이프하지 않는다. **열어 볼 수 있다는 것이
    이 형식을 고른 근거**이므로(research R1), `\\uD55C\\uAE00` 로 나가면 근거가 사라진다.
    """
    body = yaml.safe_dump(
        bundle.model_dump(mode="json"),
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=100,
    )
    return (BUNDLE_NOTICE + body).encode("utf-8")


# ─── 내보내기 검토 (US4 · FR-006) ───────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class StartUrl:
    scope: str
    """``"project"`` 또는 ``"test"``."""

    test_id: str | None
    url: str


@dataclass(frozen=True, slots=True)
class PlaintextValue:
    """묶음에 **그대로 들어갈** 평문 입력값 하나.

    가리지 않는다. 이 목록의 목적이 값을 보여 주는 것이고, 가려 놓으면 사번이나 사내 계정이
    섞여 있어도 발견할 수 없다 (research R11).
    """

    test_id: str
    step_id: str
    step_label: str | None
    field: str
    value: str
    truncated: bool


@dataclass(frozen=True, slots=True)
class ExportReview:
    """파일을 만들기 전에 보여 주는 것 (FR-006)."""

    project_name: str
    test_count: int
    group_count: int
    start_urls: list[StartUrl] = field(default_factory=list)
    plaintext_values: list[PlaintextValue] = field(default_factory=list)
    required_values: list[RequiredValue] = field(default_factory=list)
    unreadable: list[str] = field(default_factory=list)


def _plaintext_values(tests: list[Test]) -> list[PlaintextValue]:
    """값을 가진 자리 중 **변수 참조가 아닌 것**을 모은다.

    ``{{VAR}}`` 는 값이 아니라 자리표시자이므로 제외한다. 참조가 섞인 문자열
    (``https://x/{{ID}}/detail``)은 남는 평문 부분이 있으므로 포함한다 — 그 부분이
    사내 주소일 수 있다.
    """
    out: list[PlaintextValue] = []
    for test in tests:
        for step in test.steps:
            for name in VARIABLE_VALUE_FIELDS:
                text = step_field_text(step, name)
                if not text:
                    continue
                if VARIABLE_REFERENCE_PATTERN.fullmatch(text.strip()):
                    continue
                shown = text[:MAX_PLAINTEXT_PREVIEW_CHARS]
                out.append(
                    PlaintextValue(
                        test_id=test.id,
                        step_id=step.id,
                        step_label=step.label,
                        field=name,
                        value=shown,
                        truncated=len(text) > len(shown),
                    )
                )
    return out


def review_export(
    project: Project,
    tests: list[Test],
    *,
    unreadable: list[str] | None = None,
    whole_project: bool = True,
) -> ExportReview:
    """무엇이 나가는지 요약한다. **파일을 만들지 않는다** (FR-006).

    ``unreadable`` 은 정의를 읽을 수 없어 빠지는 테스트다. **내보내기를 막지 않는다** —
    깨진 파일 하나 때문에 아무것도 못 하게 되면 사용자는 그것을 고치기 전까지 갇힌다
    (014 의 `_collect` 와 같은 판단, research R11).
    """
    used = {_group_prefix(t.id) for t in tests}
    groups = [g for g in project.groups if whole_project or g.prefix in used]

    urls = [StartUrl(scope="project", test_id=None, url=project.default_start_url)]
    urls += [
        StartUrl(scope="test", test_id=t.id, url=t.start_url)
        for t in tests
        if t.start_url != project.default_start_url
    ]

    return ExportReview(
        project_name=project.name,
        test_count=len(tests),
        group_count=len(groups),
        start_urls=urls,
        plaintext_values=_plaintext_values(tests),
        required_values=collect_required_values(tests),
        unreadable=list(unreadable or []),
    )
