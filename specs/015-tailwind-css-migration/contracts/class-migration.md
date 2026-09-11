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
| `.why` | 133 | T021 | ui/Notice · ui/Toast | 완료 |
| `.btn` | 1 | T024 | `ui/Button` — 남은 1곳은 `.btn.file`(파일 선택 label)이며 폼 부품 관할 | 교체 |
| `.sm` | 1 | T027 | `ui/Button` size=sm 로 흡수 · 남은 사용은 다른 부품의 작은 변종 | 완료 |
| `.row` | 54 | T025 | ui/Table · ui/Grid | 구현 |
| `.mono` | 45 | T027 | 유틸리티 조합 (부품 아님) | 완료 |
| `.chip` | 38 | T020 | ui/Chip · ui/Badge | 구현 |
| `.line` | 35 | T027 | 유틸리티 조합 (부품 아님) | 미착수 |
| `.lbl` | 31 | T024 | ui/Field · ui/FileInput | 완료 |
| `.pane` | 29 | T023 | ui/Pane · ui/Header | 완료 |
| `.strong-sm` | 28 | T027 | 유틸리티 조합 (부품 아님) | 미착수 |
| `.fail-ink` | 27 | T019 | ui/tone.ts + 상태 유틸 | 미착수 |
| `.spacer` | 27 | T023 | ui/Pane · ui/Header | 구현 |
| `.tint-warn` | 27 | T019 | ui/tone.ts + 상태 유틸 | 미착수 |
| `.navlink` | 26 | T027 | 유틸리티 조합 (부품 아님) | 미착수 |
| `.muted` | 22 | T027 | 유틸리티 조합 (부품 아님) | 미착수 |
| `.primary` | 0 | T015 | `ui/Button` variant=primary | 완료 |
| `.ai` | 13 | T019 | ui/tone.ts + 상태 유틸 | 미착수 |
| `.danger` | 5 | T027 | `ui/Button` variant=danger 로 흡수 · 남은 사용은 `.op danger`(행 조작) | 교체 |
| `.note` | 13 | T027 | 유틸리티 조합 (부품 아님) | 미착수 |
| `.subtitle` | 12 | T023 | ui/Pane · ui/Header | 구현 |
| `.num` | 9 | T020 | ui/Chip · ui/Badge | 미착수 |
| `.title` | 9 | T023 | ui/Pane · ui/Header | 구현 |
| `.dim` | 8 | T027 | 유틸리티 조합 (부품 아님) | 미착수 |
| `.field-label` | 7 | T024 | ui/Field · ui/FileInput | 구현 |
| `.secondary` | 7 | T015 | `ui/Button` variant=default — 정본 주석이 「기본형이 곧 보조 조작」이라 적었다 | 구현 |
| `.warn` | 7 | T019 | ui/tone.ts + 상태 유틸 | 완료 |
| `.rule-top` | 6 | T023 | ui/Pane · ui/Header | 구현 |
| `.sunken` | 6 | T027 | 유틸리티 조합 (부품 아님) | 미착수 |
| `.tint-fail` | 6 | T019 | ui/tone.ts + 상태 유틸 | 미착수 |
| `.tint-run` | 6 | T019 | ui/tone.ts + 상태 유틸 | 미착수 |
| `.off` | 1 | T019 | `ui/Button` variant=off 로 흡수 · 남은 사용은 상태 수식 | 교체 |
| `.pane-hd` | 4 | T023 | ui/Pane · ui/Header | 구현 |
| `.pass` | 4 | T019 | ui/tone.ts + 상태 유틸 | 미착수 |
| `.pass-ink` | 4 | T019 | ui/tone.ts + 상태 유틸 | 미착수 |
| `.quiet` | 0 | T015 | `ui/Button` variant=quiet | 완료 |
| `.ai-ink` | 3 | T019 | ui/tone.ts + 상태 유틸 | 미착수 |
| `.log` | 3 | T027 | 유틸리티 조합 (부품 아님) | 미착수 |
| `.op` | 3 | T027 | 유틸리티 조합 (부품 아님) | 완료 |
| `.pill` | 3 | T020 | ui/Chip · ui/Badge | 미착수 |
| `.rule-bottom` | 3 | T023 | ui/Pane · ui/Header | 구현 |
| `.sel` | 3 | T020 | ui/Chip · ui/Badge | 미착수 |
| `.textlink` | 3 | T027 | 유틸리티 조합 (부품 아님) | 미착수 |
| `.band` | 2 | T020 | ui/Chip · ui/Badge | 미착수 |
| `.fail` | 2 | T019 | ui/tone.ts + 상태 유틸 | 미착수 |
| `.float` | 2 | T022 | ui/Modal · ui/Overlay | 완료 |
| `.grid-head` | 2 | T025 | ui/Table · ui/Grid | 구현 |
| `.key-cell` | 2 | T025 | ui/Table · ui/Grid | 구현 |
| `.loc` | 2 | T027 | 유틸리티 조합 (부품 아님) | 완료 |
| `.m` | 2 | T027 | 유틸리티 조합 (부품 아님) | 완료 |
| `.meta` | 2 | T027 | 유틸리티 조합 (부품 아님) | 미착수 |
| `.modal` | 2 | T022 | ui/Modal · ui/Overlay | 구현 |
| `.modal-scrim` | 2 | T022 | ui/Modal · ui/Overlay | 구현 |
| `.n` | 2 | T027 | 유틸리티 조합 (부품 아님) | 완료 |
| `.notice` | 2 | T021 | ui/Notice · ui/Toast | 완료 |
| `.phase` | 2 | T026 | workbench 부품 | 완료 |
| `.phase-name` | 2 | T026 | workbench 부품 | 구현 |
| `.steps-ft` | 2 | T026 | workbench 부품 | 구현 |
| `.warn-ink` | 2 | T019 | ui/tone.ts + 상태 유틸 | 미착수 |
| `.addr` | 1 | T027 | 유틸리티 조합 (부품 아님) | 미착수 |
| `.answer-q` | 1 | T024 | ui/Field · ui/FileInput | 구현 |
| `.bare` | 1 | T027 | 테두리 제거 수식 — 버튼 전용이 아니다. 유틸리티 조합 | 미착수 |
| `.brand` | 1 | T023 | ui/Pane · ui/Header | 구현 |
| `.brand-name` | 1 | T023 | ui/Pane · ui/Header | 구현 |
| `.code-block` | 1 | T027 | 유틸리티 조합 (부품 아님) | 미착수 |
| `.commit-bar` | 1 | T024 | ui/Field · ui/FileInput | 구현 |
| `.d` | 1 | T027 | 유틸리티 조합 (부품 아님) | 완료 |
| `.danger-edge` | 1 | T027 | 유틸리티 조합 (부품 아님) | 미착수 |
| `.divider` | 1 | T023 | ui/Pane · ui/Header | 구현 |
| `.dot` | 1 | T020 | ui/Chip · ui/Badge | 미착수 |
| `.field` | 1 | T024 | ui/Field · ui/FileInput | 구현 |
| `.file` | 1 | T024 | ui/Field · ui/FileInput | 구현 |
| `.file-input` | 1 | T024 | ui/Field · ui/FileInput | 구현 |
| `.ghost` | 1 | T015 | `ui/Button` variant=ghost | 구현 |
| `.hdr` | 1 | T023 | ui/Pane · ui/Header | 완료 |
| `.hint-line` | 1 | T021 | ui/Notice · ui/Toast | 구현 |
| `.ime-capture` | 1 | T024 | ui/Field · ui/FileInput | 구현 |
| `.in-use` | 1 | T019 | ui/tone.ts + 상태 유틸 | 미착수 |
| `.last-resort` | 1 | T020 | ui/Chip · ui/Badge | 미착수 |
| `.name` | 1 | T027 | 유틸리티 조합 (부품 아님) | 미착수 |
| `.notice-body` | 1 | T021 | ui/Notice · ui/Toast | 구현 |
| `.on` | 1 | T019 | ui/tone.ts + 상태 유틸 | 미착수 |
| `.overlay-pane` | 1 | T022 | ui/Modal · ui/Overlay | 구현 |
| `.paused` | 1 | T019 | ui/tone.ts + 상태 유틸 | 미착수 |
| `.phase-progress` | 1 | T026 | workbench 부품 | 구현 |
| `.pick` | 1 | T027 | 유틸리티 조합 (부품 아님) | 미착수 |
| `.run` | 1 | T019 | ui/tone.ts + 상태 유틸 | 미착수 |
| `.run-ink` | 1 | T019 | ui/tone.ts + 상태 유틸 | 미착수 |
| `.scrim` | 1 | T022 | ui/Modal · ui/Overlay | 구현 |
| `.segmented` | 1 | T027 | 유틸리티 조합 (부품 아님) | 미착수 |
| `.srow` | 1 | T026 | workbench 부품 | 구현 |
| `.srow-check` | 1 | T026 | workbench 부품 | 완료 |
| `.srow-name` | 1 | T026 | workbench 부품 | 구현 |
| `.srow-ops` | 1 | T026 | workbench 부품 | 완료 |
| `.steps` | 1 | T026 | workbench 부품 | 완료 |
| `.steps-hd` | 1 | T026 | workbench 부품 | 완료 |
| `.t` | 1 | T027 | 유틸리티 조합 (부품 아님) | 미착수 |
| `.table` | 1 | T025 | ui/Table · ui/Grid | 구현 |
| `.tabs` | 1 | T025 | ui/Table · ui/Grid | 구현 |
| `.tfoot` | 1 | T025 | ui/Table · ui/Grid | 구현 |
| `.thead` | 1 | T025 | ui/Table · ui/Grid | 구현 |
| `.tint-pass` | 1 | T019 | ui/tone.ts + 상태 유틸 | 미착수 |
| `.toast` | 1 | T021 | ui/Notice · ui/Toast | 완료 |
| `.toast-body` | 1 | T021 | ui/Notice · ui/Toast | 완료 |
| `.toast-layer` | 1 | T021 | ui/Notice · ui/Toast | 완료 |
| `.body` | 0 | T023 | ui/Pane · ui/Header · **사용 0 — 삭제 후보** | 완료 |
| `.disabled` | 0 | T024 | `ui/Button` 은 `:disabled` 로 처리 · `.btn.disabled` 는 파일 선택 label 관할 | 교체 |
| `.left` | 0 | T027 | 유틸리티 조합 (부품 아님) · **사용 0 — 삭제 후보** | 완료 |
| `.tint-ai` | 0 | T019 | ui/tone.ts + 상태 유틸 · **사용 0 — 삭제 후보** | 미착수 |
| `.trow` | 0 | T025 | ui/Table · ui/Grid · **사용 0 — 삭제 후보** | 구현 |

