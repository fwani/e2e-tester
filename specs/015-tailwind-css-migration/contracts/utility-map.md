# Contract: 수식 클래스 → 유틸리티 대응표

**Feature**: 015 | **Status**: 계약 | **작성**: 2026-09-10 (T027)

## 목적

부품이 아닌 **수식**(글자 크기·색·굵기 같은 것)은 컴포넌트로 만들지 않는다. 화면 코드가
유틸리티 조합으로 직접 쓴다.

그러면 **같은 수식이 화면마다 다른 조합을 얻을 위험**이 생긴다 — `.muted` 를 어떤 화면은
`text-ink-2` 로, 다른 화면은 `text-[#4A515C]` 로 쓰는 식이다. 그것이 SC-010 이 막으려는
것이고, 이 표가 그 답이다. **화면을 옮길 때 여기를 보고 옮긴다.**

값은 전부 정본에서 왔다. 새로 정한 것은 없다.

## 색 수식

| 정본 | 유틸리티 | 정본 값 |
|---|---|---|
| `.muted` | `text-ink-2` | `--ink-2` |
| `.dim` | `text-ink-3` | `--ink-3` |
| `.pass-ink` | `text-pass` | `--pass` |
| `.fail-ink` | `text-fail` | `--fail` |
| `.warn-ink` | `text-warn` | `--warn` |
| `.run-ink` | `text-run` | `--run` |
| `.ai-ink` | `text-ai` | `--ai` |
| `.sunken` | `bg-sunken-2` | `--sunken-2` |
| `.danger-edge` | `border-fail` | `--fail` |

## 바탕 수식 (`.tint-*`)

`ui/Notice` 의 `TONE` 표와 **같은 값**이다. 알림이 아닌 곳에서 바탕만 필요할 때 쓴다.

| 정본 | 유틸리티 |
|---|---|
| `.tint-pass` | `bg-pass-t border border-pass rounded-base` |
| `.tint-fail` | `bg-fail-t border border-fail-line rounded-base` |
| `.tint-warn` | `bg-warn-t border border-warn-line rounded-base` |
| `.tint-run` | `bg-run-t border border-run rounded-base` |
| `.tint-ai` | `bg-ai-t border border-ai rounded-base` |

## 글자 수식

정본이 `font:` 축약으로 적은 것을 풀었다. **값은 그대로다.**

| 정본 | 유틸리티 |
|---|---|
| `.mono` | `font-mono` |
| `.line` | `font-sans text-[13px] leading-[1.4]` |
| `.strong-sm` | `font-sans text-[13px] font-semibold leading-none` |
| `.title` | `font-sans text-[20px] font-bold leading-[1.3]` |
| `.subtitle` | `font-sans text-[13.5px] font-bold leading-none` |
| `.brand-name` | `font-sans text-[15px] font-bold leading-none tracking-[-0.01em]` |
| `.phase-name` | `font-sans text-[17px] font-bold leading-none whitespace-nowrap overflow-hidden text-ellipsis` |
| `.phase-progress` | `font-sans text-[12px] leading-none text-ink-3` |
| `.name` | `font-sans text-[13px] font-medium leading-none whitespace-nowrap overflow-hidden text-ellipsis` |
| `.num` | `font-mono text-[12px] leading-none text-ink-3` |
| `.meta` | `font-mono text-[11.5px] leading-none text-ink-3` |
| `.note` | `font-sans text-[13.5px] leading-[1.7] text-ink-2` |
| `.why` | `font-sans text-[11px] leading-[1.4] text-ink-3` |
| `.log` | `font-mono text-[12px] leading-[1.6] whitespace-pre-wrap` |
| `.key-cell` | `font-bold` |
| `.code-block` | `bg-ink text-panel rounded-base font-mono text-[11px] leading-[1.6]` |

## 구조 수식

| 정본 | 유틸리티 |
|---|---|
| `.bare` | `border-0` |
| `.spacer` | `flex-1` (또는 `ui/Table` 의 `Spacer`) |
| `.rule-top` | `border-t border-hair` |
| `.rule-bottom` | `border-b border-hair` |
| `.divider` | `ui/Surface` 의 `Divider` |
| `.left` | `flex-1 min-w-0 flex flex-col gap-s3 p-s3` |
| `.dot` | `w-[8px] h-[8px] rounded-full bg-hair-2` |

## 간격 토큰

| 정본 | 유틸리티 | 값 |
|---|---|---|
| `--s-1` | `*-s1` | 4px |
| `--s-2` | `*-s2` | 8px |
| `--s-3` | `*-s3` | 12px |
| `--s-4` | `*-s4` | 16px |
| `--s-5` | `*-s5` | 24px |
| `--s-6` | `*-s6` | 32px |
| `--gap` | `*-gap` | 12px |

정본에 없는 간격(6px·9px·10px·14px 등)은 임의값으로 쓴다 — 그 값들은 정본에도 토큰이
아니라 리터럴로 있었다. **화면 코드가 지어낸 값이 아니라는 것**이 조건이다.

## 이 표를 쓰는 규칙

1. 화면을 옮길 때 여기를 **보고** 옮긴다. 즉석에서 조합을 만들지 않는다.
2. 여기 없는 수식이 필요하면 **먼저 이 표에 더한다.** 그래야 다음 화면이 같은 조합을 쓴다.
3. 정본에 없는 값이 필요해 보이면 멈추고 기록한다 (FR-003).
