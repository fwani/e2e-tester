"""T049 — Test Step DSL 왕복 계약 (contracts/step-dsl.md).

**이것이 사용자에게 가장 중요한 계약이다.** 제품 UI 나 API 는 바뀔 수 있지만 이 파일들은
사용자가 git 에 커밋해 보관하는 자산이다 (FR-088b, 원칙 V).

계약 문서의 예제 YAML 을 그대로 적재해 검증한다 — 문서와 코드가 갈라지면 실패한다.
검증 규칙 위반 케이스도 전부 거절되는지 확인한다.
"""

from __future__ import annotations

import pathlib

import pytest
import yaml

from itb.domain.test_case import Test
from itb.storage.yaml_io import DefinitionError, dump_model, load_model

# ─── contracts/step-dsl.md 의 예제 ─────────────────────────────────────────

SINGLE_TAB = """
dsl_version: 1
id: TC-001
name: 프로젝트 생성
authoring_mode: record
start_url: https://example.internal/login
browser: chromium
variables:
  - name: PROJECT_NAME
    value: TEST
    sensitive: false
  - name: LOGIN_PASSWORD
    value: null
    sensitive: true
steps:
  - id: step-01
    type: fill
    label: 비밀번호 입력
    author: human
    tab: 0
    timeout_ms: 5000
    value: "{{LOGIN_PASSWORD}}"
    target:
      tag: input
      label: { value: 비밀번호, status: verified }
      css:   { value: "#password", status: verified }
  - id: step-02
    type: click
    label: 프로젝트 생성 클릭
    author: human
    tab: 0
    timeout_ms: 5000
    target:
      tag: button
      test_id:         { value: create-project, status: verified }
      role: button
      accessible_name: 프로젝트 생성
      role_status: verified
      text:            { value: 프로젝트 생성, status: verified }
      css:             { value: ".project-header button:nth-child(2)", status: verified }
  - id: step-03
    type: assertion
    label: '"TEST" 표시 확인'
    author: human
    tab: 0
    timeout_ms: 5000
    assertion:
      kind: visible
      value: "{{PROJECT_NAME}}"
      target:
        text: { value: TEST, status: verified }
"""

MULTI_TAB = """
dsl_version: 1
id: TC-005
name: 약관 새 창 확인
authoring_mode: record
start_url: https://example.internal/signup
browser: chromium
variables: []
steps:
  - id: step-01
    type: click
    label: 약관 보기 클릭 (새 창 열림)
    author: human
    tab: 0
    timeout_ms: 5000
    target:
      test_id: { value: terms-link, status: verified }
      role: link
      accessible_name: 약관 보기
      role_status: verified
      css: { value: "a.terms", status: verified }
  - id: step-02
    type: assertion
    label: 새 창에 약관 제목이 보이는지 확인
    author: human
    tab: 1
    timeout_ms: 5000
    assertion:
      kind: visible
      target:
        role: heading
        accessible_name: 서비스 이용약관
        role_status: verified
        text: { value: 서비스 이용약관, status: verified }
  - id: step-03
    type: close_tab
    label: 약관 창 닫기
    author: human
    tab: 1
    timeout_ms: 5000
  - id: step-04
    type: assertion
    label: 원래 화면의 동의 체크박스가 보이는지 확인
    author: human
    tab: 0
    timeout_ms: 5000
    assertion:
      kind: visible
      target:
        test_id: { value: agree-checkbox, status: verified }
"""

AI_AUTHORED = """
dsl_version: 1
id: TC-002
name: 프로젝트 삭제
authoring_mode: ai
ai_instruction: |
  로그인한 다음 프로젝트 메뉴로 이동해서
  TEST 프로젝트를 삭제해.
start_url: https://example.internal/login
browser: chromium
variables: []
steps:
  - id: step-01
    type: click
    label: 프로젝트 메뉴 클릭
    author: ai
    tab: 0
    timeout_ms: 5000
    target:
      role: menuitem
      accessible_name: 프로젝트
      role_status: verified
      css: { value: "nav a:nth-child(2)", status: verified }
  - id: step-02
    type: click
    label: 삭제 클릭
    author: human
    tab: 0
    timeout_ms: 5000
    target:
      text: { value: 삭제, status: verified }
      css:  { value: ".menu-popup button:last-child", status: verified }
"""


def _write(tmp_path: pathlib.Path, body: str) -> pathlib.Path:
    p = tmp_path / "test.yaml"
    p.write_text(body, encoding="utf-8")
    return p


# ─── 계약 문서의 예제가 적재된다 ───────────────────────────────────────────


