---
name: "sdd"
description: "Spec-Driven Development 전체 사이클(constitution → specify → plan → tasks → implement → converge)을 한 번의 선택으로 순서대로 실행하는 오케스트레이터. 개별 speckit-* 스킬을 직접 부르는 대신 이걸 쓴다. \"기능 만들어줘\", \"SDD로 진행\", \"명세부터 구현까지\", \"스펙 짜고 계획까지만\", \"중단된 데부터 이어서\" 같은 요청에 발동. 단일 단계만 필요하면(\"plan만 다시\") 해당 speckit-* 스킬을 직접 호출할 것."
argument-hint: "만들 기능 설명 (신규 시작) 또는 비워두고 현재 상태에서 이어가기"
compatibility: "Requires spec-kit project structure with .specify/ directory"
metadata:
  author: "mobigen-vertical-ai"
user-invocable: true
disable-model-invocation: false
---

## User Input

```text
$ARGUMENTS
```

이 텍스트는 **기능 설명**이다. 비어 있으면 현재 진행 상태에서 이어가는 요청으로 본다.

---

## 이 스킬의 원칙

- **선택은 시작할 때 한 번만.** 실행 단계와 모드를 처음에 확정하고, 이후에는 단계 사이에서 승인을 다시 묻지 않는다.
- **상태에서 출발한다.** 이미 만들어진 산출물은 다시 만들지 않는다. 상태 스캔 결과가 곧 이어하기(resume)다.
- **선택 단계는 조건이 맞을 때만 제안한다.** 항상 끼워 넣지 않는다.
- 각 단계는 반드시 **Skill 도구로 해당 `speckit-*` 스킬을 호출**해서 실행한다. 그 스킬이 할 일을 이 스킬이 직접 흉내 내지 않는다.

---

## 1단계: 상태 스캔

먼저 프로젝트 루트에서 아래를 실행한다.

```bash
[ -d .specify ] || { echo "NOT_A_SPECKIT_PROJECT"; exit 0; }
echo "---GIT---";   git rev-parse --is-inside-work-tree 2>&1
echo "---CONST---"; grep -qF '[PROJECT_NAME]' .specify/memory/constitution.md 2>/dev/null && echo TEMPLATE || echo FILLED
echo "---SPECS---"; ls -d specs/*/ 2>/dev/null || echo NONE
echo "---PATHS---"; bash .specify/scripts/bash/check-prerequisites.sh --paths-only --json 2>&1
echo "---RALPH---"; [ -f .claude/ralph-loop.local.md ] && sed -n '2,7p' .claude/ralph-loop.local.md || echo NONE
```

결과 해석:

- `---RALPH---` 가 `NONE` 이 아님 → **이미 활성 ralph 루프가 있다.** 이 상태로 새 루프를 시작하면 안 된다. 반복 횟수와 프롬프트를 보여주고, 이어갈지 `rm .claude/ralph-loop.local.md` 로 정리할지 사용자에게 먼저 확인한다.
- `NOT_A_SPECKIT_PROJECT` → 여기서 멈추고 `specify init --here --integration claude` 안내만 한다. 추측으로 진행하지 않는다.
- `---PATHS---` 가 `Feature directory not found` 또는 `Failed to resolve feature paths` 로 실패 → **아직 기능이 없는 상태**다. 정상이며 오류가 아니다. `specify` 부터 시작한다.
- `---PATHS---` 가 JSON을 반환 → 그 `FEATURE_DIR` 로 아래를 이어서 실행한다.

```bash
FD="<FEATURE_DIR>"
for f in spec.md plan.md tasks.md; do [ -f "$FD/$f" ] && echo "OK   $f" || echo "MISS $f"; done
echo "clarify_needed=$(grep -c 'NEEDS CLARIFICATION' "$FD/spec.md" 2>/dev/null || echo 0)"
echo "tasks_open=$(grep -cE '^[[:space:]]*-[[:space:]]*\[ \]' "$FD/tasks.md" 2>/dev/null || echo 0)"
```

