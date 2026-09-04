"""T074 — 복호화된 민감 값이 어디에도 남지 않는다 (SC-010, FR-089d).

**전수 검사다.** 한 경로만 막고 통과했다고 보면 안 된다 — 값은 정의 파일, 비밀 파일, 실행
산출물(스크린샷·콘솔·네트워크), 실패 메시지, 임시 파일, API 응답, WebSocket 이벤트, 그리고
생성된 코드 중 **어디로든** 샐 수 있다. 이 파일은 그 목록을 하나씩 훑는다.

민감 값은 재실행 중 실제로 복호화되어 브라우저에 입력된다. 즉 이 테스트는 "값이 쓰이지
않아서 새지 않은" 상태를 통과로 착각하지 않는다 — 값이 쓰였음을 먼저 확인한다.
"""

from __future__ import annotations

import json
import pathlib
import tempfile

import pytest
from fastapi.testclient import TestClient
from us2_support import record_login, replay, result_of

SECRET = "Tr0ub4dor-3-not-a-real-password"
"""픽스처 앱에 입력할 값. 짧으면 스크러버가 무시하므로 충분히 길게 잡는다."""


def _all_text_under(root: pathlib.Path) -> list[tuple[pathlib.Path, str]]:
    """디렉터리 아래 모든 파일의 내용을 텍스트로 읽는다.

    바이너리(스크린샷 PNG 등)도 **바이트 그대로** 훑는다 — 메타데이터에 값이 남을 수 있다.
    """
    out: list[tuple[pathlib.Path, str]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        try:
            data = path.read_bytes()
        except OSError:  # pragma: no cover - 읽을 수 없는 파일은 검사 대상이 아니다
            continue
        out.append((path, data.decode("utf-8", errors="replace")))
    return out


@pytest.mark.usefixtures("fixture_app")
def test_decrypted_secret_never_reaches_any_artifact(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
) -> None:
    """FR-089d — 복호화된 값이 디스크·응답·이벤트 어디에도 남지 않는다."""
    client = keyed_client
    test_id = record_login(client, fixture_app, password=SECRET)

    definition = client.get(f"/api/tests/{test_id}").json()
    sensitive = [v for v in definition["variables"] if v["sensitive"]]
    assert sensitive, (
        "비밀번호 입력이 민감 변수로 옮겨지지 않았다 — 이 테스트가 무의미해진다"
    )
    assert all(v["value"] is None for v in sensitive), (
        f"민감 변수가 정의 파일에 값을 갖고 있다: {sensitive}"
    )

    event_log.clear()
    view = replay(client, test_id)
    assert view["state"] == "completed", (
        f"민감 값을 쓰는 재실행이 통과하지 않았다: {view['state']}. "
        "값이 실제로 복호화되어 쓰였음을 먼저 확인해야 검사가 성립한다"
    )

    root = client.app.state.itb.repository.paths.root
    leaks: list[str] = []

    # 1·2·3. 정의 파일 · 비밀 파일 · 실행 산출물(스크린샷 메타데이터 포함)
    for path, text in _all_text_under(root):
        if SECRET in text:
            leaks.append(f"파일 {path.relative_to(root)}")

    # 4. 임시 디렉터리 — 실행 중 만들어진 파일이 남아 있으면 안 된다
    tmp_root = pathlib.Path(tempfile.gettempdir())
    for path in tmp_root.glob("itb-*"):
        if not path.is_file():
            continue
        if SECRET in path.read_bytes().decode("utf-8", errors="replace"):
            leaks.append(f"임시 파일 {path}")

    # 5. API 응답 — 결과·정의·목록·비밀 목록
    responses = {
        "정의": client.get(f"/api/tests/{test_id}").text,
        "결과": json.dumps(result_of(client, test_id), ensure_ascii=False),
        "목록": client.get("/api/tests").text,
        "비밀 목록": client.get("/api/secrets").text,
    }
    for label, body in responses.items():
        if SECRET in body:
            leaks.append(f"API 응답({label})")

    # 6. WebSocket 이벤트 — 발행 지점에서 가로챈 전량
    for name, payload in event_log:
        if SECRET in json.dumps(payload, ensure_ascii=False, default=str):
            leaks.append(f"WS 이벤트({name})")

    assert not leaks, f"복호화된 민감 값이 다음 위치에 남았다: {sorted(set(leaks))}"


@pytest.mark.usefixtures("fixture_app")
def test_failure_message_and_artifacts_are_scrubbed(
    keyed_client: TestClient,
    fixture_app: str,
    event_log: list[tuple[str, dict]],
) -> None:
    """FR-089d — 실패 경로에서도 마스킹된다.

    실패 메시지에는 시도한 후보 표현과 대상 화면 텍스트가 들어간다. 성공 경로만 막고
    실패 경로를 놓치는 것이 전형적인 누출 방식이다.
    """
    from us2_support import break_first_click

    client = keyed_client
    test_id = record_login(client, fixture_app, password=SECRET)
    broken_index = break_first_click(client, test_id)

    event_log.clear()
    view = replay(client, test_id)
    assert view["state"] == "failed", f"실패를 유도했는데 실패하지 않았다: {view['state']}"

    result = result_of(client, test_id)
    assert result["outcome"] == "fail"
    assert result["failed_step_index"] == broken_index

    blob = json.dumps(result, ensure_ascii=False, default=str)
    assert SECRET not in blob, "실패 결과에 민감 값이 남았다"

    root = client.app.state.itb.repository.paths.root
    for path, text in _all_text_under(root):
        assert SECRET not in text, f"실패 산출물에 민감 값이 남았다: {path.relative_to(root)}"

    for name, payload in event_log:
        assert SECRET not in json.dumps(payload, ensure_ascii=False, default=str), (
            f"실패 이벤트에 민감 값이 남았다: {name}"
        )


def test_no_generated_code_surface_leaks_secrets() -> None:
    """FR-089d-1 — 생성 코드는 민감 변수를 **참조로만** 담는다.

    이 테스트는 생성기가 없던 때 "표면이 아직 없다" 를 확인하는 형태로 먼저 있었다
    (헌법 품질 게이트 4 — 조용히 통과하는 구멍을 남기지 않는다). 생성기가 들어왔으므로
    이제 실제 검사를 한다.
    """
    from itb.domain.locator import Candidate, CandidateStatus, TargetLocator
    from itb.domain.step import FillStep
    from itb.domain.test_case import Variable
    from itb.generator.playwright_gen import ValueRenderer, step_lines

    step = FillStep(
        id="step-01",
        label="비밀번호 입력",
        target=TargetLocator(
            tag="input",
            label=Candidate(value="비밀번호", status=CandidateStatus.VERIFIED),
        ),
        value="{{SECRET_VALUE_1}}",
    )
    renderer = ValueRenderer(
        {"SECRET_VALUE_1": Variable(name="SECRET_VALUE_1", value=None, sensitive=True)}
    )
    code = "\n".join(step_lines(step, renderer))

    assert "SECRET_VALUE_1" in code, "민감 변수 참조가 생성 코드에 없다"
    # 참조는 **환경 변수 조회**로만 나타난다 — 값이 코드에 들어갈 자리가 없다.
    assert "process.env.SECRET_VALUE_1" in code
    assert SECRET not in code


# ─── 002 — 인라인 입력 경로도 같은 규칙을 지킨다 (DR-024 · SC-010) ──────────


def test_inline_put_stores_only_ciphertext(keyed_client: TestClient) -> None:
    """DR-024 — 인라인 입력이 쓰는 경로는 `PUT /api/secrets/{name}` 하나다.

    Step 편집 안에서 넣든 별도 화면에서 넣든 **같은 엔드포인트**를 쓴다. 그래서 봉인
    규칙이 두 벌로 갈리지 않는다 — 새 경로를 만들었다면 그쪽만 규칙을 빠뜨릴 수 있었다
    (research R5 가 새 엔드포인트를 만들지 않기로 한 이유).
    """
    resp = keyed_client.put("/api/secrets/INLINE_PW", json={"value": SECRET})
    assert resp.status_code in (200, 204), resp.text

    repo = keyed_client.app.state.itb.repository  # type: ignore[attr-defined]
    raw = repo.paths.secrets_file.read_text(encoding="utf-8")
    assert SECRET not in raw, "비밀 파일에 평문이 있다"
    assert "INLINE_PW" in raw, "변수 이름이 없다"


def test_secrets_listing_never_returns_values(keyed_client: TestClient) -> None:
    """인라인 입력이 기존 변수를 고를 때 쓰는 목록. **값이 오면 안 된다** (DR-026)."""
    keyed_client.put("/api/secrets/INLINE_PW", json={"value": SECRET})

    resp = keyed_client.get("/api/secrets")

    assert resp.status_code == 200, resp.text
    assert SECRET not in resp.text
    names = resp.json()["names"]
    assert {"INLINE_PW"} <= {n["name"] for n in names}
    for entry in names:
        assert set(entry) == {"name", "present"}, f"값이 딸려 왔다: {entry}"


def test_put_requires_only_the_public_key(project_client: TestClient) -> None:
    """**인라인 입력이 성립하는 근거** (research R5).

    비밀키가 필요했다면 Step 을 편집하는 자리에서 값을 넣을 수 없었다 — 실행 시에만
    있는 것을 편집 시점에 요구하게 된다.
    """
    project_client.post("/api/keys/generate", json={"passphrase": None})
    keys = project_client.app.state.itb.key_paths  # type: ignore[attr-defined]
    keys.private.unlink()  # 비밀키를 지운다

    resp = project_client.put("/api/secrets/ONLY_PUBLIC", json={"value": SECRET})

    assert resp.status_code in (200, 204), resp.text
