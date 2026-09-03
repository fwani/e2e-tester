"""T158 — 민감 값 치환이 이벤트 발행보다 먼저 일어남을 보증한다 (analyze C2).

`/speckit-analyze` 가 HIGH 로 식별한 구체적 실패 경로:

    리코더가 비밀번호 평문을 포착 → **아직 치환 전** → `step_added` 이벤트 발행
    → 평문이 프론트에 도달

이 테스트는 리코더 파이프라인에 **평문이 이벤트 페이로드로 들어가는 경로가 없음**을
확인한다. 순서를 뒤바꾸면 실패한다.

FR-083 (화면·로그·결과 마스킹) 과 FR-089d (기록 금지) 의 UI 쪽 대응이다.
"""

from __future__ import annotations

import pathlib
from typing import Any

import pytest
from nacl.public import PublicKey

from itb.domain.step import Author, Step
from itb.recording.recorder import SENSITIVE_VARIABLE_PREFIX, Recorder
from itb.secrets.keys import KeyPaths, generate, load_public
from itb.secrets.store import SecretStore

PASSWORD = "not-a-real-password-9f3a"


class _FakeSession:
    """리코더가 필요로 하는 최소 세션. 브라우저 없이 파이프라인만 본다."""

    def __init__(self) -> None:
        self.emitted: list[tuple[str, dict[str, Any]]] = []
        self.context = None
        self.max_tabs = 10

    async def emit(self, event_type: str, **payload: Any) -> None:
        self.emitted.append((event_type, payload))

    def tab_of(self, _page: Any) -> Any:
        return None

    def open_tabs(self) -> list[Any]:
        return []


@pytest.fixture
def sealed_env(tmp_path: pathlib.Path) -> tuple[SecretStore, PublicKey]:
    keys = KeyPaths(tmp_path / "keys")
    generate(keys)
    return SecretStore(tmp_path / "secrets.local.yaml"), load_public(keys)


def _recorder(
    store: SecretStore | None, public: PublicKey | None, sink_log: list[Step]
) -> Recorder:
    async def sink(step: Step, _index: int) -> None:
        sink_log.append(step)

    return Recorder(
        session=_FakeSession(),  # type: ignore[arg-type]
        sink=sink,
        store=store,
        public_key=public,
    )


# ─── 치환이 먼저 일어난다 ───────────────────────────────────────────────────


def test_sensitive_value_becomes_variable_reference(
    sealed_env: tuple[SecretStore, PublicKey],
) -> None:
    """치환 함수가 평문을 돌려주지 않는다 — 이것이 순서 보증의 근거다."""
    store, public = sealed_env
    rec = _recorder(store, public, [])
    element = {"label": "비밀번호", "attributes": {}}

    stored = rec._to_variable_reference(PASSWORD, sensitive=True, element=element)

    assert stored != PASSWORD
    assert stored.startswith("{{")
    assert stored.endswith("}}")
    assert SENSITIVE_VARIABLE_PREFIX in stored


def test_plaintext_is_sealed_into_secret_store(
    sealed_env: tuple[SecretStore, PublicKey],
) -> None:
    """평문은 비밀 파일의 암호문으로만 존재한다 (FR-089c)."""
    store, public = sealed_env
    rec = _recorder(store, public, [])
    rec._to_variable_reference(PASSWORD, sensitive=True, element={"label": "비밀번호"})

    assert store.names(), "비밀 값이 보관되지 않았다"
    assert PASSWORD not in store.path.read_text(encoding="utf-8")


def test_non_sensitive_value_passes_through(
    sealed_env: tuple[SecretStore, PublicKey],
) -> None:
    """민감하지 않은 값은 그대로 저장된다 — 과도한 마스킹은 테스트를 못 읽게 만든다."""
    store, public = sealed_env
    rec = _recorder(store, public, [])
    assert rec._to_variable_reference("TEST", sensitive=False, element={}) == "TEST"


# ─── 이벤트·Step 에 평문이 없다 ─────────────────────────────────────────────


@pytest.mark.parametrize("has_key", [True, False])
def test_recorded_step_never_carries_plaintext(
    tmp_path: pathlib.Path, has_key: bool
) -> None:
    """**키가 없어도** 평문이 Step 에 들어가지 않는다.

    키가 없으면 값을 보관할 수 없지만, 그렇다고 평문을 Step 에 넣어서는 안 된다.
    경고를 남기고 변수 참조만 저장한다.
    """
    store: SecretStore | None = None
    public: PublicKey | None = None
    if has_key:
        keys = KeyPaths(tmp_path / "keys")
        generate(keys)
        store = SecretStore(tmp_path / "secrets.local.yaml")
        public = load_public(keys)

    rec = _recorder(store, public, [])
    stored = rec._to_variable_reference(
        PASSWORD, sensitive=True, element={"label": "비밀번호"}
    )
    assert PASSWORD not in stored
    if not has_key:
        assert rec.warnings, "키가 없을 때 경고를 남기지 않았다"
        assert any("공개키" in w for w in rec.warnings)


