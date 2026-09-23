"""바이트 → 묶음 (기능 019 · data-model §6).

검증이 **다섯 겹**이고 앞의 겹을 통과하지 못하면 뒤를 시도하지 않는다.

1. **바이트** — 상한 초과면 읽지 않는다
2. **YAML** — 별칭 금지 로더로 파싱, 최상위가 매핑인지
3. **묶음 모델** — `ShareBundle` 검증, 형식 버전
4. **선언 보충** — 참조는 있는데 선언이 없는 변수를 채운다 (FR-047)
5. **도메인** — 각 `Test` 를 `Test` 모델로 검증

**4번이 5번 앞에 있다.** `Test._check_refs` 가 선언 없는 참조를 거부하므로, 보충하지 않고
검증에 넘기면 손으로 편집된 묶음이 통째로 거부되고 사용자는 "무엇을 고쳐야 하는지" 대신
"읽을 수 없다" 만 받는다. 보충은 **없는 값을 지어내는 것이 아니라 빈 자리를 드러내는
것**이며, 민감 변수라면 채우기 전까지 실행이 막힌다.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import yaml
from pydantic import ValidationError

from itb.domain.test_case import (
    DSL_VERSION,
    SENSITIVE_VARIABLE_PREFIX,
    Test,
    Variable,
    referenced_variable_names,
)
from itb.sharing.bundle import RequiredValue, ShareBundle, collect_required_values
from itb.sharing.limits import (
    BUNDLE_VERSION,
    MAX_BUNDLE_BYTES,
    MAX_BUNDLE_GROUPS,
    MAX_BUNDLE_TESTS,
)


class BundleError(Exception):
    """묶음을 읽을 수 없다. 사유를 그대로 사용자에게 보여 줄 수 있어야 한다."""


class BundleTooLargeError(BundleError):
    """상한 초과. ``kind`` 가 무엇의 상한인지 말한다."""

    def __init__(self, message: str, kind: str) -> None:
        super().__init__(message)
        self.kind = kind


class BundleMalformedError(BundleError):
    """해석할 수 없다 — 파싱 실패, 최상위 형식 오류, **YAML 별칭 사용**."""


class BundleVersionError(BundleError):
    """읽을 수 없는 형식 버전. **부분 복원을 시도하지 않는다.**"""


class InvalidTestError(BundleError):
    """테스트 정의가 도메인 검증에 실패했다. 문제를 **전부 모아** 나른다."""

    def __init__(self, problems: list[str]) -> None:
        super().__init__("묶음 안 테스트 정의를 읽을 수 없습니다.")
        self.problems = problems


class _NoAliasLoader(yaml.SafeLoader):
    """앵커/별칭을 거부하는 로더 (research R4).

    `safe_load` 는 임의 객체 생성은 막지만 **별칭 폭탄**(billion laughs)은 막지 못한다 —
    수백 바이트짜리 문서가 전개되면서 수 GB 가 될 수 있다. 이 파일은 사람이 보낸 외부
    입력이고, 헌법은 모든 외부 입력을 경계에서 검증할 것을 요구한다.

    **정상적인 묶음은 별칭을 쓰지 않는다.** 우리가 만드는 파일은
    `yaml.safe_dump(default_flow_style=False)` 로 나오므로 잃는 것이 없다.

    ``compose_node`` 에서 막는 이유는 **전개되기 전**이기 때문이다. 전개된 뒤에 재면 재지
    않은 것과 같다.
    """

    def compose_node(self, parent: object, index: object) -> object:
        if self.check_event(yaml.AliasEvent):
            event = self.peek_event()
            msg = (
                "묶음에 YAML 별칭(*alias)이 있습니다. 이 도구가 만든 파일이 아닙니다. "
                f"(줄 {event.start_mark.line + 1})"
            )
            raise BundleMalformedError(msg)
        return super().compose_node(parent, index)  # type: ignore[arg-type]


@dataclass(slots=True)
class RepairedVariable:
    """선언이 없어 보충한 변수 (FR-047)."""

    test_id: str
    name: str
    sensitive: bool


@dataclass(slots=True)
class ReadBundle:
    """읽어 낸 묶음과, 읽는 동안 일어난 일.

    `bundle` 만 돌려주면 **무엇을 보충했는지** 사라진다. 조용히 고치면 사용자는 파일이
    온전했다고 믿는다.
    """

    bundle: ShareBundle
    repaired: list[RepairedVariable] = field(default_factory=list)

    @property
    def tests(self) -> list[Test]:
        return self.bundle.tests

    @property
    def project(self) -> object:
        return self.bundle.project

    @property
    def bundle_version(self) -> int:
        return self.bundle.bundle_version

    @property
    def required_values(self) -> list[RequiredValue]:
        return self.bundle.required_values


def _parse(data: bytes) -> dict[str, object]:
    """1겹·2겹 — 바이트 상한과 YAML."""
    if len(data) > MAX_BUNDLE_BYTES:
        msg = (
            f"묶음 파일이 상한({MAX_BUNDLE_BYTES // (1024 * 1024)}MB)을 넘습니다. "
            "테스트를 나눠서 여러 번에 걸쳐 공유하세요."
        )
        raise BundleTooLargeError(msg, "bytes")

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        msg = "묶음 파일이 UTF-8 텍스트가 아닙니다. 전송 중 손상됐을 수 있습니다."
        raise BundleMalformedError(msg) from exc

    try:
        raw = yaml.load(text, Loader=_NoAliasLoader)  # noqa: S506 — 별칭까지 막은 SafeLoader 파생
    except BundleMalformedError:
        raise
    except yaml.YAMLError as exc:
        msg = f"묶음 파일을 해석할 수 없습니다: {exc}"
        raise BundleMalformedError(msg) from exc

    if not isinstance(raw, dict):
        msg = "묶음 파일의 최상위가 매핑이 아닙니다. 이 도구가 만든 파일이 아닙니다."
        raise BundleMalformedError(msg)
    return raw


def _check_version(raw: dict[str, object]) -> None:
    """3겹의 앞부분 — 형식 버전.

    **모델 검증보다 먼저 본다.** 버전이 다르면 필드 구성도 다를 수 있고, 그때 나오는
    "surprise 는 허용되지 않는 필드입니다" 는 사용자에게 아무것도 알려 주지 않는다.
    """
    version = raw.get("bundle_version")
    if version == BUNDLE_VERSION:
        return
    if isinstance(version, int) and version > BUNDLE_VERSION:
        msg = (
            f"이 묶음은 더 새로운 형식입니다 (버전 {version}, 이 도구는 {BUNDLE_VERSION}). "
            "도구를 최신 버전으로 올린 뒤 다시 시도하세요."
        )
    else:
        msg = (
            f"읽을 수 없는 묶음 형식입니다 (버전 {version!r}). "
            f"이 도구는 버전 {BUNDLE_VERSION} 만 읽습니다."
        )
    raise BundleVersionError(msg)


def _check_size(raw: dict[str, object]) -> None:
    """건수 상한. 바이트를 통과해도 대상 프로젝트가 수용하지 못할 수 있다."""
    tests = raw.get("tests")
    if isinstance(tests, list) and len(tests) > MAX_BUNDLE_TESTS:
        msg = f"묶음에 담긴 테스트가 너무 많습니다 ({len(tests)} > {MAX_BUNDLE_TESTS})."
        raise BundleTooLargeError(msg, "tests")

    project = raw.get("project")
    groups = project.get("groups") if isinstance(project, dict) else None
    if isinstance(groups, list) and len(groups) > MAX_BUNDLE_GROUPS:
        msg = f"묶음에 담긴 그룹이 너무 많습니다 ({len(groups)} > {MAX_BUNDLE_GROUPS})."
        raise BundleTooLargeError(msg, "groups")


def _repair_variables(raw_tests: list[object]) -> list[RepairedVariable]:
    """4겹 — 참조는 있는데 선언이 없는 변수를 채운다 (FR-047).

    ``raw_tests`` 를 **제자리에서** 고친다. 모델로 만든 뒤에는 고칠 수 없다 —
    `Test._check_refs` 가 그 전에 거부하기 때문이다.

    판정 근거는 이름뿐이다. 다른 근거가 파일에 남아 있지 않다.
    """
    repaired: list[RepairedVariable] = []

    for entry in raw_tests:
        if not isinstance(entry, dict):
            continue
        steps = entry.get("steps")
        if not isinstance(steps, list):
            continue

        declared = {
            v.get("name")
            for v in (entry.get("variables") or [])
            if isinstance(v, dict)
        }
        referenced = referenced_variable_names(
            [_LooseStep(s) for s in steps if isinstance(s, dict)]  # type: ignore[arg-type]
        )

        missing = sorted(referenced - declared)
        if not missing:
            continue

        variables = list(entry.get("variables") or [])
        test_id = str(entry.get("id", "?"))
        for name in missing:
            sensitive = name.startswith(SENSITIVE_VARIABLE_PREFIX)
            variables.append(
                {"name": name, "value": None if sensitive else "", "sensitive": sensitive}
            )
            repaired.append(RepairedVariable(test_id=test_id, name=name, sensitive=sensitive))
        entry["variables"] = variables

    return repaired


class _LooseStep:
    """아직 모델이 아닌 스텝에서 값 자리를 읽기 위한 얇은 감싸개.

    :func:`itb.domain.test_case.referenced_variable_names` 는 `getattr` 로 자리를 읽으므로,
    사전을 속성처럼 보이게 하면 **같은 자리 목록**(`VARIABLE_VALUE_FIELDS`)을 그대로 쓸 수
    있다. 자리 목록을 여기 베끼지 않으려는 것이다 (research R7).
    """

    __slots__ = ("_raw",)

    def __init__(self, raw: dict[str, object]) -> None:
        self._raw = raw

    def __getattr__(self, name: str) -> object:
        value = self._raw.get(name)
        return _LooseStep(value) if isinstance(value, dict) else value


def read_bundle(data: bytes) -> ReadBundle:
    """묶음 바이트를 읽는다. 다섯 겹을 순서대로 통과시킨다 (data-model §6)."""
    raw = _parse(data)
    _check_version(raw)
    _check_size(raw)

    raw_tests = raw.get("tests")
    repaired = _repair_variables(raw_tests) if isinstance(raw_tests, list) else []

    try:
        bundle = ShareBundle.model_validate(raw)
    except ValidationError as exc:
        problems = _test_problems(exc, raw_tests if isinstance(raw_tests, list) else [])
        if problems:
            raise InvalidTestError(problems) from exc
        msg = f"묶음 파일의 모양이 올바르지 않습니다: {_first_reason(exc)}"
        raise BundleMalformedError(msg) from exc

    _check_dsl_versions(bundle)

    # 매니페스트의 요약을 **믿지 않는다.** 파일이 손으로 편집될 수 있으므로 정의에서
    # 다시 계산하고, 보충한 것은 `declared=False` 로 표시한다 (research R7).
    repaired_names = {(r.test_id, r.name) for r in repaired}
    recomputed = collect_required_values(bundle.tests)
    bundle.required_values = [
        value.model_copy(
            update={
                "declared": not any(
                    (u.test_id, value.name) in repaired_names for u in value.usages
                )
            }
        )
        for value in recomputed
    ]

    return ReadBundle(bundle=bundle, repaired=repaired)


def _check_dsl_versions(bundle: ShareBundle) -> None:
    """`Test` 모델이 이미 거부하지만, 사유를 이 기능의 말로 바꿔 준다.

    기본 메시지("지원하지 않는 dsl_version")만으로는 사용자가 **묶음 전체를 못 쓴다**는
    것을 모른다.
    """
    bad = [t.id for t in bundle.tests if t.dsl_version != DSL_VERSION]
    if bad:
        raise InvalidTestError([f"{tid}: 이 도구가 읽을 수 없는 테스트 형식입니다" for tid in bad])


def _first_reason(exc: ValidationError) -> str:
    first = exc.errors()[0]
    loc = ".".join(str(p) for p in first.get("loc", ()))
    return f"{loc}: {first.get('msg', '')}" if loc else str(first.get("msg", ""))


def _test_problems(exc: ValidationError, raw_tests: list[object]) -> list[str]:
    """개별 테스트 정의에서 난 오류만 모아 **어느 테스트의 무엇인지** 말로 만든다.

    전부 모아서 한 번에 보고한다 — 하나씩 고치며 다시 가져오게 하면, 10건짜리 묶음에서
    10번 시도하게 된다.

    **식별자로 말한다.** `tests[3]` 은 사용자가 파일에서 찾을 수 있는 이름이 아니다.

    `tests` 목록 **자체**의 오류(비어 있음, 목록이 아님)는 여기 들어오지 않는다. 그것은
    개별 테스트의 문제가 아니라 묶음의 모양 문제이고, 사용자가 할 일이 다르다.
    """
    out: list[str] = []
    for err in exc.errors():
        loc = err.get("loc", ())
        if len(loc) < 2 or loc[0] != "tests" or not isinstance(loc[1], int):
            continue
        index = loc[1]
        entry = raw_tests[index] if index < len(raw_tests) else None
        name = entry.get("id") if isinstance(entry, dict) else None
        who = str(name) if name else f"{index + 1}번째 테스트"
        where = ".".join(str(p) for p in loc[2:]) or "(정의)"
        out.append(f"{who} — {where}: {err.get('msg', '')}")
    return out


def declare_missing(test: Test) -> tuple[Test, list[str]]:
    """이미 만들어진 `Test` 에 빠진 선언을 채운다. **쓰이는 곳이 없으면 그대로 돌려준다.**

    `read_bundle` 은 모델이 되기 전에 고치므로 이 함수를 쓰지 않는다. 다른 경로(정의를
    손으로 고친 뒤 다시 읽는 경우)에서 같은 규칙이 필요할 때를 위해 규칙을 한 곳에 둔다.
    """
    declared = {v.name for v in test.variables}
    missing = sorted(referenced_variable_names(test.steps) - declared)
    if not missing:
        return test, []
    added = [
        Variable(
            name=name,
            value=None if name.startswith(SENSITIVE_VARIABLE_PREFIX) else "",
            sensitive=name.startswith(SENSITIVE_VARIABLE_PREFIX),
        )
        for name in missing
    ]
    return test.model_copy(update={"variables": [*test.variables, *added]}), missing
