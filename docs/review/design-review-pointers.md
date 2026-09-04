# design-review 근거 위치표 (T156 리뷰어 보조)

`scripts/review_pointers.py` 가 `specs/001-interactive-ai-test-builder/checklists/design-review.md` 에서 생성했다. **판정은 들어 있지 않다** — 각 항목이 가리키는 근거가 어느 파일 몇 번째 줄에 있는지만 해석한다.

라인 번호는 생성 시점 기준이다. 문서가 바뀌면 다시 생성한다:

```bash
python3 scripts/review_pointers.py > docs/review/design-review-pointers.md
```


## 1. 헌법 원칙 준수 증거

| 항목 | 검토 관점 | 근거 위치 | 판정 |
|---|---|---|---|
| CHK001 | Completeness | `specs/001-interactive-ai-test-builder/spec.md:367` |  |
| CHK002 | Measurability | `specs/001-interactive-ai-test-builder/spec.md:381`<br>`specs/001-interactive-ai-test-builder/spec.md:546` |  |
| CHK003 | Traceability | `specs/001-interactive-ai-test-builder/spec.md:488`<br>`specs/001-interactive-ai-test-builder/plan.md:85` |  |
| CHK004 | Clarity | `specs/001-interactive-ai-test-builder/research.md:358` |  |
| CHK005 | Clarity | `specs/001-interactive-ai-test-builder/spec.md:447` |  |
| CHK006 | Measurability | `specs/001-interactive-ai-test-builder/spec.md:407` |  |
| CHK007 | Consistency | `specs/001-interactive-ai-test-builder/spec.md:683`<br>`specs/001-interactive-ai-test-builder/plan.md:236` |  |
| CHK008 | Traceability | `specs/001-interactive-ai-test-builder/plan.md:85` |  |
| CHK009 | Gap | `specs/001-interactive-ai-test-builder/research.md:480` |  |

## 2. 멀티 탭 범위 변경의 반영 완결성

| 항목 | 검토 관점 | 근거 위치 | 판정 |
|---|---|---|---|
| CHK010 | Consistency | `specs/001-interactive-ai-test-builder/spec.md:427`<br>`specs/001-interactive-ai-test-builder/spec.md:718` |  |
| CHK011 | Completeness | `specs/001-interactive-ai-test-builder/spec.md:429`<br>`specs/001-interactive-ai-test-builder/data-model.md:234` |  |
| CHK012 | Consistency | `specs/001-interactive-ai-test-builder/spec.md:373`<br>`specs/001-interactive-ai-test-builder/spec.md:433` |  |
| CHK013 | Clarity | `specs/001-interactive-ai-test-builder/spec.md:439`<br>`specs/001-interactive-ai-test-builder/research.md:201` |  |
| CHK014 | Edge Case | `specs/001-interactive-ai-test-builder/spec.md:437` |  |
| CHK015 | Gap | `specs/001-interactive-ai-test-builder/research.md:263` |  |
| CHK016 | Coverage | `specs/001-interactive-ai-test-builder/quickstart.md:134` |  |
| CHK017 | Completeness | `specs/001-interactive-ai-test-builder/plan.md:129` |  |
| CHK018 | Clarity | `specs/001-interactive-ai-test-builder/spec.md:441`<br>`specs/001-interactive-ai-test-builder/spec.md:718` |  |
| CHK019 | Measurability | `specs/001-interactive-ai-test-builder/spec.md:273` |  |

## 3. 디자인 자산과의 정합성

| 항목 | 검토 관점 | 근거 위치 | 판정 |
|---|---|---|---|
| CHK020 | Traceability | `specs/001-interactive-ai-test-builder/checklists/requirements.md:1` |  |
| CHK021 | Gap | `specs/001-interactive-ai-test-builder/spec.md:349`<br>`specs/001-interactive-ai-test-builder/spec.md:586`<br>`specs/001-interactive-ai-test-builder/spec.md:439` |  |
| CHK022 | Coverage | `specs/001-interactive-ai-test-builder/spec.md:451` |  |
| CHK023 | Completeness | `specs/001-interactive-ai-test-builder/spec.md:540` |  |
| CHK024 | Ambiguity | `specs/001-interactive-ai-test-builder/spec.md:395`<br>`specs/001-interactive-ai-test-builder/data-model.md:154` |  |
| CHK025 | Edge Case · Gap | `specs/001-interactive-ai-test-builder/spec.md:350` |  |
| CHK026 | Consistency | `specs/001-interactive-ai-test-builder/spec.md:706` |  |
| CHK027 | Gap | `specs/001-interactive-ai-test-builder/data-model.md:234` |  |

## 4. 보안 요구사항의 빈틈

