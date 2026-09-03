/* eslint-disable */
/**
 * 이 파일은 backend/schema/*.schema.json 에서 자동 생성됐다. 손으로 고치지 마세요.
 * 권위 정의: backend/src/itb/domain/*.py (Pydantic v2)
 * 재생성: cd backend && uv run python -m itb.schema.export && cd ../frontend && npm run gen:types
 */

export type AiInstruction = string | null;
/**
 * 작성 방식. **테스트를 시작한 방식**으로 결정하며 이후 바뀌지 않는다 (FR-002a).
 */
export type AuthoringMode = "record" | "ai";
export type BrowserKind = "chromium";
export type CreatedAt = string;
export type DslVersion = number;
export type Id = string;
export type Name = string;
export type StartUrl = string;
/**
 * @minItems 1
 */
export type Steps = [
  ClickStep | FillStep | SelectStep | NavigateStep | AssertionStep | CloseTabStep,
  ...(ClickStep | FillStep | SelectStep | NavigateStep | AssertionStep | CloseTabStep)[]
];
export type Author = "human" | "ai";
export type FrameUrl = string | null;
export type Id1 = string;
export type Label = string;
export type Tab = number;
export type AccessibleName = string | null;
/**
 * 기록 시점 검증 결과. research R4 실측으로 ``AMBIGUOUS`` 가 추가됐다.
 */
export type CandidateStatus = "verified" | "ambiguous" | "unverified" | "not_collected";
export type Value = string;
export type Role = string | null;
export type Name1 = string;
export type Value1 = string;
export type Tag = string | null;
export type TimeoutMs = number;
export type Type = "click";
export type Author1 = "human" | "ai";
export type FrameUrl1 = string | null;
export type Id2 = string;
export type Label1 = string;
export type Tab1 = number;
export type TimeoutMs1 = number;
export type Type1 = "fill";
export type Value2 = string;
export type Author2 = "human" | "ai";
export type FrameUrl2 = string | null;
export type Id3 = string;
export type Label2 = string;
export type Tab2 = number;
export type TimeoutMs2 = number;
export type Type2 = "select";
export type Value3 = string;
export type Author3 = "human" | "ai";
export type FrameUrl3 = string | null;
export type Id4 = string;
export type Label3 = string;
export type Tab3 = number;
export type TimeoutMs3 = number;
export type Type3 = "navigate";
export type Url = string;
export type AssertionKind = "visible" | "hidden" | "text" | "url";
export type MatchMode = "equals" | "contains";
export type Value4 = string | null;
export type Author4 = "human" | "ai";
export type FrameUrl4 = string | null;
export type Id5 = string;
export type Label4 = string;
export type Tab4 = number;
export type TimeoutMs4 = number;
export type Type4 = "assertion";
export type Author5 = "human" | "ai";
export type FrameUrl5 = string | null;
export type Id6 = string;
export type Label5 = string;
export type Tab5 = number;
export type TimeoutMs5 = number;
export type Type5 = "close_tab";
export type UpdatedAt = string;
export type Name2 = string;
export type Sensitive = boolean;
export type Value5 = string | null;
export type Variables = Variable[];

/**
 * 하나의 테스트 시나리오. `tests/` 아래 YAML 파일 하나에 대응한다.
 */
export interface Test {
  ai_instruction: AiInstruction;
  authoring_mode: AuthoringMode;
  browser: BrowserKind;
  created_at: CreatedAt;
  dsl_version: DslVersion;
  id: Id;
  name: Name;
  start_url: StartUrl;
  steps: Steps;
  updated_at: UpdatedAt;
  variables: Variables;
}
export interface ClickStep {
  author: Author;
  frame_url: FrameUrl;
  id: Id1;
  label: Label;
  tab: Tab;
  target: TargetLocator;
  timeout_ms: TimeoutMs;
  type: Type;
}
/**
 * 한 요소에 대한 식별 후보 묶음.
 *
 * **불변식**: 후보가 하나도 없는 ``TargetLocator`` 는 유효하지 않다.
 * 최소한 ``css`` 는 항상 수집된다.
 */
export interface TargetLocator {
  accessible_name: AccessibleName;
  css: Candidate | null;
  label: Candidate | null;
  role: Role;
  role_status: CandidateStatus | null;
  stable_attr: StableAttr | null;
  tag: Tag;
  test_id: Candidate | null;
  text: Candidate | null;
}
/**
 * 식별 후보 하나.
 */
export interface Candidate {
  status: CandidateStatus;
  value: Value;
}
/**
 * `[name="value"]` 형태로 쓰는 안정적 속성.
 */
export interface StableAttr {
  name: Name1;
  status: CandidateStatus;
  value: Value1;
}
export interface FillStep {
  author: Author1;
  frame_url: FrameUrl1;
  id: Id2;
  label: Label1;
  tab: Tab1;
  target: TargetLocator;
  timeout_ms: TimeoutMs1;
  type: Type1;
  value: Value2;
}
export interface SelectStep {
  author: Author2;
  frame_url: FrameUrl2;
  id: Id3;
  label: Label2;
  tab: Tab2;
  target: TargetLocator;
  timeout_ms: TimeoutMs2;
  type: Type2;
  value: Value3;
}
export interface NavigateStep {
  author: Author3;
  frame_url: FrameUrl3;
  id: Id4;
  label: Label3;
  tab: Tab3;
  timeout_ms: TimeoutMs3;
  type: Type3;
  url: Url;
}
export interface AssertionStep {
  assertion: Assertion;
  author: Author4;
  frame_url: FrameUrl4;
  id: Id5;
  label: Label4;
  tab: Tab4;
  timeout_ms: TimeoutMs4;
  type: Type4;
}
/**
 * 검증 Step 의 조건.
 */
export interface Assertion {
  kind: AssertionKind;
  match: MatchMode;
  target: TargetLocator | null;
  value: Value4;
}
/**
 * 탭 닫기 (FR-030c). 대상은 공통 ``tab`` 필드가 가리킨다.
 */
export interface CloseTabStep {
  author: Author5;
  frame_url: FrameUrl5;
  id: Id6;
  label: Label5;
  tab: Tab5;
  timeout_ms: TimeoutMs5;
  type: Type5;
}
/**
 * 테스트 안에서 값을 대신하는 이름.
 */
export interface Variable {
  name: Name2;
  sensitive: Sensitive;
  value: Value5;
}
