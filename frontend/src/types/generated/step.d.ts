/* eslint-disable */
/**
 * 이 파일은 backend/schema/*.schema.json 에서 자동 생성됐다. 손으로 고치지 마세요.
 * 권위 정의: backend/src/itb/domain/*.py (Pydantic v2)
 * 재생성: cd backend && uv run python -m itb.schema.export && cd ../frontend && npm run gen:types
 */

export type Step =
  | ClickStep
  | FillStep
  | SelectStep
  | NavigateStep
  | AssertionStep
  | CloseTabStep
  | HoverStep
  | DragStep
  | UploadStep
  | PressStep;
export type Author = "human" | "ai";
export type FrameUrl = string | null;
export type Id = string;
export type Label = string;
export type Tab = number;
export type AccessibleName = string | null;
/**
 * 기록 시점 검증 결과. research R4 실측으로 ``AMBIGUOUS`` 가 추가됐다.
 */
export type CandidateStatus = "verified" | "ambiguous" | "unverified" | "not_collected";
export type Value = string;
export type Role = string | null;
export type Name = string;
export type Value1 = string;
export type Tag = string | null;
export type TimeoutMs = number;
export type Type = "click";
export type Author1 = "human" | "ai";
export type FrameUrl1 = string | null;
export type Id1 = string;
export type Label1 = string;
export type Tab1 = number;
export type TimeoutMs1 = number;
export type Type1 = "fill";
export type Value2 = string;
export type Author2 = "human" | "ai";
export type FrameUrl2 = string | null;
export type Id2 = string;
export type Label2 = string;
export type Tab2 = number;
export type TimeoutMs2 = number;
export type Type2 = "select";
export type Value3 = string;
export type Author3 = "human" | "ai";
export type FrameUrl3 = string | null;
export type Id3 = string;
export type Label3 = string;
export type Tab3 = number;
export type TimeoutMs3 = number;
export type Type3 = "navigate";
export type Url = string;
export type AssertionKind = "visible" | "hidden" | "text" | "url" | "value" | "enabled" | "disabled";
export type MatchMode = "equals" | "contains" | "not_equals" | "not_contains";
export type Value4 = string | null;
export type Author4 = "human" | "ai";
export type FrameUrl4 = string | null;
export type Id4 = string;
export type Label4 = string;
export type Observed = string;
export type RecordedAt = string;
export type Truncated = boolean;
export type Tab4 = number;
export type TimeoutMs4 = number;
export type Type4 = "assertion";
export type Author5 = "human" | "ai";
export type FrameUrl5 = string | null;
export type Id5 = string;
export type Label5 = string;
export type Tab5 = number;
export type TimeoutMs5 = number;
export type Type5 = "close_tab";
export type Author6 = "human" | "ai";
export type FrameUrl6 = string | null;
export type Id6 = string;
export type Label6 = string;
export type Tab6 = number;
export type TimeoutMs6 = number;
export type Type6 = "hover";
export type Author7 = "human" | "ai";
export type FrameUrl7 = string | null;
export type Id7 = string;
export type Label7 = string;
export type Tab7 = number;
export type TimeoutMs7 = number;
export type Type7 = "drag";
export type Author8 = "human" | "ai";
export type FileName = string;
export type FrameUrl8 = string | null;
export type Id8 = string;
export type Label8 = string;
export type Tab8 = number;
export type TimeoutMs8 = number;
export type Type8 = "upload";
export type Author9 = "human" | "ai";
export type FrameUrl9 = string | null;
export type Id9 = string;
/**
 * 키 입력 Step 이 누를 수 있는 키 (023 FR-052·FR-053).
 *
 * ## 왜 자유 문자열이 아닌가
 *
 * | | 자유 문자열 | 열거형 |
 * |---|---|---|
 * | 오타 (`enter` 대 `Enter`) | **실행 시점까지 숨는다** | 정의 시점에 거절 |
 * | AI 가 없는 키를 지어내면 | 실행 시점 오류 | 도구 호출이 즉시 거절 |
 * | 생성된 코드 | **검증 안 된 문자열이 그대로 나간다** | 목록에 있는 값만 |
 *
 * 세 번째 줄에서 갈렸다. 헌법의 보안 제약이 「생성된 Playwright 코드는 생성 중
 * **데이터로 다루어야** 하며 페이지에서 온 문자열의 이스케이프되지 않은 결합으로
 * 만들어서는 안 된다」고 못박는다. 검증되지 않은 키 이름이 생성기로 들어가는 경로를
 * 열지 않는다 (023 research R12).
 *
 * ## 왜 넷뿐인가
 *
 * ``ENTER``·``SPACE`` 는 사용자가 요구한 것이고, ``TAB``·``ESCAPE`` 는 같은
 * 「확정·이동·취소」 계열이면서 클릭으로 대신할 수 없다. 화살표는 선택 Step 이,
 * Backspace 는 입력 Step 이 담당한다. 문자 키는 입력 Step 이 담당하며, 키로 쪼개면
 * 녹화가 피해 온 IME 조합 문제가 되돌아온다.
 *
 * **넓히는 것은 값을 더하는 일이다.** 좁게 시작하는 것이 나중을 막지 않는다.
 *
 * ## 값이 표준 도구의 키 이름과 같은 철자다
 *
 * 변환표를 두지 않기 위해서다. 표가 있으면 어느 쪽이 권위인지 매번 판단해야 하고 값을
 * 더할 때마다 두 곳을 고쳐야 한다 (023 contracts/export-mapping.md §6).
 */
