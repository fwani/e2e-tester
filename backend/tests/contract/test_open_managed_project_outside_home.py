"""도구가 만든 프로젝트는 위치와 무관하게 다시 열 수 있다 (UX U-08).

워크스루에서 겪은 것: ``XDG_DATA_HOME`` 이 홈 밖을 가리키는 환경에서 프로젝트를 만들면
목록에 뜨는데, 「열기」를 누르면 「사용자 홈 디렉터리 아래의 경로만 열 수 있습니다. 프로젝트
폴더 안의 경로를 지정하세요.」 로 거절됐다. 그 경로는 도구가 정하고 도구가 만들고 도구가
화면에 찍어 준 것이다 — 사용자는 아무 경로도 입력한 적이 없다.

홈 경계는 임의 파일 시스템 탐색을 막기 위한 것이고(DR-005), 도구가 아는 위치는 그 경계가
지키려는 것과 무관하다.
"""

from __future__ import annotations

import pathlib

import pytest
from fastapi.testclient import TestClient

from itb.storage.paths import home_root


def test_managed_project_outside_home_reopens(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    outside = tmp_path / "outside-data"  # conftest 의 가짜 홈(tmp_path/home)의 형제 — 홈 밖이다
    monkeypatch.setenv("XDG_DATA_HOME", str(outside))

    created = client.post(
        "/api/project/create",
        json={"name": "홈 밖 프로젝트", "default_start_url": "http://127.0.0.1:1/"},
    )
    assert created.status_code == 201, created.text
    root = pathlib.Path(created.json()["root"])
    assert home_root() not in root.resolve().parents, "재현 조건이 아니다 — 홈 안에 만들어졌다"

    listed = client.get("/api/project/list").json()["projects"]
    assert any(p["root"] == str(root) for p in listed), "목록에 없다면 이 테스트의 전제가 틀렸다"

    reopened = client.post("/api/project/open", json={"path": str(root)})
    assert reopened.status_code == 200, (
        f"도구가 만들고 목록에 띄운 프로젝트를 도구가 열지 못한다: {reopened.text}"
    )
    assert reopened.json()["name"] == "홈 밖 프로젝트"


def test_unknown_path_outside_home_is_still_refused(
    client: TestClient, tmp_path: pathlib.Path
) -> None:
    """경계를 넓힌 것이 아니라 예외를 둔 것이다. 모르는 홈 밖 경로는 여전히 막는다."""
    stranger = tmp_path / "stranger"
    stranger.mkdir()
    (stranger / "itb-project.yaml").write_text(
        "name: 낯선 것\ndefault_start_url: http://127.0.0.1:1/\n", encoding="utf-8"
    )

    resp = client.post("/api/project/open", json={"path": str(stranger)})

    assert resp.status_code == 400, resp.text
    body = resp.json()["error"]
    assert body["code"] == "INVALID_PATH"
    assert "도구가 만들었거나 이전에 연" in body["message"], body["message"]
