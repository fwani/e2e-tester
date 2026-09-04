# Quickstart: 이상 경로 견고성 검증

**Feature**: `specs/003-error-path-hardening` | **Date**: 2026-09-04

이 문서는 이 라운드가 실제로 성립했는지 **직접 돌려 확인하는 방법**이다. 구현 코드는 담지 않는다.

---

## 0. 전제

```bash
cd backend && uv sync
cd ../frontend && npm install
```

001·002 의 구현이 이미 있어야 한다. 이 라운드는 그 위에서 이상 조작을 가한다.

**`uv run pytest` 가 아니라 `uv run python -m pytest` 여야 한다.** 실행 파일로 돌리면 현재
디렉터리가 경로에 들어가지 않아 공용 픽스처 임포트(`from tests.conftest import ...`)가 깨진다.
이 라운드와 무관한 기존 조건이지만, 그동안 문서에 잘못 적혀 있었다.

화면 검증은 **제품 서버와 제품 화면을 실제로 띄운다.** node 와 브라우저가 필요하고, 설정된
포트(백엔드·프런트엔드)가 비어 있어야 한다. 없으면 건너뛰지 않고 실패로 알린다 (RG-106).

---

## 1. 시나리오 목록이 커버리지 규칙을 만족하는가 (SC-206)

권위 목록은 `specs/003-error-path-hardening/contracts/abnormal-scenarios.json` 하나다.

```bash
cd backend && uv run python -m pytest tests/abnormal/test_catalogue.py -v
```

**기대**: 12개 조합(고장 유형 4 × 조작 면 3)이 각각 3건 이상. 식별자 중복 없음. 필드 누락 없음.

목록만 빠르게 세어 보려면:

```bash
python3 -c "
import json, collections
d = json.load(open('specs/003-error-path-hardening/contracts/abnormal-scenarios.json'))
c = collections.Counter((s['fault'], s['surface']) for s in d['scenarios'])
print('총', len(d['scenarios']), '건')
for f in d['faults']:
    print(f'{f:18}', '  '.join(f'{s}={c[(f,s)]}' for s in d['surfaces']))
"
```

---

## 2. 오류 계약이 한 곳에서만 정의되는가 (EC-006)

```bash
cd backend && uv run python -m itb.schema.export --check
cd ../frontend && npm run gen:types && git diff --exit-code src/types/generated/
```

**기대**: 둘 다 변경 없음. `backend/schema/error-response.schema.json` 이 존재하고, 프런트엔드
생성 타입이 그것과 일치한다.

손으로 쓴 복사본이 남아 있지 않은지:

```bash
grep -n 'PROJECT_NOT_OPEN' frontend/src/api/client.ts
```

**기대**: 결과 없음. `client.ts` 는 생성된 타입을 임포트만 한다.

---

## 3. 모든 오류 코드가 분류를 갖는가 (EC-001·RG-104-1)

```bash
cd backend && uv run python -m pytest tests/abnormal/test_error_contract.py -v
```

**기대**: 모든 `ErrorCode` 가 대응표에 있다. 코드를 새로 추가하고 분류를 빼면 이 검증이 실패한다.

---

## 4. 모든 요청 경로가 규약을 지키는가 (RG-104-2)

```bash
cd backend && uv run python -m pytest tests/abnormal/test_route_sweep.py -v
```

**기대**: 앱에 등록된 모든 경로가 거부 응답에서 `category` 와 `next_action` 을 담고, 오류 스키마를
만족하며, 내부 경로·스택을 노출하지 않는다. **새 경로를 추가하면 이 검증이 자동으로 포함한다.**

계약을 우회하는 오류 생성이 없는지:

```bash
cd backend && uv run python -m pytest tests/abnormal/test_no_bypass.py -v
```

---

## 5. 처리되지 않은 오류가 정상 거부와 구별되는가 (EC-003)

이 라운드가 존재하는 이유다. 구현 전에는 둘 다 `DEFINITION_INVALID` 였다.

```bash
cd backend && uv run python -m pytest tests/abnormal/test_error_contract.py -k internal -v
```

**기대**: 처리되지 않은 오류는 `code=INTERNAL_ERROR`, `category=broken`. 정상 거부는
`category=blocked`. 두 응답을 코드만 보고 구별할 수 있다.

---

## 6. 고장 유형별 검증

시나리오는 면(surface)마다 실행기 하나가 목록을 읽어 펼친다. 고장 유형별로 파일이 나뉘지 않는다.

```bash
cd backend
uv run python -m pytest tests/abnormal/test_api_surface.py -v       # 요청 경계 19건
uv run python -m pytest tests/abnormal/test_boundary_surface.py -v  # 외부 경계 14건
uv run python -m pytest tests/abnormal/test_ui_surface.py -v        # 화면 18건 (제품 UI 를 띄운다)
```

