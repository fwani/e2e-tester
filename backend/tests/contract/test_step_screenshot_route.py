"""Step 별 화면 서빙 계약. 011 FR-390·FR-391·FR-396b · contracts/api-contract.md §3.

## 왜 `kind` 를 늘리지 않았는가

`GET …/result/artifacts/{kind}` 는 **실행 전체에 하나씩**인 산출물을 위한 것이고, `kind`
별 media type 표가 그 전제 위에 있다. Step 별은 인덱스를 갖는 다른 성질이라 `kind` 에 넣으면
인덱스를 실을 자리가 없다.

## 이 파일이 재는 것

성공 하나와 **오류 다섯**이다. 오류가 더 많은 이유는 이 엔드포인트가 「없음」을 말하는 방식이
곧 사용자에게 보이는 것이기 때문이다 — 「없습니다」만 돌려주면 화면은 민감 값 때문에 남기지
않은 것과 촬영이 실패한 것을 구분할 수 없다 (FR-391).
"""

from __future__ import annotations

import pathlib
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from itb.domain.run_result import Outcome, RunResult, StepOutcome, StepResult
from itb.storage.repository import ProjectRepository

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _project_root(client: TestClient) -> pathlib.Path:
    created = client.post(
        "/api/project/create",
        json={"name": "화면", "default_start_url": "http://127.0.0.1:1/"},
    )
    assert created.status_code == 201, created.text
    return pathlib.Path(created.json()["root"])


def _write_result(root: pathlib.Path, steps: list[StepResult]) -> None:
    now = datetime.now(UTC)
    ProjectRepository.open(root).write_result(
        RunResult(
            test_id="TC-001",
            outcome=Outcome("pass"),
            started_at=now,
            finished_at=now,
            total_ms=100,
            passed_count=len(steps),
            total_count=len(steps),
            browser="chromium",
            steps=steps,
        )
    )


def _step(index: int, **over: object) -> StepResult:
    base: dict[str, object] = {
        "step_id": f"st-{index + 1}",
        "index": index,
        "label": f"Step {index + 1}",
        "outcome": StepOutcome.PASS,
    }
    base.update(over)
    return StepResult(**base)  # type: ignore[arg-type]


def _url(index: int) -> str:
    return f"/api/tests/TC-001/result/steps/{index}/screenshot"


# ─── 성공 ───────────────────────────────────────────────────────────────────


def test_serves_png_bytes(client: TestClient) -> None:
    """경로가 아니라 **내용**을 돌려준다 (기존 산출물 서빙과 같은 규칙 · UX U-03)."""
    root = _project_root(client)
    shots = root / ".runs" / "TC-001" / "steps"
    shots.mkdir(parents=True)
    (shots / "1.png").write_bytes(PNG_MAGIC + b"\x00" * 16)
    _write_result(root, [_step(0), _step(1, screenshot=".runs/TC-001/steps/1.png")])

    resp = client.get(_url(1))
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"] == "image/png"
    assert resp.content.startswith(PNG_MAGIC)


# ─── 오류 다섯 ──────────────────────────────────────────────────────────────


def test_no_result_is_404(client: TestClient) -> None:
    _project_root(client)
    resp = client.get(_url(0))
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "TEST_NOT_FOUND"


def test_index_out_of_range_says_how_many(client: TestClient) -> None:
    """그 실행의 Step 수를 밝힌다 — 「없습니다」만으로는 무엇이 틀렸는지 알 수 없다."""
    root = _project_root(client)
    _write_result(root, [_step(0), _step(1)])
    resp = client.get(_url(9))
    assert resp.status_code == 404
    assert "2개" in resp.json()["error"]["message"]


def test_negative_index_is_400(client: TestClient) -> None:
    root = _project_root(client)
    _write_result(root, [_step(0)])
    resp = client.get("/api/tests/TC-001/result/steps/-1/screenshot")
    assert resp.status_code == 400, resp.text


def test_missing_screenshot_carries_the_reason(client: TestClient) -> None:
    """**FR-391 의 핵심.** 사유가 그대로 실려 나간다 — 화면이 그 행에서 말할 수 있어야 한다."""
    root = _project_root(client)
    _write_result(
        root,
        [_step(0, screenshot_note="민감 값이 화면에 있어 남기지 않았습니다")],
    )
    resp = client.get(_url(0))
    assert resp.status_code == 404
    assert "민감 값" in resp.json()["error"]["message"]


def test_missing_screenshot_without_note_still_answers(client: TestClient) -> None:
    """사유가 없어도 문장은 있어야 한다 — 빈 오류는 화면이 쓸 수 없다."""
    root = _project_root(client)
    _write_result(root, [_step(0)])
    resp = client.get(_url(0))
    assert resp.status_code == 404
    assert resp.json()["error"]["message"] != ""


def test_file_gone_says_so(client: TestClient) -> None:
    """결과에는 경로가 있는데 파일이 사라졌다 — `.runs/` 를 지운 경우다."""
    root = _project_root(client)
    (root / ".runs" / "TC-001").mkdir(parents=True)
    _write_result(root, [_step(0, screenshot=".runs/TC-001/steps/0.png")])
    resp = client.get(_url(0))
    assert resp.status_code == 404
    assert "다시 실행" in (resp.json()["error"].get("next_action") or "")


def test_path_outside_project_is_rejected(client: TestClient) -> None:
    """결과 파일을 손으로 고쳐 프로젝트 밖을 가리키게 해도 서빙하지 않는다.

    **기존 산출물 서빙과 같은 함수를 쓴다** (`_artifact_file`). 복제하면 한쪽만 고쳐지는
    날이 오고, 그날 프로젝트 밖 파일이 나간다.
    """
    root = _project_root(client)
    _write_result(root, [_step(0, screenshot="../../etc/passwd")])
    resp = client.get(_url(0))
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "INVALID_PATH"


# ─── 기존 결과 파일 호환 (SC-613) ───────────────────────────────────────────


def test_old_result_without_fields_is_readable(client: TestClient) -> None:
    """011 이전 결과 파일에는 두 필드가 없다. **읽히고**, 화면은 「없음」으로 답한다."""
    root = _project_root(client)
    runs = root / ".runs" / "TC-001"
    runs.mkdir(parents=True)
    (runs / "result.json").write_text(
        """{
          "test_id": "TC-001", "outcome": "pass",
          "started_at": "2026-09-01T00:00:00Z", "finished_at": "2026-09-01T00:00:01Z",
          "total_ms": 10, "passed_count": 1, "total_count": 1, "browser": "chromium",
          "steps": [{"step_id": "st-1", "index": 0, "label": "하나", "outcome": "pass"}]
        }""",
        encoding="utf-8",
    )
    # 결과 자체가 읽힌다.
    assert client.get("/api/tests/TC-001/result").status_code == 200
    # 화면은 없다는 사실을 받는다.
    assert client.get(_url(0)).status_code == 404