export type PressKey = "Enter" | "Space" | "Tab" | "Escape";
export type Label9 = string;
export type Tab9 = number;
export type TimeoutMs9 = number;
export type Type9 = "press";

export interface ClickStep {
  author: Author;
  frame_url: FrameUrl;
  id: Id;
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
  name: Name;
  status: CandidateStatus;
  value: Value1;
}
export interface FillStep {
  author: Author1;
  frame_url: FrameUrl1;
  id: Id1;
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
  id: Id2;
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
  id: Id3;
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
  id: Id4;
  label: Label4;
  mismatch: AuthoringMismatch | null;
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
 * 작성 시점에 이 검증이 통과하지 않았다는 기록 (020 FR-005·FR-008).
 *
 * ## 이것이 있는 이유 — 정의는 제품 동작의 사본이 아니다
 *
 * 지시문이 「저장하면 `저장되었습니다` 가 뜬다」를 요구했는데 제품이 `처리 완료` 를
 * 띄우면, 지금까지의 제품은 **검증 Step 을 만들지 않았다.** 성공한 것만 기록하는
 * 규칙(001 FR-061)이 검증에도 걸려 있었기 때문이다. 모델에게는 통과하는 값을 찾는
 * 것 외에 선택지가 없었고, 그래서 버그값이 정답으로 굳었다.
 *
 * 이 모델이 그 자리를 채운다. **기대와 달랐다는 사실을 기록하고 Step 은 남긴다.**
 *
 * ## 기대값은 여기에 없다
 *
 * 기대값의 유일한 출처는 ``AssertionStep.assertion.value`` 다. 여기에 복제해 두면
 * Step 편집으로 조건을 고쳤을 때 둘이 갈리고, 그때 어느 쪽이 맞는지 아무도 모른다
 * (`UploadStep` 이 확장자를 별도 필드로 두지 않는 것과 같은 판단).
 *
 * ## 결함이라고 판정하지 않는다
 *
 * 이름이 「결함」이 아니라 「어긋남」인 이유다. 기대와 관찰이 달랐다는 것은 사실이고,
 * 그것이 제품 결함인지 지시문 오류인지는 **사람이 판단한다.**
 */
export interface AuthoringMismatch {
  observed: Observed;
  recorded_at: RecordedAt;
  truncated: Truncated;
}
/**
 * 탭 닫기 (FR-030c). 대상은 공통 ``tab`` 필드가 가리킨다.
 */
export interface CloseTabStep {
  author: Author5;
  frame_url: FrameUrl5;
  id: Id5;
  label: Label5;
  tab: Tab5;
  timeout_ms: TimeoutMs5;
  type: Type5;
}
/**
 * 마우스를 올리는 동작 (FR-023c).
 *
 * **화면을 바꾼 hover 만 기록한다.** 포인터가 지나간 모든 요소를 Step 으로 만들면 정의가
 * 쓸모없이 길어지고, 어느 hover 가 의미 있었는지 사람이 다시 판단해야 한다. 리코더는
 * hover 직후 문서 변화가 관측된 경우만 이 Step 을 만든다 (contracts/step-dsl.md).
 */
export interface HoverStep {
  author: Author6;
  frame_url: FrameUrl6;
  id: Id6;
  label: Label6;
  tab: Tab6;
  target: TargetLocator;
  timeout_ms: TimeoutMs6;
  type: Type6;
}
/**
 * 끌어다 놓는 동작 (FR-023c).
 *
 * ``target`` 이 끄는 대상이고 ``drop_target`` 이 놓는 위치다. 다른 Step 과 마찬가지로
 * ``target`` 이 주된 대상이므로 `target_of` 가 그대로 동작한다.
 */
export interface DragStep {
  author: Author7;
  drop_target: TargetLocator;
  frame_url: FrameUrl7;
  id: Id7;
  label: Label7;
  tab: Tab7;
  target: TargetLocator;
  timeout_ms: TimeoutMs7;
  type: Type7;
}
/**
 * 파일을 올리는 동작 (2026-09-09 사용자 보고).
 *
 * ## 무엇을 기록하는가 — **파일 이름 하나다**
 *
 * 사용자가 요구한 것은 확장자다: 「파일업로드 녹화의 경우, 파일의 확장자 기록되 되어야함.
 * 실제 서비스에서는 확장자를 보는경우가 있기 때문」.
 *
 * 그래서 이 Step 은 ``file_name`` 을 갖고, **확장자는 그 이름의 일부다.** 확장자를 별도
 * 필드로 두지 않는 이유는 진실이 둘이 되기 때문이다 — 이름이 ``보고서.xlsx`` 인데
 * 확장자 필드가 ``csv`` 인 Step 이 만들어질 수 있고, 그때 어느 쪽이 맞는지 아무도 모른다.
 * 확장자가 필요한 곳은 `extension_of` 로 꺼낸다.
 *
 * **파일 내용은 기록하지 않는다.** 녹화 시점에 브라우저가 주는 것은 이름뿐이고
 * (``File.name``), 내용을 정의 파일에 담으면 테스트가 옮겨 다닐 수 없게 된다. 재실행은
 * 같은 이름의 빈 파일을 만들어 올린다 — 확장자를 보는 검증은 통과하고, 내용을 파싱하는
 * 검증은 통과하지 못한다. 그 한계는 실행기 쪽에 적어 두었다.
 */
export interface UploadStep {
  author: Author8;
  file_name: FileName;
  frame_url: FrameUrl8;
  id: Id8;
  label: Label8;
  tab: Tab8;
  target: TargetLocator;
  timeout_ms: TimeoutMs8;
  type: Type8;
}
/**
 * 키를 누르는 동작 (023 FR-050).
 *
 * ## ``target`` 이 필수인 이유 — 포커스에 기대지 않는다
 *
 * 「지금 포커스된 곳에 Enter」는 **앞 Step 의 부작용에 결과가 좌우된다.** 정의만 보고
 * 무엇을 했는지 알 수 없고, 화면이 조금 바뀌면 엉뚱한 요소가 키를 받는다. 원칙 II 가
 * 요구하는 「같은 화면이면 같은 결과」가 성립하지 않는다.
 *
 * 그래서 실행도 내보내기도 **대상 요소에 포커스를 준 뒤** 키를 보낸다 (FR-051).
 *
 * ## ``value`` 가 아니라 ``key`` 인 이유
 *
 * :class:`FillStep` 의 ``value`` 는 **사람이 친 글자**이고 민감할 수 있어 변수 참조로
 * 저장된다. 여기의 ``key`` 는 **어느 키를 눌렀는가**이고 열거값이며 비밀이 될 수 없다.
 * 이름을 같게 하면 민감값 처리 코드가 이 필드도 훑어야 하는지 매번 판단하게 된다.
 *
 * ## 이 Step 은 결과를 판정하지 않는다
 *
 * 「Enter 를 눌렀더니 태그가 생겼다」를 확인하려면 **검증 Step 을 따로** 둔다. 키를
 * 눌렀는데 화면이 안 바뀌어도 이 Step 은 성공이다 — 동작과 판정을 한 Step 에 뭉치면
 * 실패했을 때 어느 쪽이 틀렸는지 알 수 없다.
 */
export interface PressStep {
  author: Author9;
  frame_url: FrameUrl9;
  id: Id9;
  key: PressKey;
  label: Label9;
  tab: Tab9;
  target: TargetLocator;
  timeout_ms: TimeoutMs9;
  type: Type9;
}