@pytest.mark.parametrize(
    ("name", "body"),
    [("단일 탭", SINGLE_TAB), ("멀티 탭", MULTI_TAB), ("AI 작성", AI_AUTHORED)],
)
def test_contract_examples_load(name: str, body: str, tmp_path: pathlib.Path) -> None:
    """계약 문서의 예제가 그대로 적재되어야 한다. 문서와 코드가 갈라지면 실패한다."""
    test = load_model(_write(tmp_path, body), Test)
    assert test.steps, name


def test_single_tab_example_details(tmp_path: pathlib.Path) -> None:
    test = load_model(_write(tmp_path, SINGLE_TAB), Test)
    assert test.id == "TC-001"
    assert test.referenced_variables() == {"LOGIN_PASSWORD", "PROJECT_NAME"}
    assert test.sensitive_variable_names() == {"LOGIN_PASSWORD"}
    # 민감 변수는 값을 갖지 않는다 (FR-082)
    sensitive = next(v for v in test.variables if v.sensitive)
    assert sensitive.value is None


def test_multi_tab_example_tab_references(tmp_path: pathlib.Path) -> None:
    """FR-030a~c — 탭 참조와 close_tab 이 계약대로 표현된다."""
    test = load_model(_write(tmp_path, MULTI_TAB), Test)
    tabs = [s.tab for s in test.steps]
    assert tabs == [0, 1, 1, 0]
    types = [s.type.value for s in test.steps]
    assert types == ["click", "assertion", "close_tab", "assertion"]


def test_ai_example_keeps_instruction_but_steps_are_deterministic(
    tmp_path: pathlib.Path,
) -> None:
    """FR-063 — 지시문은 보관만 하고 실행 대상이 아니다."""
    test = load_model(_write(tmp_path, AI_AUTHORED), Test)
    assert test.ai_instruction is not None
    assert "TEST 프로젝트를 삭제해" in test.ai_instruction
    # 지시문에서 변수 참조를 뽑지 않는다 — 실행 대상이 아니다
    assert test.referenced_variables() == set()


def test_ai_and_human_steps_have_identical_shape(tmp_path: pathlib.Path) -> None:
    """원칙 I — 작성 주체가 달라도 구조가 같다 (FR-014·FR-075)."""
    test = load_model(_write(tmp_path, AI_AUTHORED), Test)
    ai_step, human_step = test.steps
    assert ai_step.author.value == "ai"
    assert human_step.author.value == "human"
    assert type(ai_step) is type(human_step)
    assert set(ai_step.model_dump()) == set(human_step.model_dump())


# ─── 왕복 (저장 → 적재 → 저장) ─────────────────────────────────────────────


@pytest.mark.parametrize("body", [SINGLE_TAB, MULTI_TAB, AI_AUTHORED])
def test_roundtrip_is_stable(body: str, tmp_path: pathlib.Path) -> None:
    """적재 → 저장 → 재적재가 같은 결과를 낸다.

    안정적이지 않으면 저장할 때마다 git diff 가 흔들려 사용자가 자산을 관리할 수 없다.
    """
    first = load_model(_write(tmp_path, body), Test)
    out = tmp_path / "out.yaml"
    dump_model(out, first)
    second = load_model(out, Test)
    assert first.model_dump(mode="json") == second.model_dump(mode="json")

    dump_model(out, second)
    assert out.read_text(encoding="utf-8") == (tmp_path / "out.yaml").read_text(encoding="utf-8")


def test_dumped_yaml_is_human_readable(tmp_path: pathlib.Path) -> None:
    """FR-011 — 사람이 읽고 편집할 수 있어야 한다."""
    test = load_model(_write(tmp_path, SINGLE_TAB), Test)
    out = tmp_path / "out.yaml"
    dump_model(out, test)
    raw = out.read_text(encoding="utf-8")
    # 한글이 이스케이프되지 않는다
    assert "프로젝트 생성" in raw
    # 필드 순서가 모델 정의를 따른다 (정렬하지 않는다)
    assert raw.index("dsl_version") < raw.index("steps")
    # 안전 로더로 다시 읽을 수 있다
    assert isinstance(yaml.safe_load(raw), dict)


# ─── 검증 규칙 위반은 전부 거절된다 (contracts/step-dsl.md §검증 규칙) ────


