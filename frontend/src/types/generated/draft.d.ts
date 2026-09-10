/* eslint-disable */
/**
 * 이 파일은 backend/schema/*.schema.json 에서 자동 생성됐다. 손으로 고치지 마세요.
 * 권위 정의: backend/src/itb/domain/*.py (Pydantic v2)
 * 재생성: cd backend && uv run python -m itb.schema.export && cd ../frontend && npm run gen:types
 */

export type Actor = string | null;
export type CreatedAt = string;
export type Description = string | null;
export type DesiredTestId = string | null;
export type DraftId = string;
export type Expectation = string | null;
export type GroupPrefix = string;
export type Name = string;
export type Procedure = string | null;
export type FileName = string;
export type Row = number;
export type SheetName = string;

/**
 * 스프레드시트 행 하나에서 온, 아직 스텝이 없는 테스트의 의도.
 *
 * ``drafts/<draft_id>-<slug>.yaml`` 파일 하나에 대응한다. `tests/` 와 디렉터리를 나눈 것은
 * 벽을 정규식이 아니라 파일시스템이 되게 하려는 것이다 (014 research R7).
 */
export interface Draft {
  actor: Actor;
  created_at: CreatedAt;
  description: Description;
  desired_test_id: DesiredTestId;
  draft_id: DraftId;
  expectation: Expectation;
  group_prefix: GroupPrefix;
  name: Name;
  procedure: Procedure;
  source: DraftSource;
}
/**
 * 이 초안이 어느 파일의 어느 시트 몇 행에서 왔는가.
 *
 * 사용자가 원본 설계서를 되짚을 수 있어야 한다. 초안이 스무 건 쌓였을 때 "이건 어디서
 * 온 거지"에 답하지 못하면 목록은 정체 모를 할 일 더미가 된다.
 */
export interface DraftSource {
  file_name: FileName;
  row: Row;
  sheet_name: SheetName;
}
