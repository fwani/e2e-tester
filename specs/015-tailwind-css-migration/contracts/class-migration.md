# Contract: 의미 클래스 109개 행선지 대응표

**Feature**: 015 | **Status**: 살아 있는 문서 — 전환이 진행되며 갱신된다

## 목적

SC-009 「미상 0건」. 109개를 머릿속으로 추적할 수 없고, 전환이 여러 커밋에 걸치므로
진행 상태를 담을 자리가 필요하다. 남은 클래스를 세는 것만으로는 *어디로 갔는지*를
알 수 없다.

## 표 형식

| 클래스 | 사용처 | 행선지 | 상태 |
|---|---|---|---|
| `.btn` | 1 | T024 | `ui/Button` — 남은 1곳은 `.btn.file`(파일 선택 label)이며 폼 부품 관할 | 교체 | 클래스가 사는 곳 | 「완료」 조건 |
|---|---|
| **정본 구획** (1~203줄, 자동 추출) | **화면 코드의 사용 0.** 정의는 남는다 — 확정 디자인의 기록이자 L1 대조의 기준이다 |
| **파생 구획** (204줄~, 손으로 쓴 것) | **정의 삭제.** 화면이 쓰지 않으면 남길 이유가 없다 |

사용자가 고른 「전면 해체」는 이 정정으로 약해지지 않는다 — **화면 코드에서 의미 클래스가
사라지는 것은 같다.** 바뀐 것은 tokens.css 의 정본 구획을 무엇으로 보느냐다.

## 기계가 세는 것 (가드 G-D)

```
tokens.css 에 남은 의미 클래스 수  ==  이 표의 「완료」 아닌 행 수
```

표만 갱신하고 코드를 안 옮기는 것과 그 반대를 둘 다 잡는다.

## 표 (구현 시작 시 채운다)

> 클래스 목록 추출:
> ```bash
> grep -oE '^\.[a-zA-Z0-9_-]+' frontend/src/theme/tokens.css | sort -u
> ```
> 사용처 계수는 각 클래스에 대해 `frontend/src/**/*.tsx` 를 센다.
> 이 표를 채우는 것이 2단계(부품)의 첫 작업이다.

**채운 시각**: 2026-09-10 (T008) · **클래스 109개 · 사용 104 · 미사용 5**

사용처는 `.tsx` 의 `className` 값에서 토큰을 추출해 셌다. 자식 선택자(`.pane .body`)로만
쓰이는 것은 0 으로 나올 수 있으므로, **사용 0 인 5개는 삭제 전에 실제 사용을 확인한다.**

