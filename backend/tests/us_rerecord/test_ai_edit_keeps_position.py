"""**AI 가 Step 을 고쳐도 실행 위치가 그대로다** (2026-09-11 사용자 보고).

## 무엇을 봤나

재녹화 세션에서 AI 에게 지시하자 AI 가 Step 둘을 만들고, 이어서 그 대상을 다시
지목했다. 그 순간 화면 머리가 「Step 23 이후 정지」에서 **「Step 01 에서 중지」**로
바뀌었다. 그 상태에서 「계속하기」를 누르면 이미 지나온 로그인부터 전부 다시 실행한다.

## 왜 그랬나

편집 연산(`step_edits`)은 실행 위치를 **받아서 고쳐 돌려준다** — 앞에서 지운 Step 만큼
위치를 당기는 식이다. 그 결과가 `_apply_rerecord_edit` 을 지나 세션의 위치가 된다.

도구 쪽 `BrowserToolbox._current_index` 는 **0 을 넘기고 있었고**, 주석은 「편집 연산이
이 값으로 하는 일은 경고뿐」이라고 적고 있었다. 그것이 틀렸다. AI 가 무엇을 고치든
세션의 실행 위치가 0 이 됐다.

SC-007(로그인이 재실행되지 않는다)이 정확히 이 지점에 걸려 있다.

## 왜 사람의 편집에서는 안 났나

사람의 편집은 `steps.py` 를 지나고, 그쪽은 세션이 가진 위치를 그대로 넘긴다. 같은 순수
함수를 쓰면서 **넘기는 값만 달랐다** — 원칙 I 이 지키려는 것이 바로 이 대칭이다.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from tests.us2_support import stop_quietly
from tests.us3_support import record_login_then_two_menus
from tests.us4_support import Action, click_named, install_driver, observe
from tests.us_rerecord.support import open_rerecord, saved_step_ids, say

pytestmark = pytest.mark.browser


def relabel(step_id: str, label: str) -> Action:
    """AI 가 자기가 만든 Step 의 이름을 고친다 (FR-032).

    **`update_step` 을 고른 이유**는 그것이 목록을 바꾸지 않기 때문이다. 삭제·이동은
    위치가 움직이는 것이 정상이므로 「위치가 그대로다」를 셀 수 없다.
    """

    def action(_state: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        return ("update_step", {"step_id": step_id, "field": "label", "value": label})

    return action


def test_editing_a_step_does_not_rewind_the_run_position(
    keyed_client: TestClient, fixture_app: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    test_id = record_login_then_two_menus(keyed_client, fixture_app)
    saved = saved_step_ids(keyed_client, test_id)
    # AI 가 만들 Step 의 id — `allocate_step_id` 가 「쓰인 번호를 피해 개수+1」로 준다.
    made = f"step-{len(saved) + 1:02d}"

    install_driver(
        monkeypatch,
        [
            observe(0),
            # 하나 만들고,
            click_named("프로젝트 생성"),
            # 방금 만든 그것을 고친다. 여기가 위치를 되감던 자리다.
            relabel(made, "생성 상자를 연다"),
        ],
    )

    # 마지막 Step 하나를 구간으로 — 도착점은 그 앞이다.
    sid = open_rerecord(keyed_client, test_id, [saved[-1]])
    assert isinstance(sid, str)
    try:
        arrival = keyed_client.get(f"/api/sessions/{sid}").json()["current_step_index"]
        assert arrival > 0, "도착점이 0 이면 되감김을 구별할 수 없다"

        view = say(keyed_client, sid, "프로젝트 생성을 눌러 줘")

        # 고친 것이 반영됐다 — 대본이 실제로 그 Step 을 건드렸다는 증거다.
        labels = {s["id"]: s["label"] for s in view["steps"]}
        assert labels.get(made) == "생성 상자를 연다", labels

        # **그리고 위치는 앞으로만 갔다.** 수정 전에는 여기가 0 이었다.
        assert view["current_step_index"] >= arrival, (
            f"실행 위치가 되감겼다: {arrival} → {view['current_step_index']}. "
            "「계속하기」가 이미 지나온 Step 을 다시 실행한다 (SC-007 위반)"
        )
    finally:
        stop_quietly(keyed_client, sid)
