"""증거 탭이 **내용**을 받는다 (UX U-03).

워크스루에서 겪은 것: 결과 화면의 SCREENSHOT 탭은 깨진 이미지 아이콘, CONSOLE·NETWORK 탭은
``.runs/TC-001/console.log`` 라는 상대 경로 한 줄이었다. 실제 파일은 디스크에 정상으로
있었다. 엔드포인트가 바이트 대신 ``{"kind","path"}`` JSON 을 돌려줬기 때문이다.
"""

from __future__ import annotations

import pathlib
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from itb.domain.run_result import Artifacts, Outcome, RunResult
from itb.storage.repository import ProjectRepository

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def _project_root(client: TestClient) -> pathlib.Path:
    created = client.post(
        "/api/project/create",
        json={"name": "증거", "default_start_url": "http://127.0.0.1:1/"},
    )
    assert created.status_code == 201, created.text
    return pathlib.Path(created.json()["root"])


def _write_failed_result(root: pathlib.Path, *, network_log: str | None) -> None:
    runs = root / ".runs" / "TC-001"
    runs.mkdir(parents=True)
    (runs / "failure.png").write_bytes(PNG_MAGIC + b"\x00" * 16)
    (runs / "console.log").write_text("[error] 로그인 응답 없음\n", encoding="utf-8")
    now = datetime.now(UTC)
    ProjectRepository.open(root).write_result(
        RunResult(
            test_id="TC-001",
            outcome=Outcome("fail"),
            started_at=now,
            finished_at=now,
            total_ms=230,
            passed_count=3,
            total_count=5,
            failed_step_index=3,
            browser="chromium",
            artifacts=Artifacts(
                failure_screenshot=".runs/TC-001/failure.png",
                console_log=".runs/TC-001/console.log",
                network_log=network_log,
            ),
        )
    )


def test_artifacts_come_back_as_bytes_with_their_media_type(client: TestClient) -> None:
    _write_failed_result(_project_root(client), network_log=None)

    shot = client.get("/api/tests/TC-001/result/artifacts/screenshot")
    assert shot.status_code == 200, shot.text
    assert shot.headers["content-type"].startswith("image/png"), shot.headers["content-type"]
    assert shot.content.startswith(PNG_MAGIC), "이미지 바이트가 아니다 — <img> 가 깨진다"

    log = client.get("/api/tests/TC-001/result/artifacts/console")
    assert log.status_code == 200, log.text
    assert log.headers["content-type"].startswith("text/plain")
    assert log.text == "[error] 로그인 응답 없음\n", "로그 본문이 아니다"

    missing = client.get("/api/tests/TC-001/result/artifacts/network")
    assert missing.status_code == 404
    assert "산출물이 없습니다" in missing.json()["error"]["message"]


def test_deleted_artifact_file_says_what_to_do(client: TestClient) -> None:
    """결과 파일은 가리키는데 실제 파일이 지워진 경우 — 경로를 보여주고 다음 행동을 준다."""
    _write_failed_result(_project_root(client), network_log=".runs/TC-001/network.log")

    resp = client.get("/api/tests/TC-001/result/artifacts/network")

    assert resp.status_code == 404, resp.text
    body = resp.json()["error"]
    assert ".runs/TC-001/network.log" in body["message"]
    assert "다시 실행" in body["next_action"]
