/* eslint-disable */
/**
 * 이 파일은 backend/schema/*.schema.json 에서 자동 생성됐다. 손으로 고치지 마세요.
 * 권위 정의: backend/src/itb/domain/*.py (Pydantic v2)
 * 재생성: cd backend && uv run python -m itb.schema.export && cd ../frontend && npm run gen:types
 */

/**
 * 오류가 "내가 고칠 수 있는 것"인지에 답한다 (003 EC-001).
 *
 * 값이 둘뿐인 것은 의도적이다. 목적이 "사용자가 할 일이 있는가"에 답하는 것이고
 * 답은 예/아니오 둘뿐이다. 판단이 서지 않는 오류는 ``BROKEN`` 이다 — 제품이 스스로를
 * 설명하지 못한 것이므로.
 */
export type Category = "blocked" | "broken";
export type ErrorCode =
  | "PROJECT_NOT_OPEN"
  | "PROJECT_ALREADY_EXISTS"
  | "PROJECT_NOT_FOUND"
  | "INVALID_PATH"
  | "PROJECT_IN_USE"
  | "PROJECT_MISMATCH"
  | "PROJECT_DELETE_FAILED"
  | "GROUP_NOT_FOUND"
  | "GROUP_ALREADY_EXISTS"
  | "GROUP_PREFIX_RESERVED"
  | "TEST_NOT_FOUND"
  | "TEST_IN_USE"
  | "TEST_DELETE_FAILED"
  | "TEST_DELETE_PARTIAL"
  | "TEST_MOVE_FAILED"
  | "TEST_MOVE_PARTIAL"
  | "STEP_LIST_EMPTY"
  | "DEFINITION_INVALID"
  | "DEFINITION_STALE"
  | "SESSION_NOT_FOUND"
  | "SESSION_ALREADY_ACTIVE"
  | "SESSION_LOST"
  | "NOT_PAUSED"
  | "CANNOT_RESUME_PAST_FAILURE"
  | "INVALID_TRANSITION"
  | "TAB_NOT_FOUND"
  | "TAB_LIMIT_REACHED"
  | "KEY_MISSING"
  | "KEY_ALREADY_EXISTS"
  | "PASSPHRASE_REQUIRED"
  | "PASSPHRASE_INVALID"
  | "DECRYPT_FAILED"
  | "FINGERPRINT_MISMATCH"
  | "SECRET_NOT_FOUND"
  | "STEP_FAILED"
  | "TARGET_UNREACHABLE"
  | "ELEMENT_NOT_READY"
  | "ELEMENT_AMBIGUOUS"
  | "AI_FAILED"
  | "STORAGE_WRITE_FAILED"
  | "PROMPT_NOT_FOUND"
  | "UPLOAD_REJECTED"
  | "UPLOAD_NOT_FOUND"
  | "EXPORT_FAILED"
  | "IMPORT_FILE_REJECTED"
  | "IMPORT_PLAN_NOT_FOUND"
  | "IMPORT_CAPACITY_EXCEEDED"
  | "IMPORT_FAILED"
  | "IMPORT_PARTIAL"
  | "DRAFT_NOT_FOUND"
  | "NOT_SUPPORTED"
  | "INTERNAL_ERROR";
export type Message = string;
export type NextAction = string;

export interface ErrorResponse {
  error: ErrorBody;
}
/**
 * 오류 하나. ``category`` 는 ``code`` 에서 자동으로 채워진다.
 */
export interface ErrorBody {
  category: Category;
  code: ErrorCode;
  detail?: Detail;
  message: Message;
  next_action: NextAction;
}
export interface Detail {
  [k: string]: unknown;
}