**기대**: 각 시나리오가 판정 3축을 모두 통과. 실패는 시나리오 식별자(`AS-NNN`)와 어느 축이
어긋났는지를 함께 알린다.

외부 실패 재현은 실제 외부를 무너뜨리지 않는다 — AI 클라이언트를 대체하고, 브라우저를 검증
쪽에서 닫고, 고정 앱에 지연·무응답 경로를 쓴다 (`research.md` R4).

---

## 7. 저장 원자성 (AP-042)

```bash
cd backend && uv run python -m pytest tests/abnormal/test_boundary_surface.py -k 'AS-049 or AS-050' -v
```

**기대**: 쓰기 도중 실패해도 (a) 조각난 파일이 남지 않고 (b) 원본이 그대로다. 대상은 테스트 정의
쓰기, 비밀 값 저장소 쓰기, 프로젝트 등록 쓰기 셋 모두.

직접 확인하려면 — 테스트 하나를 저장한 뒤 정의 파일을 읽어 온전한지 본다:

```bash
cd backend && uv run python -c "
import yaml, pathlib, sys
p = sorted(pathlib.Path('.').rglob('*/tests/*.yaml'))
print('정의 파일', len(p), '개')
for f in p:
    yaml.safe_load(f.read_text())   # 조각난 파일이면 여기서 실패한다
print('모두 온전함')
"
```

---

## 8. 화면 쪽 검증 — 두 층

### 8-1. 컴포넌트 층 (빠르다)

```bash
cd frontend && npm run test -- --run
```

**기대**: 공용 오류 통로가 `message` 와 `next_action` 을 **함께** 보여주고, `broken` 과 `blocked` 를
구분하며, 각 화면이 그 통로를 지난다 (RG-104-4).

### 8-2. 실브라우저 층 — 제품 UI 를 실제로 띄운다 (RG-105)

```bash
cd backend && uv run python -m pytest tests/abnormal/test_ui_surface.py -v
```

**이 층은 이 라운드에서 처음 생긴다.** 그전까지 이 저장소에는 제품 화면을 실제로 여는 검증이
하나도 없었다 — `backend/tests/e2e/` 는 요청 경계 종단이고(브라우저는 제품이 *대상 사이트*를
자동화하느라 열린다), `frontend/tests/` 는 화면 없는 환경에서 컴포넌트를 그린다.

**여기서만 판정되는 것**:

| 확인 | 시나리오 |
|---|---|
| 버튼 연타가 **실제로** 요청을 몇 번 내보내는가 | AS-024 (AP-022) |
| 화면을 벗어났다 돌아오면 무엇이 보이는가 | AS-026 (AP-023) |
| 두 창에서 같은 세션을 조작하면 어떻게 되는가 | AS-047 (AP-041) |
| 화면이 멈추는가 | 판정축 ② 전부 |

느리다 (서버 둘을 띄운다). 그래도 컴포넌트 층을 **대체하지 않고 위에 얹는다** — 둘은 잡는
것이 다르다.

---

## 9. 회귀 — 되던 것이 그대로인가 (RG-102·SC-207)

```bash
cd backend && uv run python -m pytest
cd ../frontend && npm run test -- --run && npm run typecheck
```

**기대**: 실패 0건. 이 라운드는 오류 계약을 제품 전역에서 건드리므로 이것이 가장 중요한 관문이다.

---

## 10. 완료 판정 (SC-201)

```bash
cd backend && uv run python -m pytest tests/abnormal/ -v --tb=short
```

**기대**: 목록의 **전건**이 판정 3축을 모두 통과. 미판정·불일치 0건.

실행 수단이 등록되지 않아 건너뛴 시나리오도 0건이어야 한다 (SC-211). 건너뛰기는 통과가
아니다 — 조용히 건너뛰면 "전건 통과"가 거짓이 된다.

한 건이라도 실패하면 이 라운드는 완료가 아니다. 실패한 시나리오의 식별자와 어긋난 축을 기록하고,
그것이 결함이면 고치고 시나리오 정의가 틀린 것이면 목록을 고친다.

---

## 확인이 필요한 사항

- **다른 세션이 같은 저장소를 동시에 수정 중이었다** (커밋 `725a9bb`·`8fb3fa6`). 구현 착수 전에 `git status` 와 최근 커밋을 확인한다
- `SESSION_LOST` 의 분류(`blocked`/`broken`)는 구현 단계에서 정한다. 브라우저가 사라진 원인이 외부인지 제품인지에 따라 갈린다 (`data-model.md §1.3`)
- 판정축 ②는 "무엇이 잘못됐는지와 다음 행동이 화면에 존재하는가"로 좁혀 자동 판정한다. 문구의 품질 평가는 이 라운드 범위 밖이다