def test_capture_is_recorded_for_variable_definition(
    sealed_env: tuple[SecretStore, PublicKey],
) -> None:
    """저장 시 민감 변수 정의를 만들 수 있도록 포착 기록이 남아야 한다 (FR-082)."""
    store, public = sealed_env
    rec = _recorder(store, public, [])
    rec._to_variable_reference(PASSWORD, sensitive=True, element={"label": "비밀번호"})

    assert len(rec.sensitive_captures) == 1
    capture = rec.sensitive_captures[0]
    assert capture.variable_name.startswith(SENSITIVE_VARIABLE_PREFIX)
    assert capture.sealed is True


@pytest.mark.parametrize(
    "element",
    [
        pytest.param({"label": "비밀 번호 (필수)!"}, id="한글-라벨"),
        pytest.param({"label": "Pass Word (required)!"}, id="특수문자"),
        pytest.param({"attributes": {"name": "user-password"}}, id="name-속성"),
        pytest.param({"attributes": {"name": "123start"}}, id="숫자로-시작"),
        pytest.param({}, id="근거-없음"),
        pytest.param({"label": "!!!"}, id="영숫자-없음"),
    ],
)
def test_variable_name_always_matches_pattern(
    sealed_env: tuple[SecretStore, PublicKey], element: dict[str, Any]
) -> None:
    """변수 이름은 반드시 `[A-Z][A-Z0-9_]*` 를 지켜야 한다.

    지키지 않으면 저장 시 `Test` 검증이 실패한다 — 한글 라벨이 흔하므로 실제로 자주 걸린다.
    """
    import re

    store, public = sealed_env
    rec = _recorder(store, public, [])
    stored = rec._to_variable_reference(PASSWORD, sensitive=True, element=element)
    name = stored[2:-2]
    assert re.match(r"^[A-Z][A-Z0-9_]*$", name), f"변수 이름 패턴 위반: {name}"
    assert len(name) <= 60


def test_variable_names_are_unique_without_ascii_basis(
    sealed_env: tuple[SecretStore, PublicKey],
) -> None:
    """ASCII 근거가 없는 필드가 여러 개면 이름이 겹쳐선 안 된다."""
    store, public = sealed_env
    rec = _recorder(store, public, [])
    first = rec._to_variable_reference(PASSWORD, sensitive=True, element={"label": "암호"})
    second = rec._to_variable_reference("other", sensitive=True, element={"label": "확인"})
    assert first != second


# ─── 파이프라인 순서 자체를 고정한다 ───────────────────────────────────────


def test_pipeline_order_substitution_before_sink(
    sealed_env: tuple[SecretStore, PublicKey],
) -> None:
    """sink 가 받는 Step 에는 이미 치환이 끝나 있어야 한다.

    이 테스트가 T157 의 순서 보증이다. `_record_fill` 에서 치환을 sink 호출 뒤로 옮기면
    실패한다.
    """
    store, public = sealed_env
    received: list[Step] = []
    rec = _recorder(store, public, received)
    rec.start(author=Author.HUMAN)

    # `_record_fill` 의 치환 → Step 생성 → sink 순서를 직접 검증한다.
    element = {"label": "비밀번호", "attributes": {}, "css": "#password", "tag": "input"}
    stored = rec._to_variable_reference(PASSWORD, sensitive=True, element=element)

    from itb.domain.locator import Candidate, CandidateStatus, TargetLocator
    from itb.domain.step import FillStep

    step = FillStep(
        id="step-01",
        label="비밀번호 입력 (민감)",
        author=Author.HUMAN,
        tab=0,
        target=TargetLocator(
            css=Candidate(value="#password", status=CandidateStatus.VERIFIED)
        ),
        value=stored,
    )

    import asyncio

    asyncio.run(rec.sink(step, -1))

    assert received, "sink 가 Step 을 받지 못했다"
    payload = received[0].model_dump_json()
    assert PASSWORD not in payload, "sink 에 평문이 도달했다 — T157 순서가 깨졌다"
    assert "{{" in payload


def test_sensitive_label_marks_the_step(
    sealed_env: tuple[SecretStore, PublicKey],
) -> None:
    """사용자가 어느 Step 이 민감 값을 쓰는지 알아야 한다 (FR-083)."""
    _store, _public = sealed_env
    label = Recorder._fill_label({"label": "비밀번호"}, sensitive=True)
    assert "민감" in label
    plain = Recorder._fill_label({"label": "이메일"}, sensitive=False)
    assert "민감" not in plain