이 결과로 **단계별 상태**를 판정한다.

| 단계 | 완료 판정 기준 |
|---|---|
| constitution | `constitution.md` 에 `[PROJECT_NAME]` 플레이스홀더가 없음 (`FILLED`) |
| specify | `FEATURE_DIR/spec.md` 존재 |
| plan | `FEATURE_DIR/plan.md` 존재 |
| tasks | `FEATURE_DIR/tasks.md` 존재 |
| implement | `tasks_open` 이 0 |
| converge | 직전 converge 결과가 **Converged** |

`specs/` 에 디렉터리가 여러 개인데 `check-prerequisites` 가 가리키는 대상이 사용자 의도와 다를 수 있으면, 어느 기능을 대상으로 할지 2단계 질문에 함께 넣는다.

---

## 2단계: 실행 계획 제시 + 한 번의 선택

스캔 결과를 표로 먼저 보여준다.

```
현재 상태 — specs/001-user-login
  ✓ constitution   ✓ specify(요구사항 12, 미해결 2)   ✓ plan   ✗ tasks   ✗ implement
```

그다음 **AskUserQuestion을 정확히 한 번** 호출한다. 질문은 최대 2개:

**질문 1 — 실행할 단계** (`multiSelect: true`)
- 기본 경로의 미완료 단계를 옵션으로 올리고, 이어서 실행할 것들을 미리 권장 표시한다.
- 이미 완료된 단계는 옵션에서 뺀다. 단, 사용자가 명시적으로 재실행을 요청했으면 `(재실행)` 표시로 포함한다.
- 아래 **조건부 선택 단계** 규칙에 걸린 것만 옵션에 추가한다.

**질문 2 — 실행 모드** (`multiSelect: false`)
- `연속 실행` — 선택한 단계를 끝까지 멈추지 않고 실행 (기본)
- `단계별 산출물 확인` — 각 단계 후 산출물 요약만 출력하고 계속 진행 (승인은 묻지 않음)

**질문 3 — 구현 방식** (`multiSelect: false`) — `implement` 를 선택했을 때만 묻는다
- `자체 수렴 루프` (기본) — implement ↔ converge 를 최대 3회. 진행이 보이고 중간 개입이 가능하다.
- `ralph 자율 루프` — ralph-loop 플러그인에 위임해 Converged 까지 무개입 반복.
  **아래 진입 조건을 모두 통과할 때만 이 옵션을 제시한다.** 하나라도 실패하면 옵션 자체를 올리지 말고, 왜 제시하지 않았는지 한 줄로 알린다.

기능 설명이 비어 있고 `spec.md` 도 없으면, 질문 대신 **무엇을 만들 것인지** 부터 되묻는다. 그것 없이는 specify가 성립하지 않는다.

### 조건부 선택 단계 제안 규칙

| 선택 단계 | 제안 조건 |
|---|---|
| `speckit-clarify` | `spec.md` 에 `NEEDS CLARIFICATION` 이 1개 이상이고, plan이 아직 없음 |
| `speckit-checklist` | plan을 이번 실행에 포함하고, 사용자가 품질·완결성 검증을 언급했거나 요구사항이 20개 이상 |
| `speckit-analyze` | tasks와 implement를 **둘 다** 이번 실행에 포함 (구현 전 정합성 점검) |
| `speckit-taskstoissues` | 사용자가 GitHub 이슈/티켓 생성을 언급 |

조건에 안 걸리면 옵션에 올리지 않는다. 사용자가 직접 요청하면 조건과 무관하게 포함한다.

### 실행 전 안전 점검

**공통 — `implement` 가 포함된 경우**

git 저장소가 아니면 실행 전에 한 줄로 알린다.

> git 저장소가 아니라 구현 결과를 되돌릴 수 없습니다. `git init` 후 진행을 권합니다.

사용자가 그대로 가겠다고 하면 진행한다. 되묻고 막지 않는다.

