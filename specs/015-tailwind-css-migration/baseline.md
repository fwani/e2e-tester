# 기준선 — 전환 전 실측 (T001)

**측정 시각**: 2026-09-10 | **커밋**: `1bc508f` (전환 착수 직전) | **브랜치**: `015-tailwind-css-migration`

이 수치가 없으면 나중에 "줄지 않았다"·"늘지 않았다"를 증명할 수 없다.
전환이 끝난 뒤 [quickstart.md](quickstart.md) §1·§6 이 이 표와 대조한다.

## 테스트

| 축 | 값 | 재는 법 |
|---|---|---|
| 테스트 파일 | **94** | `find tests -name '*.test.ts*' \| wc -l` |
| 테스트 케이스 | **1244** | `npm test -- --run` |
| 통과 | **1244 / 1244** | 실패 0 · 건너뜀 0 |
| **단언 총수** | **1934** | `grep -rho 'expect(' tests \| wc -l` |
| `.style.` 직접 읽기 | **68** | `grep -rho '\.style\.' tests \| wc -l` |
| 무른 단언 | **596** | `node scripts/count-assertions.mjs` |
| 건너뛴 테스트 | **0** | 같음 |

**무른 단언 596 은 기존 코드베이스의 것이다.** 015 가 만든 것이 아니며 줄이는 것도 이번
범위가 아니다. 기준선으로 두는 이유는 **이 수가 늘면 신호**이기 때문이다 — 단언 총수만
지키고 `toBeDefined()` 로 바꾸면 수치는 통과하고 검증은 사라진다.

**단언 1934 가 헌법 Quality Gate 4 의 기준선이다.** 전환 후 이 수보다 줄면
그 자리를 지목하고 이유를 대야 한다 (T065).

`.style.` 68 은 판정 방법을 바꿔야 하는 지점의 수다. 이 수는 0 이 되어야 하지만,
**그만큼의 단언이 사라지는 것이 아니라 다른 형태로 옮겨간다** (LC-4 의 3겹).

## 소스

| 축 | 값 | 재는 법 |
|---|---|---|
| 인라인 `style={{` | **455** | `grep -rho 'style={{' src \| wc -l` |
| 인라인이 있는 `.tsx` | **39 / 43** | |
| 의미 클래스 | **109** (규칙 블록 139) | `tokens.css` 주석 제외 셀렉터 추출 |
| 시각 언어 위반 | **색 0 · 인라인 0 · 팔레트 밖 0종** | `node scripts/count-violations.mjs` |

**위반이 이미 0 이라는 것이 이 전환의 출발점이다.** 008 이 시각 속성을 끝냈고,
남은 455 곳은 배치 속성이며 008 계약 §2 가 허용한 것이다.

## 빌드 산출물

| 파일 | 크기 | gzip |
|---|---|---|
| `dist/assets/index-*.css` | **15.04 kB** | **3.43 kB** |
| `dist/assets/index-*.js` | 446.60 kB | 132.03 kB |
| `dist/index.html` | 0.62 kB | 0.39 kB |

빌드 시간 668ms.

**CSS 15.04 kB 가 SC-007 의 기준선이다.** 전환 후 이보다 커지면 원인을 찾는다 (T064).

## 인라인 분포 (파일별)

전환 작업 배정의 근거다. 4-B 의 작업 순서가 이 표를 따른다.

| 파일 | 수 | 담당 작업 |
|---|---|---|
| `pages/TestList.tsx` | 55 | T031 |
| `pages/ProjectSetup.tsx` | 55 | T032 |
| `pages/ImportPreview.tsx` | 41 | T033 |
| `components/workbench/WorkArea.tsx` | 30 | T034 |
| `pages/KeyManagement.tsx` | 28 | T035 |
| `components/workbench/StepDetail.tsx` | 24 | T036 |
| `pages/DraftList.tsx` | 17 | T037 |
| `pages/EditView.tsx` · `components/TestBulkConfirm.tsx` | 15 · 15 | T038 |
| `pages/SecretValues.tsx` · `components/InlineSecretInput.tsx` | 13 · 7 | T039 |
| `components/workbench/PhaseBar.tsx` | 13 | T040 |
| `components/workbench/ActionPalette.tsx` · `ActionButton.tsx` | 13 · 5 | T041 |
| `components/workbench/InsertStepForm.tsx` | 12 | T042 |
| `components/workbench/TargetPane.tsx` | 11 | T043 |
| `components/MirrorView.tsx` | 11 | T044 |
| `components/workbench/StepList.tsx` · `StepRowOps.tsx` | 10 · 1 | T045 |
| `components/LocatorPriorityTable.tsx` · `AssertionForm.tsx` | 9 · 9 | T046 |
| `pages/SessionScreen.tsx` · `TestGroupBar.tsx` · `SessionLostBanner.tsx` | 7 · 7 · 6 | T047 |
| `components/workbench/NoticeStack.tsx` · `BulkDeleteConfirm.tsx` | 4 · 1 | T048 |
| `components/design/Chrome.tsx` · `BrowserFrame.tsx` | 4 · 4 | T049 |
| `components/TabStrip.tsx` | 2 | T017 (US1 시범) |
| 잔여 소형 9개 | 20 | T050 |

---

## 중간 기록 — US1 완료 시점 (T018 · 2026-09-10)

| 축 | 기준선 | US1 후 | 판정 |
|---|---|---|---|
| 테스트 통과 | 1244/1244 | **1258/1258** | ✅ (가드 4종이 더해져 늘었다) |
| 단언 총수 | 1934 | **1950** | ✅ 줄지 않았다 |
| 인라인 | 455 | **453** | 진행 중 |
| 의미 클래스 (정본+파생) | 109 | **107** | 진행 중 (파생에서 `.btn.quiet`·`button.primary` 삭제) |
| CSS 크기 | 15.04 kB | **21.10 kB** | ⚠️ **SC-007 미달** |
| 위반 계수 | 0 | **0** | ✅ 유지 |
| L1 대조 | 725칸 불일치 0 | **725칸 불일치 0** | ✅ 유지 |

**CSS 6.06 kB 증가는 공존 상태 때문이다.** Tailwind 유틸리티가 들어왔는데 의미 클래스
107개가 아직 그대로 있다. 전환이 끝나면 그 107개가 사라지므로 순감할 것으로 보지만,
**그것은 예상이고 지금은 미달이다.** T064 가 판정한다.

**값 복제 0 실증 (US1 시나리오 3)**: 정본 `--ink` 를 `#FF00FF` 로 바꾸고 빌드하니
산출 CSS 의 정의만 바뀌고 `.bg-ink{background-color:var(--ink)}` 는 그대로였다.
유틸리티가 정본을 직접 가리킨다는 증거다.

## 전환 후 기록 (작업이 채운다)

| 축 | 기준선 | 전환 후 | 판정 |
|---|---|---|---|
| 단언 총수 | 1934 | _(T065)_ | 줄면 안 된다 |
| 무른 단언 | 596 | _(T065)_ | 늘면 안 된다 |
| 테스트 통과 | 1244/1244 | _(T065)_ | 전량 통과 |
| 인라인 | 455 | _(T051)_ | 등록된 예외뿐 |
| 의미 클래스 | 109 | _(T028)_ | 0 |
| CSS 크기 | 15.04 kB | _(T064)_ | 늘면 안 된다 |
| 위반 계수 | 0 | _(T053)_ | 0 유지 |
| L2 대조 | — | _(T063)_ | 불일치 0 |