| 클래스 | 사용처 | 담당 | 행선지 | 상태 |
|---|---|---|---|---|
| `.why` | 133 | T021 | ui/Notice · ui/Toast | 미착수 |
| `.btn` | 1 | T024 | `ui/Button` — 남은 1곳은 `.btn.file`(파일 선택 label)이며 폼 부품 관할 | 교체 |
| `.sm` | 1 | T027 | `ui/Button` size=sm 로 흡수 · 남은 사용은 다른 부품의 작은 변종 | 교체 |
| `.row` | 54 | T025 | ui/Table · ui/Grid | 미착수 |
| `.mono` | 45 | T027 | 유틸리티 조합 (부품 아님) | 미착수 |
| `.chip` | 38 | T020 | ui/Chip · ui/Badge | 구현 |
| `.line` | 35 | T027 | 유틸리티 조합 (부품 아님) | 미착수 |
| `.lbl` | 31 | T024 | ui/Field · ui/FileInput | 미착수 |
| `.pane` | 29 | T023 | ui/Pane · ui/Header | 미착수 |
| `.strong-sm` | 28 | T027 | 유틸리티 조합 (부품 아님) | 미착수 |
| `.fail-ink` | 27 | T019 | ui/tone.ts + 상태 유틸 | 미착수 |
| `.spacer` | 27 | T023 | ui/Pane · ui/Header | 미착수 |
| `.tint-warn` | 27 | T019 | ui/tone.ts + 상태 유틸 | 미착수 |
| `.navlink` | 26 | T027 | 유틸리티 조합 (부품 아님) | 미착수 |
| `.muted` | 22 | T027 | 유틸리티 조합 (부품 아님) | 미착수 |
| `.primary` | 0 | T015 | `ui/Button` variant=primary | 완료 |
| `.ai` | 13 | T019 | ui/tone.ts + 상태 유틸 | 미착수 |
| `.danger` | 5 | T027 | `ui/Button` variant=danger 로 흡수 · 남은 사용은 `.op danger`(행 조작) | 교체 |
| `.note` | 13 | T027 | 유틸리티 조합 (부품 아님) | 미착수 |
| `.subtitle` | 12 | T023 | ui/Pane · ui/Header | 미착수 |
| `.num` | 9 | T020 | ui/Chip · ui/Badge | 미착수 |
| `.title` | 9 | T023 | ui/Pane · ui/Header | 미착수 |
| `.dim` | 8 | T027 | 유틸리티 조합 (부품 아님) | 미착수 |
| `.field-label` | 7 | T024 | ui/Field · ui/FileInput | 미착수 |
| `.secondary` | 7 | T015 | `ui/Button` variant=default — 정본 주석이 「기본형이 곧 보조 조작」이라 적었다 | 구현 |
| `.warn` | 7 | T019 | ui/tone.ts + 상태 유틸 | 미착수 |
| `.rule-top` | 6 | T023 | ui/Pane · ui/Header | 미착수 |
| `.sunken` | 6 | T027 | 유틸리티 조합 (부품 아님) | 미착수 |
| `.tint-fail` | 6 | T019 | ui/tone.ts + 상태 유틸 | 미착수 |
| `.tint-run` | 6 | T019 | ui/tone.ts + 상태 유틸 | 미착수 |
| `.off` | 1 | T019 | `ui/Button` variant=off 로 흡수 · 남은 사용은 상태 수식 | 교체 |
| `.pane-hd` | 4 | T023 | ui/Pane · ui/Header | 미착수 |
| `.pass` | 4 | T019 | ui/tone.ts + 상태 유틸 | 미착수 |
| `.pass-ink` | 4 | T019 | ui/tone.ts + 상태 유틸 | 미착수 |
| `.quiet` | 0 | T015 | `ui/Button` variant=quiet | 완료 |
| `.ai-ink` | 3 | T019 | ui/tone.ts + 상태 유틸 | 미착수 |
| `.log` | 3 | T027 | 유틸리티 조합 (부품 아님) | 미착수 |
| `.op` | 3 | T027 | 유틸리티 조합 (부품 아님) | 미착수 |
| `.pill` | 3 | T020 | ui/Chip · ui/Badge | 미착수 |
| `.rule-bottom` | 3 | T023 | ui/Pane · ui/Header | 미착수 |
| `.sel` | 3 | T020 | ui/Chip · ui/Badge | 미착수 |
| `.textlink` | 3 | T027 | 유틸리티 조합 (부품 아님) | 미착수 |
| `.band` | 2 | T020 | ui/Chip · ui/Badge | 미착수 |
| `.fail` | 2 | T019 | ui/tone.ts + 상태 유틸 | 미착수 |
| `.float` | 2 | T022 | ui/Modal · ui/Overlay | 미착수 |
| `.grid-head` | 2 | T025 | ui/Table · ui/Grid | 미착수 |
| `.key-cell` | 2 | T025 | ui/Table · ui/Grid | 미착수 |
| `.loc` | 2 | T027 | 유틸리티 조합 (부품 아님) | 미착수 |
| `.m` | 2 | T027 | 유틸리티 조합 (부품 아님) | 미착수 |
| `.meta` | 2 | T027 | 유틸리티 조합 (부품 아님) | 미착수 |
| `.modal` | 2 | T022 | ui/Modal · ui/Overlay | 미착수 |
| `.modal-scrim` | 2 | T022 | ui/Modal · ui/Overlay | 미착수 |
| `.n` | 2 | T027 | 유틸리티 조합 (부품 아님) | 미착수 |
| `.notice` | 2 | T021 | ui/Notice · ui/Toast | 미착수 |
| `.phase` | 2 | T026 | workbench 부품 | 미착수 |
| `.phase-name` | 2 | T026 | workbench 부품 | 미착수 |
| `.steps-ft` | 2 | T026 | workbench 부품 | 미착수 |
| `.warn-ink` | 2 | T019 | ui/tone.ts + 상태 유틸 | 미착수 |
| `.addr` | 1 | T027 | 유틸리티 조합 (부품 아님) | 미착수 |
| `.answer-q` | 1 | T024 | ui/Field · ui/FileInput | 미착수 |
| `.bare` | 1 | T027 | 테두리 제거 수식 — 버튼 전용이 아니다. 유틸리티 조합 | 미착수 |
| `.brand` | 1 | T023 | ui/Pane · ui/Header | 미착수 |
| `.brand-name` | 1 | T023 | ui/Pane · ui/Header | 미착수 |
| `.code-block` | 1 | T027 | 유틸리티 조합 (부품 아님) | 미착수 |
| `.commit-bar` | 1 | T024 | ui/Field · ui/FileInput | 미착수 |
| `.d` | 1 | T027 | 유틸리티 조합 (부품 아님) | 미착수 |
| `.danger-edge` | 1 | T027 | 유틸리티 조합 (부품 아님) | 미착수 |
| `.divider` | 1 | T023 | ui/Pane · ui/Header | 미착수 |
| `.dot` | 1 | T020 | ui/Chip · ui/Badge | 미착수 |
| `.field` | 1 | T024 | ui/Field · ui/FileInput | 미착수 |
| `.file` | 1 | T024 | ui/Field · ui/FileInput | 미착수 |
| `.file-input` | 1 | T024 | ui/Field · ui/FileInput | 미착수 |
| `.ghost` | 1 | T015 | `ui/Button` variant=ghost | 구현 |
| `.hdr` | 1 | T023 | ui/Pane · ui/Header | 미착수 |
| `.hint-line` | 1 | T021 | ui/Notice · ui/Toast | 미착수 |
| `.ime-capture` | 1 | T024 | ui/Field · ui/FileInput | 미착수 |
| `.in-use` | 1 | T019 | ui/tone.ts + 상태 유틸 | 미착수 |
| `.last-resort` | 1 | T020 | ui/Chip · ui/Badge | 미착수 |
| `.name` | 1 | T027 | 유틸리티 조합 (부품 아님) | 미착수 |
| `.notice-body` | 1 | T021 | ui/Notice · ui/Toast | 미착수 |
| `.on` | 1 | T019 | ui/tone.ts + 상태 유틸 | 미착수 |
| `.overlay-pane` | 1 | T022 | ui/Modal · ui/Overlay | 미착수 |
| `.paused` | 1 | T019 | ui/tone.ts + 상태 유틸 | 미착수 |
| `.phase-progress` | 1 | T026 | workbench 부품 | 미착수 |
| `.pick` | 1 | T027 | 유틸리티 조합 (부품 아님) | 미착수 |
| `.run` | 1 | T019 | ui/tone.ts + 상태 유틸 | 미착수 |
| `.run-ink` | 1 | T019 | ui/tone.ts + 상태 유틸 | 미착수 |
| `.scrim` | 1 | T022 | ui/Modal · ui/Overlay | 미착수 |
| `.segmented` | 1 | T027 | 유틸리티 조합 (부품 아님) | 미착수 |
| `.srow` | 1 | T026 | workbench 부품 | 미착수 |
| `.srow-check` | 1 | T026 | workbench 부품 | 미착수 |
| `.srow-name` | 1 | T026 | workbench 부품 | 미착수 |
| `.srow-ops` | 1 | T026 | workbench 부품 | 미착수 |
| `.steps` | 1 | T026 | workbench 부품 | 미착수 |
| `.steps-hd` | 1 | T026 | workbench 부품 | 미착수 |
| `.t` | 1 | T027 | 유틸리티 조합 (부품 아님) | 미착수 |
| `.table` | 1 | T025 | ui/Table · ui/Grid | 미착수 |
| `.tabs` | 1 | T025 | ui/Table · ui/Grid | 미착수 |
| `.tfoot` | 1 | T025 | ui/Table · ui/Grid | 미착수 |
| `.thead` | 1 | T025 | ui/Table · ui/Grid | 미착수 |
| `.tint-pass` | 1 | T019 | ui/tone.ts + 상태 유틸 | 미착수 |
| `.toast` | 1 | T021 | ui/Notice · ui/Toast | 미착수 |
| `.toast-body` | 1 | T021 | ui/Notice · ui/Toast | 미착수 |
| `.toast-layer` | 1 | T021 | ui/Notice · ui/Toast | 미착수 |
| `.body` | 0 | T023 | ui/Pane · ui/Header · **사용 0 — 삭제 후보** | 미착수 |
| `.disabled` | 0 | T024 | `ui/Button` 은 `:disabled` 로 처리 · `.btn.disabled` 는 파일 선택 label 관할 | 교체 |
| `.left` | 0 | T027 | 유틸리티 조합 (부품 아님) · **사용 0 — 삭제 후보** | 미착수 |
| `.tint-ai` | 0 | T019 | ui/tone.ts + 상태 유틸 · **사용 0 — 삭제 후보** | 미착수 |
| `.trow` | 0 | T025 | ui/Table · ui/Grid · **사용 0 — 삭제 후보** | 미착수 |

**미배정 0개**: 없음