### ralph 자율 루프 진입 조건 (게이트)

`ralph 자율 루프` 는 사람 개입 없이 파일을 반복 수정한다. 아래를 **모두** 통과해야 선택지로 올린다.

| # | 조건 | 확인 방법 | 실패 시 |
|---|---|---|---|
| 1 | git 저장소일 것 | `git rev-parse --is-inside-work-tree` | 옵션 제외. "git 저장소가 아니라 자율 루프를 제시하지 않았습니다" |
| 2 | 작업 트리가 깨끗할 것 | `git status --porcelain` 가 비어 있음 | 커밋 또는 stash를 먼저 안내하고 옵션 제외 |
| 3 | `tasks.md` 가 존재하고 미완료 작업이 1개 이상 | `tasks_open >= 1` | 돌릴 대상이 없음. 옵션 제외 |
| 4 | 활성 ralph 루프가 없을 것 | `.claude/ralph-loop.local.md` 부재 | 1단계에서 이미 처리 |

**선택된 뒤, 루프 시작 전에 반드시 아래를 수행한다.**

1. **되돌림 지점 확보** — 전용 브랜치를 만들고 현재 상태를 커밋한다. 자율 루프의 결과를 기존 브랜치에 바로 쌓지 않는다.
   ```bash
   git switch -c sdd/ralph-$(date +%Y%m%d-%H%M%S)
   git add -A && git commit -m "chore: ralph 루프 시작 전 스냅샷" --allow-empty
   ```
2. **반복 상한 확정** — `--max-iterations` 는 **항상** 붙인다. 기본 10, 사용자가 올려도 **20을 넘기지 않는다**. 무제한(`0`)은 어떤 경우에도 쓰지 않는다.
3. **완료 약속 확정** — `--completion-promise "SDD_CONVERGED"` 를 항상 설정한다. 약속 없이 시작하면 상한에 걸릴 때까지 무조건 돈다.
4. **중단 방법 고지** — 루프 시작 직전에 아래를 그대로 출력한다.
   ```
   중단: 다른 터미널에서 rm .claude/ralph-loop.local.md
   되돌리기: git switch <원래 브랜치> (작업은 sdd/ralph-* 브랜치에 격리됨)
   진행 확인: head -8 .claude/ralph-loop.local.md
   ```

## 3단계: 순서대로 실행

선택된 단계를 **아래 고정 순서**로 실행한다. 선택 여부와 무관하게 순서는 바뀌지 않는다.

```
constitution → specify → clarify → plan → checklist → tasks → analyze → implement → converge
```

각 단계는 Skill 도구로 호출한다.

| 단계 | 호출 | args |
|---|---|---|
| constitution | `Skill(skill: "speckit-constitution")` | 사용자가 준 원칙, 없으면 빈 값 |
| specify | `Skill(skill: "speckit-specify")` | 기능 설명 원문 |
| clarify | `Skill(skill: "speckit-clarify")` | 빈 값 |
| plan | `Skill(skill: "speckit-plan")` | 사용자가 언급한 기술 스택·제약 |
| checklist | `Skill(skill: "speckit-checklist")` | 검증하려는 관점 |
| tasks | `Skill(skill: "speckit-tasks")` | 빈 값 |
| analyze | `Skill(skill: "speckit-analyze")` | 빈 값 |
| implement | `Skill(skill: "speckit-implement")` | 구현 가이드·작업 필터 |
| converge | `Skill(skill: "speckit-converge")` | 빈 값 |

**실행 규칙**

