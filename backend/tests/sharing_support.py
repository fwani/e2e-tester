"""공유 묶음 검증용 공용 도구 (기능 019).

브라우저 없이 프로젝트를 채운다. 내보내기가 보는 것은 저장된 정의뿐이므로, 정의를 직접
써 넣으면 녹화를 돌리지 않고도 필요한 모양을 전부 만들 수 있다 — `excel_support` 가
014 에서 쓴 방식과 같다.

**민감 값을 다루는 도구가 여기 있다.** `seal_secret` 은 제품의 봉인 경로를 그대로 지나며,
`SecretStore` 를 직접 건드리지 않는다. 테스트가 제품과 다른 경로로 값을 넣으면 "봉인됐다"
가 아니라 "봉인됐다고 우리가 믿는다" 를 확인하게 된다.
"""

from __future__ import annotations

import pathlib
from typing import Any

import yaml
from fastapi.testclient import TestClient

from itb.domain.assertion import Assertion, AssertionKind
from itb.domain.locator import Candidate, CandidateStatus, TargetLocator
from itb.domain.step import AssertionStep, ClickStep, FillStep, NavigateStep, Step
from itb.domain.test_case import AuthoringMode, Test, Variable, variable_reference
from itb.storage.repository import ProjectRepository

EXPORT = "/api/share/export"
PREVIEW = "/api/share/export/preview"
PLAN = "/api/share/import/plan"
COMMIT = "/api/share/import/commit"

KNOWN_PASSWORD = "not-a-real-password-019"
"""테스트가 봉인하는 값. **묶음 바이트에서 이 문자열을 찾아** 유출을 판정한다 (SC-004)."""


def verified(value: str) -> Candidate:
    return Candidate(value=value, status=CandidateStatus.VERIFIED)


def target(text: str) -> TargetLocator:
    return TargetLocator(text=verified(text))


def click(index: int, label: str) -> Step:
    return ClickStep(id=f"step-{index:02d}", label=label, target=target(label))


def fill(index: int, label: str, value: str) -> Step:
    return FillStep(id=f"step-{index:02d}", label=label, target=target(label), value=value)


def check(index: int, label: str, value: str) -> Step:
    return AssertionStep(
        id=f"step-{index:02d}",
        label=label,
        assertion=Assertion(kind=AssertionKind.TEXT, value=value),
    )


def navigate(index: int, label: str, url: str) -> Step:
    return NavigateStep(id=f"step-{index:02d}", label=label, url=url)


def make_test(
    test_id: str,
    name: str,
    *,
    steps: list[Step] | None = None,
    variables: list[Variable] | None = None,
    start_url: str = "https://example.internal/login",
) -> Test:
    """저장 가능한 테스트 하나. 기본은 평문 입력 1개 + 클릭 1개 + 검증 1개."""
    return Test(
        id=test_id,
        name=name,
        authoring_mode=AuthoringMode.RECORD,
        start_url=start_url,
        variables=variables or [],
        steps=steps
        or [
            fill(1, "아이디 입력", "platform-user"),
            click(2, "로그인 버튼"),
            check(3, "대시보드 표시 확인", "대시보드"),
        ],
    )


def make_secret_test(
    test_id: str = "TC-001",
    name: str = "로그인",
    *,
    secret_name: str = "SECRET_LOGIN_PW",
    plain_name: str | None = None,
) -> Test:
    """민감 변수를 쓰는 테스트. `plain_name` 을 주면 **값이 빈 비민감 변수**도 함께 쓴다."""
    steps: list[Step] = [fill(1, "비밀번호 입력", variable_reference(secret_name))]
    variables = [Variable(name=secret_name, value=None, sensitive=True)]
    if plain_name is not None:
        steps.insert(0, fill(0, "아이디 입력", variable_reference(plain_name)))
        variables.append(Variable(name=plain_name, value="", sensitive=False))
    steps.append(click(2, "로그인 버튼"))
    return make_test(test_id, name, steps=steps, variables=variables)


def repo_of(client: TestClient) -> ProjectRepository:
    """열린 프로젝트의 저장소를 연다."""
    root = client.get("/api/project").json()["root"]
    return ProjectRepository.open(pathlib.Path(root))


def write_tests(client: TestClient, *tests: Test) -> ProjectRepository:
    repo = repo_of(client)
    for test in tests:
        repo.write_test(test)
    return repo


def seal_secret(client: TestClient, name: str, value: str = KNOWN_PASSWORD) -> None:
    """제품의 봉인 경로로 값을 넣는다. 키가 이미 있어야 한다 (`keyed_client`)."""
    resp = client.put(f"/api/secrets/{name}", json={"value": value})
    assert resp.status_code == 204, resp.text


def ciphertexts(repo: ProjectRepository) -> list[str]:
    """비밀 파일의 암호문 전부. 묶음 바이트와 대조해 유출을 판정한다 (SC-004)."""
    path = repo.paths.secrets_file
    if not path.exists():
        return []
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return [str(v) for v in (raw.get("values") or {}).values()]


def load_bundle(data: bytes) -> dict[str, Any]:
    """내려받은 바이트를 YAML 로 다시 읽는다.

    **파일을 거쳐 온 것을 본다.** 우리가 만든 자료구조를 그대로 확인하면 "썼다고 생각한 것"
    을 확인하게 된다 — `excel_support.read_back` 과 같은 판단이다.
    """
    return yaml.safe_load(data.decode("utf-8"))


def export_bundle(client: TestClient, test_ids: list[str] | None = None) -> bytes:
    resp = client.post(EXPORT, json={"test_ids": test_ids})
    assert resp.status_code == 200, resp.text
    return resp.content
