"""오류 계약의 **유일한 권위 정의**. 헌법 Cross-language schema duty.

    { "error": {
        "code": "STEP_LIST_EMPTY",
        "category": "blocked",
        "message": "Step이 없어 저장할 수 없습니다.",
        "next_action": "브라우저에서 동작을 기록하거나 Step을 추가한 뒤 다시 저장하세요.",
        "detail": {}
    } }

여기서 JSON Schema 를 내보내고 프론트엔드는 그것으로 TypeScript 타입을 생성한다
(`itb.schema.export` → `backend/schema/error-response.schema.json`). 프론트엔드가
`ErrorCode` 목록을 손으로 복제하던 것을 이 파이프라인이 대체한다 (003 EC-006).

**분류(`category`)는 호출부가 정하지 않는다.** `code` 로부터 `CATEGORY` 대응표를 통해
결정된다 — 손으로 적으면 코드와 어긋나고, 어긋난 분류는 분류가 없는 것보다 나쁘다.

메시지는 **사용자에게 그대로 보여줄 수 있어야 한다.** 내부 스택이나 경로를 노출하지 않고,
무엇을 해야 하는지 알려준다 (003 EC-005).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator


class Category(StrEnum):
    """오류가 "내가 고칠 수 있는 것"인지에 답한다 (003 EC-001).

    값이 둘뿐인 것은 의도적이다. 목적이 "사용자가 할 일이 있는가"에 답하는 것이고
    답은 예/아니오 둘뿐이다. 판단이 서지 않는 오류는 ``BROKEN`` 이다 — 제품이 스스로를
    설명하지 못한 것이므로.
    """

    BLOCKED = "blocked"
    """제품이 규칙에 따라 **의도적으로 거절**했다. 사용자가 고쳐 다시 하면 된다."""

    BROKEN = "broken"
    """제품이 **처리하지 못했다**. 사용자가 할 수 있는 일이 없다."""


class ErrorCode(StrEnum):
    # 프로젝트
    PROJECT_NOT_OPEN = "PROJECT_NOT_OPEN"
    PROJECT_ALREADY_EXISTS = "PROJECT_ALREADY_EXISTS"
    PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"
    INVALID_PATH = "INVALID_PATH"
    PROJECT_IN_USE = "PROJECT_IN_USE"
    """실행 중인 세션이 있어 프로젝트를 삭제할 수 없다 (012 FR-417).

    ``SESSION_ALREADY_ACTIVE`` 와 갈라 두는 이유는 **사용자가 할 일이 다르기 때문**이다.
    그쪽은 "이 테스트가 이미 실행 중" 이라 기다리거나 그 실행을 보면 되고, 이것은
    "브라우저를 먼저 중지해야 지울 수 있다" 다.
    """
    PROJECT_DELETE_FAILED = "PROJECT_DELETE_FAILED"
    """프로젝트를 휴지통으로 옮기지 못했다 (012 FR-414).

    **이 오류를 받은 사용자의 프로젝트는 원래 자리에 그대로 있다.** 이동이 실패하면
    레지스트리를 건드리지 않기 때문이다. 그 사실이 메시지에 반드시 들어가야 한다 —
    실패 후 사용자가 가장 먼저 하는 질문이 "내 테스트는 어떻게 됐나" 다.

    ``STORAGE_WRITE_FAILED`` 로 대신할 수 없다. 그쪽은 파일을 쓰다 실패한 것이고
    이것은 디렉터리를 옮기다 실패한 것이라, 사용자가 확인할 것(권한 · 남은 공간 · 볼륨)이
    다르다.
    """

    # 테스트 그룹 (013)
    GROUP_NOT_FOUND = "GROUP_NOT_FOUND"
    GROUP_ALREADY_EXISTS = "GROUP_ALREADY_EXISTS"
    """접두어나 이름이 겹친다 (013 FR-442).

    둘 다 프로젝트 안에서 고유해야 한다 — 이름이 겹치면 사용자가 어느 쪽에 넣었는지 알 수
    없고, 접두어가 겹치면 식별자가 어느 그룹인지 가리키지 못한다.
    """
    GROUP_PREFIX_RESERVED = "GROUP_PREFIX_RESERVED"
    """`TC` 는 그룹 없음이 쓴다 (013 FR-445a).

    기존 테스트가 전부 `TC-###` 이므로, 새 그룹이 `TC` 를 쓰면 그룹에 넣은 적 없는 테스트가
    그 그룹에 나타난다.
    """

    # 테스트
    TEST_NOT_FOUND = "TEST_NOT_FOUND"
    TEST_IN_USE = "TEST_IN_USE"
    """실행 중인 세션이 있어 지우거나 옮길 수 없다 (013 FR-433).

    `SESSION_ALREADY_ACTIVE` 와 갈라 두는 이유는 **사용자가 할 일이 다르기 때문**이다.
    그쪽은 "이 테스트가 이미 실행 중" 이라 기다리거나 그 실행을 보면 되고, 이것은
    "브라우저를 먼저 중지해야 정리할 수 있다" 다.
    """
    TEST_DELETE_FAILED = "TEST_DELETE_FAILED"
    """휴지통으로 옮기지 못했고 **되돌렸다** (013 FR-432).

    이 오류를 받은 사용자의 테스트는 **전부 원래 자리에 있다.** 요청 전과 같다는 뜻이며,
    그 사실이 안내에 반드시 들어가야 한다 — 실패 후 사용자가 가장 먼저 하는 질문이
    "내 테스트는 어떻게 됐나" 다.
    """
    TEST_DELETE_PARTIAL = "TEST_DELETE_PARTIAL"
    """옮기다 실패했고 **되돌리지도 못했다** (013 contracts/api-contract.md §3).

    `TEST_DELETE_FAILED` 와 **반드시 갈라야 한다.** 그쪽은 아무것도 하지 않은 것과 같지만
    이쪽은 일부가 휴지통에 남아 있다 — 사용자가 확인할 자리가 있다는 뜻이고, 할 일이 다르다.

    파일 시스템에는 여러 경로에 걸친 원자적 연산이 없다. 여기서 보장하는 것은 **모든 자산이
    휴지통 아니면 원래 자리에 있다** 이며, 파괴는 어느 경로에서도 일어나지 않는다. 그 사실을
    조용히 통과시키지 않으려고 코드를 가른다.
    """
    TEST_MOVE_FAILED = "TEST_MOVE_FAILED"
    """그룹 이동에 실패했고 되돌렸다 (013 FR-444b)."""
    STEP_LIST_EMPTY = "STEP_LIST_EMPTY"
    DEFINITION_INVALID = "DEFINITION_INVALID"
    DEFINITION_STALE = "DEFINITION_STALE"
    """편집을 시작한 뒤 정의 파일이 밖에서 바뀌었다 (006 FR-209).

    ``DEFINITION_INVALID`` 와 갈라 두는 이유는 **사용자가 할 일이 다르기 때문**이다.
    ``DEFINITION_INVALID`` 는 내 편집이 잘못된 것이고, 이것은 내 편집은 멀쩡한데 바탕이
    바뀐 것이다. 같은 코드로 내보내면 사용자는 멀쩡한 편집을 고치려 들고, 고칠 것이 없어
    헤맨다 — ``ELEMENT_NOT_READY`` 를 ``STEP_FAILED`` 와 갈라 둔 것과 같은 판단이다.
    """

    # 세션
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    SESSION_ALREADY_ACTIVE = "SESSION_ALREADY_ACTIVE"
    SESSION_LOST = "SESSION_LOST"
    NOT_PAUSED = "NOT_PAUSED"
    CANNOT_RESUME_PAST_FAILURE = "CANNOT_RESUME_PAST_FAILURE"
    """실패한 Step 앞에서 재개를 요청했다 (005 FR-136).

    조용히 건너뛰면 화면은 「완료」라고 말하고 저장된 결과는 실패인 상태가 된다 (U-05).
    """

    INVALID_TRANSITION = "INVALID_TRANSITION"
    TAB_NOT_FOUND = "TAB_NOT_FOUND"
    TAB_LIMIT_REACHED = "TAB_LIMIT_REACHED"

    # 비밀 값·키
    KEY_MISSING = "KEY_MISSING"
    KEY_ALREADY_EXISTS = "KEY_ALREADY_EXISTS"
    PASSPHRASE_REQUIRED = "PASSPHRASE_REQUIRED"
    PASSPHRASE_INVALID = "PASSPHRASE_INVALID"
    DECRYPT_FAILED = "DECRYPT_FAILED"
    FINGERPRINT_MISMATCH = "FINGERPRINT_MISMATCH"
    SECRET_NOT_FOUND = "SECRET_NOT_FOUND"

    # 실행 — Step 을 수행하지 못했다 (003 AP-031·AP-033, 004 FR-120·FR-123)
    STEP_FAILED = "STEP_FAILED"
    TARGET_UNREACHABLE = "TARGET_UNREACHABLE"
    ELEMENT_NOT_READY = "ELEMENT_NOT_READY"
    """대기 예산 안에 어느 후보도 요소 하나를 가리키지 못했다 (004 FR-120).

    ``STEP_FAILED`` 와 갈라 두는 이유는 **사용자가 할 일이 다르기 때문**이다. 후보가
    애초에 없는 것은 정의 문제라 기다려도 달라지지 않지만, 이것은 대상 화면이 느린
    것이고 예산을 늘리면 통과한다. 두 경우를 같은 코드로 내보내면 사용자는 멀쩡한
    정의를 고치려 들고, 고칠 것이 없어 헤맨다.
    """

    ELEMENT_AMBIGUOUS = "ELEMENT_AMBIGUOUS"
    """대기 예산 안에 여러 요소만 매칭됐다 (004 FR-120).

    **자동으로 하나를 고르지 않는다.** 첫 번째를 골라 진행하면 잘못된 요소에 대해
    테스트가 통과할 수 있고, 그것은 실패보다 나쁘다 — 다음 회귀를 못 잡는다.
    004 이전 코드가 실제로 그렇게 동작했다 (research R2 실측).
    """

    # 외부 환경 (003 AP-032·AP-042)
    AI_FAILED = "AI_FAILED"
    STORAGE_WRITE_FAILED = "STORAGE_WRITE_FAILED"

    # 브라우저 요구·업로드 (010 FR-337a·FR-340)
    PROMPT_NOT_FOUND = "PROMPT_NOT_FOUND"
    """브라우저 요구가 이미 처리됐거나 이 세션의 것이 아니다 (010 FR-340).

    `SESSION_NOT_FOUND` 와 갈라 두는 이유는 **사용자가 할 일이 다르기 때문**이다. 세션은
    살아 있고 요구 하나만 사라진 것이므로, 사용자는 화면을 떠날 것이 아니라 다음 요구를
    기다리면 된다. 같은 코드로 내보내면 화면은 「세션이 끝났습니다」를 띄우고 사용자는
    멀쩡한 세션을 버린다.
    """

    UPLOAD_REJECTED = "UPLOAD_REJECTED"
    """올린 파일이 상한을 넘었다 (010 FR-337a).

    크기와 개수를 한 코드로 두는 이유는 사용자가 할 일이 같기 때문이다 — 더 작은 파일을
    고르거나, 세션을 정리하고 다시 시작한다. 무엇이 상한이었는지는 `detail` 이 말한다.

    **자르지 않고 거절한다.** 잘린 파일을 대상 페이지가 받으면 그 실패는 원인을 드러내지
    않는다.
    """

    UPLOAD_NOT_FOUND = "UPLOAD_NOT_FOUND"
    """지정한 파일을 이 세션에서 찾을 수 없다 (010 FR-337b·FR-340).

    세션이 끝나면 올린 파일이 정리되므로(FR-337b), 오래된 화면이 남은 식별자를 보내면
    여기로 온다. 다른 세션의 식별자도 마찬가지다 — 저장소가 세션 단위로 나뉘어 있어
    조회 자체가 실패한다.
    """

    # 미지원
    NOT_SUPPORTED = "NOT_SUPPORTED"

    # 내부 — 처리되지 않은 오류 (003 EC-003)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    """처리되지 않은 오류 **전용**.

    003 이전에는 최종 처리기가 ``DEFINITION_INVALID`` 를 썼다. 그 코드는 사용자가
    잘못된 정의를 넣어 **정상적으로 거부당했을 때**도 쓰인다. 하나의 코드가 두 분류에
    걸치면 분류 자체가 성립하지 않으므로 코드를 나눈다.
    """


# ─── 코드 → 분류 전수 대응표 (003 EC-001·RG-104-1) ─────────────────────────
#
# 모든 ErrorCode 가 정확히 하나의 분류를 가진다. 코드를 추가하고 여기에 넣지 않으면
# tests/abnormal/test_error_contract.py 가 실패한다.

CATEGORY: dict[ErrorCode, Category] = {
    # 프로젝트 — 사용자가 대상을 고르거나 만들면 된다
    ErrorCode.PROJECT_NOT_OPEN: Category.BLOCKED,
    ErrorCode.PROJECT_ALREADY_EXISTS: Category.BLOCKED,
    ErrorCode.PROJECT_NOT_FOUND: Category.BLOCKED,
    ErrorCode.INVALID_PATH: Category.BLOCKED,
    ErrorCode.PROJECT_IN_USE: Category.BLOCKED,
    # `broken` 이 아니다. 이 저장소에서 `broken` 은 **처리되지 않은 오류** 하나뿐이고
    # (`INTERNAL_ERROR`, tests/abnormal/test_error_contract.py 가 세고 있다), 옮기기
    # 실패는 제품이 붙잡아 사유를 말한 정상 거부다. 사용자가 할 일도 있다 — 권한과
    # 남은 공간. `STORAGE_WRITE_FAILED` 가 같은 이유로 `blocked` 다.
    ErrorCode.PROJECT_DELETE_FAILED: Category.BLOCKED,
    # 테스트 그룹 (013) — 전부 정상 거부다. `BROKEN` 은 처리되지 않은 오류 하나뿐이다.
    ErrorCode.GROUP_NOT_FOUND: Category.BLOCKED,
    ErrorCode.GROUP_ALREADY_EXISTS: Category.BLOCKED,
    ErrorCode.GROUP_PREFIX_RESERVED: Category.BLOCKED,
    # 테스트 — 사용자가 내용을 고치면 된다
    ErrorCode.TEST_NOT_FOUND: Category.BLOCKED,
    # 013 — 제품이 붙잡아 사유를 말한 거부다. 사용자가 할 일이 있다.
    ErrorCode.TEST_IN_USE: Category.BLOCKED,
    ErrorCode.TEST_DELETE_FAILED: Category.BLOCKED,
    ErrorCode.TEST_DELETE_PARTIAL: Category.BLOCKED,
    ErrorCode.TEST_MOVE_FAILED: Category.BLOCKED,
    ErrorCode.STEP_LIST_EMPTY: Category.BLOCKED,
    ErrorCode.DEFINITION_INVALID: Category.BLOCKED,
    # 006 — 사용자가 두 선택(다시 읽기·덮어쓰기) 중 하나를 고르면 된다.
    ErrorCode.DEFINITION_STALE: Category.BLOCKED,
    # 세션 — 순서를 바꾸거나 기다리면 된다
    ErrorCode.SESSION_NOT_FOUND: Category.BLOCKED,
    ErrorCode.SESSION_ALREADY_ACTIVE: Category.BLOCKED,
    ErrorCode.NOT_PAUSED: Category.BLOCKED,
    ErrorCode.CANNOT_RESUME_PAST_FAILURE: Category.BLOCKED,
    ErrorCode.INVALID_TRANSITION: Category.BLOCKED,
    ErrorCode.TAB_NOT_FOUND: Category.BLOCKED,
    ErrorCode.TAB_LIMIT_REACHED: Category.BLOCKED,
    # 세션 상실 — 브라우저가 사라진 것은 대개 바깥 사정이다. 제품은 그것을 옮겨 전할 뿐이고
    # 사용자에게는 할 일이 있다(기록한 Step 을 저장하고 새 세션을 연다). 그래서 BLOCKED 다.
    # 제품이 스스로 브라우저를 잃은 경우는 그 지점에서 INTERNAL_ERROR 로 드러난다.
    ErrorCode.SESSION_LOST: Category.BLOCKED,
    # 비밀 값·키 — 사용자가 키·암호구를 다루면 된다
    ErrorCode.KEY_MISSING: Category.BLOCKED,
    ErrorCode.KEY_ALREADY_EXISTS: Category.BLOCKED,
    ErrorCode.PASSPHRASE_REQUIRED: Category.BLOCKED,
    ErrorCode.PASSPHRASE_INVALID: Category.BLOCKED,
    ErrorCode.DECRYPT_FAILED: Category.BLOCKED,
    ErrorCode.FINGERPRINT_MISMATCH: Category.BLOCKED,
    ErrorCode.SECRET_NOT_FOUND: Category.BLOCKED,
    # 실행 — 정의를 고치거나 대상 화면을 확인하면 된다. **제품이 깨진 것이 아니다.**
    # AP-031 이 이것을 직접 요구한다: 대상 쪽 사정에서 비롯된 실패를 제품 결함으로
    # 보이게 해서는 안 된다.
    ErrorCode.STEP_FAILED: Category.BLOCKED,
    ErrorCode.TARGET_UNREACHABLE: Category.BLOCKED,
    # 004 — 셋 다 BLOCKED 인 것은 의도적이다. 분류는 "내가 고칠 수 있는가"에만 답하고
    # (003 EC-001), 무엇을 할지는 code 와 next_action 이 말한다 (FR-123).
    ErrorCode.ELEMENT_NOT_READY: Category.BLOCKED,
    ErrorCode.ELEMENT_AMBIGUOUS: Category.BLOCKED,
    # 외부 환경 — 원인이 제품 밖에 있고, 사용자가 손댈 자리가 있다 (SESSION_LOST 와 같은
    # 판단이다). AI 는 다시 시도하거나 직접 이어받을 수 있고, 저장 실패는 공간·권한을
    # 확인하면 된다.
    ErrorCode.AI_FAILED: Category.BLOCKED,
    ErrorCode.STORAGE_WRITE_FAILED: Category.BLOCKED,
    # 010 브라우저 요구·업로드 — 셋 다 사용자가 할 일이 있다. 제품이 깨진 것이 아니다.
    ErrorCode.PROMPT_NOT_FOUND: Category.BLOCKED,
    ErrorCode.UPLOAD_REJECTED: Category.BLOCKED,
    ErrorCode.UPLOAD_NOT_FOUND: Category.BLOCKED,
    # 미지원 — 다른 방법을 쓰면 된다
    ErrorCode.NOT_SUPPORTED: Category.BLOCKED,
    # 내부 — 사용자가 할 수 있는 일이 없다
    ErrorCode.INTERNAL_ERROR: Category.BROKEN,
}


# ─── 코드 → 기본 다음 행동 (003 EC-004) ────────────────────────────────────
#
# 호출부가 상황에 맞는 문구로 덮어쓸 수 있다. 비어 있을 수는 없다.

NEXT_ACTION: dict[ErrorCode, str] = {
    ErrorCode.PROJECT_NOT_OPEN: "먼저 프로젝트를 열거나 새로 만드세요.",
    ErrorCode.PROJECT_ALREADY_EXISTS: "다른 이름을 쓰거나 기존 프로젝트를 여세요.",
    ErrorCode.PROJECT_NOT_FOUND: "경로를 확인하거나 목록에서 다른 프로젝트를 고르세요.",
    ErrorCode.INVALID_PATH: "프로젝트 폴더 안의 경로를 지정하세요.",
    ErrorCode.PROJECT_IN_USE: "실행 중인 브라우저를 먼저 중지한 뒤 다시 삭제하세요.",
    ErrorCode.PROJECT_DELETE_FAILED: (
        "프로젝트는 그대로 남아 있습니다. 저장 위치의 권한과 남은 공간을 확인하세요."
    ),
    ErrorCode.TEST_NOT_FOUND: "목록을 새로 고친 뒤 다시 고르세요. 이미 지워졌을 수 있습니다.",
    ErrorCode.TEST_IN_USE: "실행 중인 브라우저를 먼저 중지한 뒤 다시 시도하세요.",
    ErrorCode.TEST_DELETE_FAILED: (
        "테스트는 전부 원래 자리에 있습니다. 저장 위치의 권한과 남은 공간을 확인하세요."
    ),
    ErrorCode.TEST_DELETE_PARTIAL: (
        "일부가 휴지통에 남아 있습니다. 지워진 것은 없습니다. "
        "아래 자리를 확인한 뒤 목록을 새로 고치세요."
    ),
    ErrorCode.TEST_MOVE_FAILED: (
        "테스트는 전부 원래 그룹에 있습니다. 저장 위치의 권한과 남은 공간을 확인하세요."
    ),
    ErrorCode.GROUP_NOT_FOUND: "목록을 새로 고친 뒤 다시 고르세요. 이미 없어졌을 수 있습니다.",
    ErrorCode.GROUP_ALREADY_EXISTS: "다른 이름이나 접두어를 쓰세요.",
    ErrorCode.GROUP_PREFIX_RESERVED: "TC 는 그룹 없는 테스트가 씁니다. 다른 접두어를 쓰세요.",
    ErrorCode.STEP_LIST_EMPTY: "브라우저에서 동작을 기록하거나 Step을 추가한 뒤 다시 저장하세요.",
    ErrorCode.DEFINITION_INVALID: "표시된 항목을 규격에 맞게 고친 뒤 다시 시도하세요.",
    ErrorCode.DEFINITION_STALE: (
        "바뀐 내용을 확인한 뒤 다시 읽거나 내 편집으로 덮어쓸지 고르세요."
    ),
    ErrorCode.SESSION_NOT_FOUND: "세션이 이미 끝났습니다. 새 세션을 시작하세요.",
    ErrorCode.SESSION_ALREADY_ACTIVE: "진행 중인 세션을 끝내거나 그 세션으로 이동하세요.",
    ErrorCode.SESSION_LOST: "기록된 Step은 남아 있습니다. 저장한 뒤 새 세션을 시작하세요.",
    ErrorCode.NOT_PAUSED: "먼저 일시정지한 뒤 다시 시도하세요.",
    ErrorCode.CANNOT_RESUME_PAST_FAILURE: (
        "그 Step 을 고친 뒤 이어가거나, 그 Step 부터 다시 실행하세요."
    ),
    ErrorCode.INVALID_TRANSITION: "지금 가능한 동작 중에서 고르세요.",
    ErrorCode.TAB_NOT_FOUND: "탭 목록을 새로 고친 뒤 다시 고르세요. 이미 닫혔을 수 있습니다.",
    ErrorCode.TAB_LIMIT_REACHED: "쓰지 않는 탭을 닫은 뒤 다시 시도하세요.",
    ErrorCode.STEP_FAILED: (
        "대상 화면이 녹화 때와 같은지 확인하고, 다르면 그 Step의 대상을 다시 집으세요."
    ),
    ErrorCode.TARGET_UNREACHABLE: (
        "대상 사이트가 응답하는지 확인한 뒤 다시 실행하세요. 도구 문제가 아닙니다."
    ),
    # 004 — 시간 문제와 정의 문제의 안내가 정반대여야 한다. 위 STEP_FAILED 는 "대상을
    # 다시 집으세요" 라고 말하는데, 화면이 느렸을 뿐인 사용자에게 그 말을 하면 고칠 것이
    # 없는 정의를 들여다보게 만든다 (FR-122).
    ErrorCode.ELEMENT_NOT_READY: (
        "대상 화면이 느릴 수 있습니다. 실행 속도를 '느림'으로 낮춰 화면을 확인하거나, "
        "Step 상세에서 대기 시간을 늘린 뒤 그 Step부터 다시 실행하세요."
    ),
    ErrorCode.ELEMENT_AMBIGUOUS: (
        "이 식별 정보가 더 이상 요소 하나를 가리키지 않습니다. "
        "Step 상세에서 대상을 다시 집으세요."
    ),
    ErrorCode.AI_FAILED: (
        "다시 시도하거나 직접 이어받아 진행하세요. 그때까지 만들어진 Step은 남아 있습니다."
    ),
    ErrorCode.STORAGE_WRITE_FAILED: (
        "저장 공간과 폴더 권한을 확인한 뒤 다시 시도하세요. 직전 내용은 그대로 있습니다."
    ),
    ErrorCode.KEY_MISSING: "키 관리 화면에서 키 쌍을 먼저 만드세요.",
    ErrorCode.KEY_ALREADY_EXISTS: "기존 키를 쓰거나, 교체하려면 키 교체를 쓰세요.",
    ErrorCode.PASSPHRASE_REQUIRED: "키 관리 화면에서 암호구를 입력해 잠금을 해제하세요.",
    ErrorCode.PASSPHRASE_INVALID: "암호구를 다시 확인해 입력하세요.",
    ErrorCode.DECRYPT_FAILED: "이 값을 암호화한 키와 암호구가 맞는지 확인하세요.",
    ErrorCode.FINGERPRINT_MISMATCH: "이 값은 다른 키로 암호화됐습니다. 해당 키로 여세요.",
    ErrorCode.SECRET_NOT_FOUND: "비밀 값 화면에서 이 이름의 값을 먼저 등록하세요.",
    # 010 — 셋 다 **그 자리에서 할 수 있는 일**을 가리킨다. 화면을 떠나게 만들지 않는다.
    ErrorCode.PROMPT_NOT_FOUND: "그 요구는 이미 끝났습니다. 다음 요구를 기다리세요.",
    ErrorCode.UPLOAD_REJECTED: "더 작은 파일을 고르거나, 올린 파일을 정리한 뒤 다시 시도하세요.",
    ErrorCode.UPLOAD_NOT_FOUND: "파일을 다시 올린 뒤 지정하세요.",
    ErrorCode.NOT_SUPPORTED: "지원되는 다른 방법을 쓰세요.",
    ErrorCode.INTERNAL_ERROR: (
        "작업 내용은 그대로 있습니다. 화면을 새로 고쳐 이어서 진행하고, "
        "계속 발생하면 서버 로그와 함께 알려주세요."
    ),
}


class ErrorBody(BaseModel):
    """오류 하나. ``category`` 는 ``code`` 에서 자동으로 채워진다."""

    model_config = ConfigDict(extra="forbid")

    code: ErrorCode
    category: Category
    message: str
    next_action: str
    detail: dict[str, Any] = {}

    @model_validator(mode="before")
    @classmethod
    def _derive(cls, data: Any) -> Any:
        """``code`` 에서 ``category`` 를 채우고 ``next_action`` 의 기본값을 넣는다.

        ``category`` 는 호출부가 넘긴 값이 있어도 **대응표 값으로 덮어쓴다.** 이 필드의
        값은 계약이 정하는 것이지 호출부가 정하는 것이 아니다 (003 EC-002).
        """
        if not isinstance(data, dict):
            return data

        raw = data.get("code")
        try:
            code = ErrorCode(raw)
        except ValueError:
            return data  # 코드가 유효하지 않으면 pydantic 이 그 자체를 오류로 알린다

        out = dict(data)
        out["category"] = CATEGORY[code]
        if not out.get("next_action"):
            out["next_action"] = NEXT_ACTION[code]
        return out


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error: ErrorBody


def error_body(
    code: ErrorCode, message: str, *, next_action: str | None = None, **detail: Any
) -> dict[str, Any]:
    """계약 형태 오류 본문 하나. 요청 응답이든 실시간 통로든 같은 것을 쓴다 (003 EC-008)."""
    body = ErrorBody(code=code, message=message, next_action=next_action or "", detail=detail)
    return body.model_dump(mode="json")  # type: ignore[no-any-return]


def error_payload(
    code: ErrorCode, message: str, *, next_action: str | None = None, **detail: Any
) -> dict[str, Any]:
    """실시간 통로로 보내는 오류를 **요청 응답과 같은 본문**으로 만든다 (003 EC-008).

    화면은 요청 응답으로 온 오류와 실시간 통로로 온 오류를 같은 통로로 표시한다. 본문이
    다르면 한쪽에만 다음 행동이 붙고, 그 차이는 사용자가 겪을 때까지 드러나지 않는다.

    ``reason`` 을 함께 싣는다 — 001·002 의 화면과 검증이 그 이름을 읽는다. 새 소비자는
    ``error`` 를 읽으면 된다.
    """
    return {
        "error": error_body(code, message, next_action=next_action, **detail),
        "reason": message,
    }