- 한 번에 한 단계씩. 앞 단계가 끝나기 전에 다음 단계를 호출하지 않는다. 산출물이 다음 단계의 입력이다.
- **작업 병렬화는 `speckit-implement` 소관이다.** `tasks.md` 의 `[P]` 마커가 붙은 작업은 그 스킬이 알아서 함께 실행한다. sdd가 작업을 쪼개거나 직렬로 되돌리지 않는다.
- 단계 시작 시 `[3/5] plan 실행 중` 형태로 한 줄만 출력한다. 장황한 중계는 하지 않는다.
- `단계별 산출물 확인` 모드면 단계 종료 후 **3줄 이내** 요약을 덧붙인다 (생성 파일 경로 + 핵심 수치).
- **중단 조건** — 다음이면 남은 단계를 멈추고 사용자에게 상황과 남은 단계를 보고한다.
  - 단계가 오류로 실패
  - 해당 단계가 요구하는 선행 산출물이 없음
  - 스킬이 사용자에게 답을 요구함 (clarify의 질문 등) → 답을 받은 뒤 이어서 진행

---

## 4단계: 수렴 루프

`implement` 와 `converge` 를 **둘 다** 선택했을 때만 적용한다. 2단계 질문 3의 답에 따라 갈린다.

### 4-A. 자체 수렴 루프 (기본)

1. `Skill(skill: "speckit-implement")`
2. `Skill(skill: "speckit-converge")`
3. 결과가 **Converged** 면 종료
4. 아니면 converge가 `tasks.md` 에 추가한 잔여 작업을 대상으로 1번으로 돌아간다
5. **최대 3회** 반복. 3회 후에도 미수렴이면 멈추고, 남은 작업과 반복해도 줄지 않는 항목을 보고한다

반복 사이에 승인을 묻지 않는다. 2회차부터는 `[수렴 2회차] 잔여 작업 4건` 처럼 한 줄 남긴다.
직전 회차 대비 미완료 작업 수가 **줄지 않으면** 3회를 채우지 않고 즉시 멈추고 보고한다.

### 4-B. ralph 자율 루프

**앞의 게이트 4개를 모두 통과하고, 스냅샷 브랜치를 만든 뒤에만 진입한다.**

`ralph-loop` 은 호출하면 되돌아오지 않는다. Stop 훅이 세션 종료를 가로채 **저장된 프롬프트**를 다시 먹이는 구조라, 이 시점 이후 sdd의 진행 상태는 유지되지 않는다. 따라서:

- **ralph 호출은 sdd가 마지막으로 하는 일이어야 한다.** 뒤에 남은 sdd 단계가 있으면 먼저 다 끝내고 호출한다.
- **넘기는 프롬프트는 자기 완결적이어야 한다.** 반복마다 이 프롬프트만 다시 주어지므로, 앞선 대화 맥락에 의존하는 문장을 쓰면 안 된다.

호출:

```
Skill(skill: "ralph-loop:ralph-loop", args: "<아래 프롬프트> --max-iterations 10 --completion-promise SDD_CONVERGED")
```

Skill 호출이 거부되거나 동작하지 않으면 Bash 폴백을 쓴다. (플러그인 명령에 `hide-from-slash-command-tool: true` 가 걸려 있어 호출이 막힐 수 있다.)

```bash
# 버전 디렉터리는 고정하지 말고 찾아서 쓴다
SETUP=$(find "$HOME/.claude/plugins/cache" -path '*ralph-loop*/scripts/setup-ralph-loop.sh' 2>/dev/null | sort -V | tail -1)
[ -x "$SETUP" ] || { echo "ralph-loop 플러그인을 찾을 수 없습니다"; exit 1; }
"$SETUP" "<프롬프트>" --max-iterations 10 --completion-promise "SDD_CONVERGED"
```

폴백도 실패하면 ralph 모드를 포기하고 **4-A 자체 수렴 루프로 전환**한다. 사용자에게 전환 사실을 한 줄로 알린다.

#### 넘길 프롬프트 (이 골격을 그대로 채워서 쓴다)

