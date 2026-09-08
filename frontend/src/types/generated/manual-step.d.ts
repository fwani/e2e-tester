/* eslint-disable */
/**
 * 이 파일은 backend/schema/*.schema.json 에서 자동 생성됐다. 손으로 고치지 마세요.
 * 권위 정의: backend/src/itb/domain/*.py (Pydantic v2)
 * 재생성: cd backend && uv run python -m itb.schema.export && cd ../frontend && npm run gen:types
 */

export type ManualStep = NavigateSpec | CloseTabSpec | AssertUrlSpec | AssertTextSpec;
export type Kind = "navigate";
export type Label = string | null;
export type Tab = number;
export type TimeoutMs = number | null;
export type Url = string;
export type Kind1 = "close_tab";
export type Label1 = string | null;
export type Tab1 = number;
export type TimeoutMs1 = number | null;
export type Kind2 = "assert_url";
export type Label2 = string | null;
export type MatchMode = "equals" | "contains";
export type Tab2 = number;
export type TimeoutMs2 = number | null;
export type Url1 = string;
export type Kind3 = "assert_text";
export type Label3 = string | null;
export type MatchMode1 = "equals" | "contains";
export type Tab3 = number;
export type TimeoutMs3 = number | null;
export type Value = string;

export interface NavigateSpec {
  kind: Kind;
  label: Label;
  tab: Tab;
  timeout_ms: TimeoutMs;
  url: Url;
}
export interface CloseTabSpec {
  kind: Kind1;
  label: Label1;
  tab: Tab1;
  timeout_ms: TimeoutMs1;
}
export interface AssertUrlSpec {
  kind: Kind2;
  label: Label2;
  match: MatchMode;
  tab: Tab2;
  timeout_ms: TimeoutMs2;
  url: Url1;
}
export interface AssertTextSpec {
  kind: Kind3;
  label: Label3;
  match: MatchMode1;
  tab: Tab3;
  timeout_ms: TimeoutMs3;
  value: Value;
}