| 항목 | 검토 관점 | 근거 위치 | 판정 |
|---|---|---|---|
| CHK028 | Completeness | `specs/001-interactive-ai-test-builder/spec.md:592` |  |
| CHK029 | Gap | `specs/001-interactive-ai-test-builder/spec.md:592`<br>`specs/001-interactive-ai-test-builder/plan.md:129` |  |
| CHK030 | Traceability | `specs/001-interactive-ai-test-builder/contracts/README.md:1`<br>`specs/001-interactive-ai-test-builder/spec.md:592` |  |
| CHK031 | Gap | `specs/001-interactive-ai-test-builder/spec.md:599`<br>`specs/001-interactive-ai-test-builder/spec.md:606` |  |
| CHK032 | Ambiguity | `specs/001-interactive-ai-test-builder/spec.md:599`<br>`specs/001-interactive-ai-test-builder/spec.md:606` |  |
| CHK033 | Gap | `specs/001-interactive-ai-test-builder/spec.md:564` |  |
| CHK034 | Consistency | `specs/001-interactive-ai-test-builder/data-model.md:195`<br>`specs/001-interactive-ai-test-builder/spec.md:564` |  |
| CHK035 | Ambiguity | `specs/001-interactive-ai-test-builder/spec.md:608`<br>`specs/001-interactive-ai-test-builder/data-model.md:195` |  |
| CHK036 | Clarity | `specs/001-interactive-ai-test-builder/research.md:538` |  |
| CHK037 | Traceability | `specs/001-interactive-ai-test-builder/spec.md:579`<br>`specs/001-interactive-ai-test-builder/contracts/README.md:1` |  |
| CHK038 | Measurability | `specs/001-interactive-ai-test-builder/spec.md:571` |  |
| CHK039 | Completeness | `specs/001-interactive-ai-test-builder/data-model.md:12`<br>`specs/001-interactive-ai-test-builder/spec.md:581` |  |

## 5. 요구사항의 검증 가능성

| 항목 | 검토 관점 | 근거 위치 | 판정 |
|---|---|---|---|
| CHK040 | Coverage · Traceability | `(문서 참조 없음 — 전체를 대상으로 판단하는 항목)` |  |
| CHK041 | Clarity | `specs/001-interactive-ai-test-builder/spec.md:635`<br>`specs/001-interactive-ai-test-builder/quickstart.md:296` |  |
| CHK042 | Measurability | `specs/001-interactive-ai-test-builder/spec.md:641` |  |
| CHK043 | Measurability · Gap | `specs/001-interactive-ai-test-builder/spec.md:649` |  |
| CHK044 | Clarity | `specs/001-interactive-ai-test-builder/spec.md:666` |  |
| CHK045 | Clarity | `specs/001-interactive-ai-test-builder/research.md:594` |  |
| CHK046 | Measurability | `specs/001-interactive-ai-test-builder/spec.md:511`<br>`specs/001-interactive-ai-test-builder/spec.md:660` |  |

## 6. 상태 기계의 완결성

| 항목 | 검토 관점 | 근거 위치 | 판정 |
|---|---|---|---|
| CHK047 | Gap | `specs/001-interactive-ai-test-builder/data-model.md:234`<br>`specs/001-interactive-ai-test-builder/contracts/rest-api.md:1` |  |
| CHK048 | Gap | `specs/001-interactive-ai-test-builder/spec.md:471` |  |
| CHK049 | Gap | `specs/001-interactive-ai-test-builder/data-model.md:234` |  |
| CHK050 | Gap | `specs/001-interactive-ai-test-builder/spec.md:492`<br>`specs/001-interactive-ai-test-builder/spec.md:416` |  |
| CHK051 | Edge Case · Gap | `specs/001-interactive-ai-test-builder/spec.md:540` |  |
| CHK052 | Gap | `specs/001-interactive-ai-test-builder/data-model.md:234` |  |
| CHK053 | Consistency | `specs/001-interactive-ai-test-builder/spec.md:460`<br>`specs/001-interactive-ai-test-builder/spec.md:467` |  |
| CHK054 | Completeness | `specs/001-interactive-ai-test-builder/spec.md:273` |  |
| CHK055 | Gap | `specs/001-interactive-ai-test-builder/data-model.md:234` |  |

## 7. 이연 항목의 추적 가능성

| 항목 | 검토 관점 | 근거 위치 | 판정 |
|---|---|---|---|
| CHK056 | Completeness | `specs/001-interactive-ai-test-builder/spec.md:683` |  |
| CHK057 | Traceability | `specs/001-interactive-ai-test-builder/plan.md:236` |  |
| CHK058 | Clarity | `specs/001-interactive-ai-test-builder/contracts/step-dsl.md:1`<br>`specs/001-interactive-ai-test-builder/spec.md:706` |  |
| CHK059 | Measurability | `specs/001-interactive-ai-test-builder/research.md:103` |  |
| CHK060 | Clarity | `specs/001-interactive-ai-test-builder/spec.md:383`<br>`specs/001-interactive-ai-test-builder/spec.md:706` |  |
| CHK061 | Gap | `specs/001-interactive-ai-test-builder/spec.md:718` |  |

## 8. 가정과 의존성

| 항목 | 검토 관점 | 근거 위치 | 판정 |
|---|---|---|---|
| CHK062 | Assumption | `specs/001-interactive-ai-test-builder/research.md:45` |  |
| CHK063 | Traceability | `specs/001-interactive-ai-test-builder/spec.md:747`<br>`specs/001-interactive-ai-test-builder/spec.md:488` |  |
| CHK064 | Gap | `specs/001-interactive-ai-test-builder/quickstart.md:10` |  |
| CHK065 | Dependency | `specs/001-interactive-ai-test-builder/research.md:45`<br>`specs/001-interactive-ai-test-builder/research.md:538` |  |

## Notes

| 항목 | 검토 관점 | 근거 위치 | 판정 |
|---|---|---|---|

**항목 65건 · 앵커 미해결 0건.** 미해결은 체크리스트가 가리키는 절이 문서에 없거나 이름이 바뀐 것이므로, 그 자체가 검토 대상이다.