```
Spec-Driven Development 수렴 작업. 대상 기능: <FEATURE_DIR>

매 반복마다 다음을 순서대로 수행한다.
1. /speckit-implement 로 tasks.md 의 미완료 작업을 구현한다.
2. /speckit-converge 로 spec.md·plan.md 대비 잔여 작업을 점검한다.
3. 변경분을 커밋한다: git add -A && git commit -m "feat(sdd): 반복 N"

지켜야 할 범위 제한:
- tasks.md 에 있는 작업만 수행한다. 새 기능을 임의로 추가하지 않는다.
- spec.md, plan.md, .specify/ 를 수정하지 않는다. converge 가 tasks.md 에 작업을 추가하는 것은 허용한다.
- git push, git reset --hard, 브랜치 삭제, 대량 파일 삭제, 의존성 대규모 교체를 하지 않는다.
- 테스트를 삭제하거나 비활성화해서 통과시키지 않는다.

종료 조건:
- /speckit-converge 가 Converged 를 보고하면 <promise>SDD_CONVERGED</promise> 를 출력한다.
- 이 문장이 사실일 때만 출력한다. 루프를 벗어나기 위해 거짓으로 출력하지 않는다.

진행이 막힌 경우 (탈출구):
- 직전 반복 대비 미완료 작업 수가 줄지 않은 상태가 2회 연속이면, 거짓 약속을 내는 대신
  rm .claude/ralph-loop.local.md 로 루프 상태를 직접 제거해 루프를 정상 종료시킨다.
  그 뒤 무엇이 막고 있는지, 무엇을 시도했는지, 어떤 대안이 있는지 정리해 보고한다.
```

마지막 항목이 이 모드의 핵심 안전장치다. completion promise는 참일 때만 출력해야 하므로, 정체 상태에서는 약속으로 빠져나올 수 없다. 상태 파일을 직접 지우는 것이 거짓말하지 않고 루프를 끝내는 유일한 정당한 방법이다.

## 5단계: 완료 보고

마지막에 아래 형식으로 정리한다.

```
## SDD 사이클 완료 — specs/001-user-login

| 단계 | 결과 | 산출물 |
|---|---|---|
| specify | 완료 | specs/001-user-login/spec.md (요구사항 12) |
| plan    | 완료 | plan.md, research.md, data-model.md |
| tasks   | 완료 | tasks.md (작업 23) |
| implement | 완료 | 변경 파일 14 |
| converge  | Converged | — |

건너뛴 단계: clarify (미해결 항목 없음)
다음 권장: /speckit-checklist 로 요구사항 완결성 점검
```

**ralph 자율 루프로 넘긴 경우** 이 보고는 sdd가 아니라 루프 종료 시점에 작성된다. 다음을 반드시 포함한다.

- 종료 사유 — `Converged` / `max-iterations 도달` / `정체로 자체 종료` 중 무엇인지
- 작업이 쌓인 브랜치 이름 (`sdd/ralph-*`) 과 되돌리는 방법
- 반복 횟수와 커밋 수
- 미완료로 남은 작업

- 실패하거나 건너뛴 단계는 **이유와 함께** 반드시 명시한다. 조용히 빼지 않는다.
- 사용자가 요청한 범위 중 못 끝낸 게 있으면 무엇을 왜 남겼는지 명확히 적는다.

---

## 하지 않을 것

- 개별 speckit 스킬의 내부 절차를 이 스킬이 대신 수행하기 — 반드시 Skill 도구로 위임한다.
- 시작 시 한 번 받은 선택을 단계마다 다시 묻기.
- 상태 스캔 없이 `specify` 부터 무조건 시작하기 — 이미 있는 산출물을 덮어쓴다.
- `.specify/` 가 없는 디렉터리에서 진행하기.
- ralph 루프를 sdd 단계 **중간**에서 시작하기 — 뒤에 남은 단계가 실행되지 않는다.
- `--max-iterations` 없이, 또는 completion promise 없이 ralph를 켜기.
- 게이트를 통과하지 못했는데 사용자를 설득해 ralph를 켜기 — 조건이 안 되면 옵션에 올리지 않는다.
- 루프를 벗어나려고 `<promise>` 를 거짓으로 출력하기.