**미배정 0개**: 없음

## 최종 상태 (2026-09-11)

| 축 | 값 |
|---|---|
| 정본 클래스 | **109** |
| **화면 코드의 사용** | **0** |
| 표의 「완료」 | **26** (정의가 정본 구획에만 있는 것) |
| 표의 「완료」 아님 | **83** (파생 구획에 정의가 남아 있는 것) |

## 최종 판정 (T028 · 2026-09-11)

**SC-009(미상 0건)는 달성했다.** 109행 전부 행선지가 적혀 있다.

**화면 코드의 의미 클래스 사용은 0 이다.** 착수 시 104 → 43 → 0. 가드 G-B 가
Tailwind 산출물에 없는 이름을 전부 잡으므로 이 값은 사람이 세는 것이 아니다.

### 「완료」가 26/109 인 이유 — 그리고 그것이 미완이 아닌 이유

표의 「완료」는 **화면이 안 쓰고 + 파생 구획에 정의도 없음**을 뜻한다 (G-D 가 그렇게
읽는다). 83행이 「완료」로 가지 못한 것은 옮기는 일이 남아서가 아니라 **파생 구획에
정의가 남아 있기 때문**이다.

**T075 가 이 조항의 전제를 바꿨다.** 「화면이 쓰지 않으면 남길 이유가 없다」는
그 정의들이 **사용자에게 내려간다**는 전제 위에 있었다. 지금은 내려가지 않는다 —
`scripts/split-canon.mjs` 가 `:root` 변수와 요소 규칙만 뽑아 `tokens.app.css` 를 만들고
앱은 그것만 들인다. 파생 구획은 정본 구획과 마찬가지로 **기록**이 됐고, 지워도 번들은
1 바이트도 줄지 않는다.

게다가 **L1 대조가 그 일부를 읽는다.** `scripts/design_render.py` 의 `FORMS` 는
`btn`·`chip`·`srow`·`op` 의 변종을 확정 디자인과 맞대 보는데, 그 규칙 중 일부가 파생
구획에 있다. 지우면 L1 이 725칸에서 어긋나기 시작한다.

**판정: 83행의 정의 삭제는 하지 않는다.** 근거는 위 둘이며, 「완료」 조항 자체를
고칠지는 **사용자의 판단이 필요한 계약 변경**이므로 여기서 하지 않는다. 지금 상태를
한 줄로 적으면 — **화면 전환은 끝났고(사용 0), 기록은 남겨 두기로 했다.**