VIOLATIONS: list[tuple[str, str]] = [
    (
        "Step 0개",
        "dsl_version: 1\nid: TC-001\nname: x\nauthoring_mode: record\n"
        "start_url: http://a/\nsteps: []\n",
    ),
    (
        "id 패턴",
        "dsl_version: 1\nid: TC-1\nname: x\nauthoring_mode: record\n"
        "start_url: http://a/\nsteps:\n  - {id: step-01, type: close_tab, label: x}\n",
    ),
    (
        "변수 이름 패턴",
        "dsl_version: 1\nid: TC-001\nname: x\nauthoring_mode: record\n"
        "start_url: http://a/\nvariables:\n  - {name: lower, value: v}\n"
        "steps:\n  - {id: step-01, type: close_tab, label: x}\n",
    ),
    (
        "민감 변수에 평문 값",
        "dsl_version: 1\nid: TC-001\nname: x\nauthoring_mode: record\n"
        "start_url: http://a/\nvariables:\n  - {name: S, value: plain, sensitive: true}\n"
        "steps:\n  - {id: step-01, type: close_tab, label: x}\n",
    ),
    (
        "후보 없는 target",
        "dsl_version: 1\nid: TC-001\nname: x\nauthoring_mode: record\n"
        "start_url: http://a/\nsteps:\n"
        "  - {id: step-01, type: click, label: x, target: {tag: div}}\n",
    ),
    (
        "정의되지 않은 변수 참조",
        "dsl_version: 1\nid: TC-001\nname: x\nauthoring_mode: record\n"
        "start_url: http://a/\nsteps:\n"
        "  - id: step-01\n    type: fill\n    label: x\n    value: '{{NOPE}}'\n"
        "    target: {css: {value: '#a', status: verified}}\n",
    ),
    (
        "timeout 범위 초과",
        "dsl_version: 1\nid: TC-001\nname: x\nauthoring_mode: record\n"
        "start_url: http://a/\nsteps:\n"
        "  - {id: step-01, type: close_tab, label: x, timeout_ms: 999999}\n",
    ),
    (
        "tab 음수",
        "dsl_version: 1\nid: TC-001\nname: x\nauthoring_mode: record\n"
        "start_url: http://a/\nsteps:\n"
        "  - {id: step-01, type: close_tab, label: x, tab: -1}\n",
    ),
    (
        "dsl_version 미지원",
        "dsl_version: 99\nid: TC-001\nname: x\nauthoring_mode: record\n"
        "start_url: http://a/\nsteps:\n  - {id: step-01, type: close_tab, label: x}\n",
    ),
    (
        "Step id 중복",
        "dsl_version: 1\nid: TC-001\nname: x\nauthoring_mode: record\n"
        "start_url: http://a/\nsteps:\n"
        "  - {id: step-01, type: close_tab, label: a}\n"
        "  - {id: step-01, type: close_tab, label: b}\n",
    ),
    (
        "미지 Step 종류",
        "dsl_version: 1\nid: TC-001\nname: x\nauthoring_mode: record\n"
        "start_url: http://a/\nsteps:\n  - {id: step-01, type: teleport, label: x}\n",
    ),
    (
        "미지 필드",
        "dsl_version: 1\nid: TC-001\nname: x\nauthoring_mode: record\n"
        "start_url: http://a/\nbogus: 1\nsteps:\n"
        "  - {id: step-01, type: close_tab, label: x}\n",
    ),
]


@pytest.mark.parametrize(("why", "body"), VIOLATIONS, ids=[v[0] for v in VIOLATIONS])
def test_violations_are_rejected(why: str, body: str, tmp_path: pathlib.Path) -> None:
    with pytest.raises(DefinitionError) as exc:
        load_model(_write(tmp_path, body), Test)
    # 사용자가 직접 고칠 수 있도록 파일 경로가 메시지에 있어야 한다
    assert "test.yaml" in str(exc.value), why


def test_unsafe_yaml_tag_is_not_executed(tmp_path: pathlib.Path) -> None:
    """임의 객체 역직렬화를 허용하면 정의 파일이 코드 실행 경로가 된다."""
    body = "!!python/object/apply:os.system ['echo pwned']\n"
    with pytest.raises(DefinitionError):
        load_model(_write(tmp_path, body), Test)


def test_error_message_names_the_failing_field(tmp_path: pathlib.Path) -> None:
    body = (
        "dsl_version: 1\nid: TC-001\nname: x\nauthoring_mode: record\n"
        "start_url: http://a/\nsteps: []\n"
    )
    with pytest.raises(DefinitionError) as exc:
        load_model(_write(tmp_path, body), Test)
    assert "steps" in str(exc.value)


# ─── 004: 실행 속도는 테스트 자산이 아니다 (FR-110, 헌법 원칙 V) ─────────────


def test_pacing_never_reaches_the_stored_definition(tmp_path: pathlib.Path) -> None:
    """저장된 테스트 정의에 속도 관련 키가 없다.

    **구조로 이미 막혀 있다** — 속도는 `~/.config/itb/preferences.json` 에 있고 테스트
    자산 트리 밖이다. 그럼에도 이 단언을 두는 이유는, 나중에 누군가 편의로 "이 테스트는
    느리게 돌려야 한다" 를 정의에 넣고 싶어질 때 여기서 걸리게 하려는 것이다.

    정의에 들어가면 두 가지가 깨진다. 개인 취향이 팀 저장소에 커밋되고, 내보낸 Playwright
    프로젝트가 제품 고유 개념을 들고 다니게 된다 (헌법 원칙 V).
    """
    from itb.domain.run_pacing import RunPacing

    forbidden = {"pacing", "run_pacing", "delay_ms", "auto_pause", "speed"}

    import json

    # 스키마는 pydantic 내부 표현을 섞어 갖고 있어 YAML 로 못 찍는다. JSON 으로 본다.
    schema = json.dumps(Test.model_json_schema(), ensure_ascii=False)
    for key in forbidden:
        assert f'"{key}"' not in schema, (
            f"Step DSL 스키마에 실행 속도 개념({key})이 들어갔다 — FR-110 위반"
        )

    # 실제 정의를 왕복시켜도 속도 값이 어디에도 나타나지 않는다.
    for example in (SINGLE_TAB, MULTI_TAB, AI_AUTHORED):
        loaded = load_model(_write(tmp_path, example), Test)
        body = yaml.safe_dump(loaded.model_dump(mode="json"), allow_unicode=True)
        for pacing in RunPacing:
            assert f"pacing: {pacing.value}" not in body


# ─── 013 — 기존 프로젝트 파일이 그대로 읽힌다 (SC-629) ─────────────────────


def test_a_project_file_without_groups_still_loads(tmp_path: pathlib.Path) -> None:
    """013 이전에 만든 `itb-project.yaml` 에는 `groups` 키가 없다.

    **기본값이 빈 목록이어야 그대로 읽힌다.** 업그레이드만으로 사용자의 버전 관리에
    변경이 들어가서는 안 된다 — 도구가 기존 자산을 먼저 움직이지 않는다 (FR-445).
    """
    from itb.domain.test_case import Project
    from itb.storage.yaml_io import load_model

    old_file = tmp_path / "itb-project.yaml"
    old_file.write_text(
        "name: 레거시 프로젝트\n"
        "default_start_url: http://127.0.0.1:4300/login.html\n"
        "browser: chromium\n"
        "test_id_attribute: data-testid\n"
        "next_test_number: 4\n"
        "max_tabs: 10\n",
        encoding="utf-8",
    )

    project = load_model(old_file, Project)

    assert project.groups == []
    assert project.name == "레거시 프로젝트"


def test_a_reserved_prefix_cannot_be_a_group(tmp_path: pathlib.Path) -> None:
    """FR-445a — `TC` 를 그룹으로 두면 기존 테스트가 그 그룹에 나타난다.

    도메인 모델에서 막는다. 라우트만 막으면 파일을 손으로 고친 프로젝트에서 새어 나간다.
    """
    from itb.domain.test_case import Project
    from itb.storage.yaml_io import DefinitionError, load_model

    bad = tmp_path / "itb-project.yaml"
    bad.write_text(
        "name: p\n"
        "default_start_url: http://127.0.0.1:4300/login.html\n"
        "groups:\n"
        "  - prefix: TC\n"
        "    name: 가로채기\n",
        encoding="utf-8",
    )

    with pytest.raises(DefinitionError):
        load_model(bad, Project)


def test_duplicate_group_prefixes_are_rejected(tmp_path: pathlib.Path) -> None:
    """FR-442 — 접두어가 겹치면 식별자가 어느 그룹인지 가리키지 못한다."""
    from itb.domain.test_case import Project
    from itb.storage.yaml_io import DefinitionError, load_model

    bad = tmp_path / "itb-project.yaml"
    bad.write_text(
        "name: p\n"
        "default_start_url: http://127.0.0.1:4300/login.html\n"
        "groups:\n"
        "  - prefix: USER\n"
        "    name: 하나\n"
        "  - prefix: USER\n"
        "    name: 둘\n",
        encoding="utf-8",
    )

    with pytest.raises(DefinitionError):
        load_model(bad, Project)
