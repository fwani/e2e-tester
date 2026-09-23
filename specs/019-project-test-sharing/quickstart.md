# Phase 1 Quickstart: 공유용 내보내기·가져오기 검증 가이드

**Feature**: `019-project-test-sharing` | **Date**: 2026-09-23

구현이 끝났을 때 **실제로 돌려 확인하는** 절차다. 각 시나리오는 스펙의 사용자 스토리와 성공
기준에 대응한다. 세부 형식은 [contracts/rest-api.md](contracts/rest-api.md) 와
[data-model.md](data-model.md) 를 참조한다.

---

## 0. 준비

```bash
# 백엔드
cd backend && uv sync && uv run uvicorn itb.api.app:app --reload --port 8000

# 프론트엔드 (다른 터미널)
cd frontend && npm install && npm run dev
```

**두 사람을 흉내 내려면 데이터 디렉터리를 갈라야 한다.** 같은 장비에서 확인할 때는 환경 변수로
두 개의 작업 공간을 만든다 — 키쌍도 갈라지므로 "받은 사람이 내 암호문을 못 연다"가 실제로 재현된다.

```bash
# 보내는 쪽
XDG_DATA_HOME=/tmp/itb-a XDG_CONFIG_HOME=/tmp/itb-a-cfg uv run uvicorn itb.api.app:app --port 8000

# 받는 쪽
XDG_DATA_HOME=/tmp/itb-b XDG_CONFIG_HOME=/tmp/itb-b-cfg uv run uvicorn itb.api.app:app --port 8001
```

---

## 1. 자동 검사 (먼저 이것부터)

```bash
cd backend
uv run ruff check . && uv run ruff format --check .
uv run lint-imports                        # itb.sharing 의 두 계약 포함
uv run python -m itb.schema.export --check # share-bundle.schema.json 과 모델 일치
uv run pytest tests/unit tests/contract tests/integration tests/abnormal -q
uv run pytest tests/e2e -q                 # 왕복 시나리오 (느리다)

cd ../frontend
npm run typecheck && npm test -- --run
npm run gen:types && git diff --exit-code src/types/generated  # 생성물이 최신인가
```

**`lint-imports` 가 이 기능의 핵심 게이트다.** 두 계약이 걸린다.

- `itb.sharing` → `itb.secrets` 금지 — 민감 값이 묶음에 들어갈 경로가 없음을 구조로 보증
- `itb.sharing` → `itb.llm` / `itb.authoring` 금지 — 헌법 원칙 II

이 둘이 통과하지 않으면 나머지 검증은 의미가 없다.

---

## 2. 내보내기 (US1·US4 / FR-001~FR-010)

**준비**: 보내는 쪽에 민감 변수를 쓰는 테스트가 최소 1건 있어야 한다. 없으면 로그인 화면이
있는 대상으로 AI 작성 1건을 녹화해 만든다 (`fixtures/sample-app` 사용 가능).

### 2-1. 무엇이 나가는지 먼저 본다

```bash
curl -s localhost:8000/api/share/export/preview | python3 -m json.tool
```

**기대**:

- `plaintext_values` 에 스텝의 평문 입력값이 **가려지지 않은 채** 나온다 (US4 AS1)
- `required_values` 에 민감 변수와 값이 빈 비민감 변수가 이름·`sensitive`·쓰이는 스텝과 함께 나온다
- `start_urls` 에 프로젝트 기본값과 테스트별 URL 이 나온다 (US4 AS3)

화면에서도 같은 것을 본다: 테스트 목록 → 「공유용 내보내기」 → 확인 화면. 취소하면 파일이
만들어지지 않고 프로젝트가 그대로인지 확인한다 (US4 AS2).

### 2-2. 파일을 만든다

```bash
curl -s -X POST localhost:8000/api/share/export \
  -H 'Content-Type: application/json' -d '{}' \
  -D /tmp/headers.txt -o /tmp/bundle.itbshare.yaml
grep -i 'content-disposition\|x-itb-share' /tmp/headers.txt
head -20 /tmp/bundle.itbshare.yaml
```

**기대**: 파일 머리에 "민감 값이 들어 있지 않습니다" 주석, `bundle_version: 1`,
`required_values` 에 이름만 (값은 어디에도 없다).

### 2-3. 민감 값이 없음을 직접 확인한다 (SC-004)

```bash
# 암호문이 하나도 나타나지 않아야 한다
python3 - <<'PY'
import pathlib, yaml
sec = yaml.safe_load(pathlib.Path("/tmp/itb-a/itb/projects/<프로젝트>/secrets.local.yaml").read_text())
blob = pathlib.Path("/tmp/bundle.itbshare.yaml").read_text()
hits = [n for n, c in (sec.get("values") or {}).items() if c in blob]
print("암호문 유출:", hits or "없음")
PY

# 실제로 입력했던 비밀번호 평문으로도 검색한다
grep -c '<실제 비밀번호>' /tmp/bundle.itbshare.yaml   # 0 이어야 한다
```

**하나라도 걸리면 실패다.** 이것이 이 기능의 유일한 절대 조건이다.

### 2-4. 고른 테스트만 내보낸다 (US1 AS2)

```bash
curl -s -X POST localhost:8000/api/share/export \
  -H 'Content-Type: application/json' -d '{"test_ids":["TC-001"]}' \
  -o /tmp/one.itbshare.yaml
grep -c '^  - dsl_version' /tmp/one.itbshare.yaml   # 1
```

**빈 프로젝트**: 테스트가 없는 프로젝트에서 내보내면 `SHARE_EXPORT_EMPTY` 이고 파일이
만들어지지 않는다 (US1 AS4).

---

## 3. 가져오기 (US2 / FR-020~FR-030)

**받는 쪽 서버(8001)** 로 한다. 키가 다르므로 보내는 쪽의 암호문은 열 수 없는 상태다.

### 3-1. 계획을 본다

```bash
curl -s -X POST localhost:8001/api/share/import/plan \
  -F 'file=@/tmp/bundle.itbshare.yaml' -F 'target=new' | python3 -m json.tool
```

**기대** (US2 AS1): `tests` 에 들어올 테스트, `required_values` 에 채워야 할 값
(`already_stored: false`), `notices` 에 시작 URL 확인, `blocking: []`.

**이 시점에 디스크가 그대로인지 확인한다** — 확정 전에는 아무것도 만들지 않는다.

```bash
ls /tmp/itb-b/itb/projects/     # 새 프로젝트가 아직 없어야 한다
```

### 3-2. 확정한다

```bash
curl -s -X POST localhost:8001/api/share/import/commit \
  -H 'Content-Type: application/json' \
  -d '{"plan_id":"<위에서 받은 값>"}' | python3 -m json.tool
```

**기대** (US2 AS2): `created_tests` 가 계획과 같고, `project_root` 아래 `tests/*.yaml` 이
생겼으며, 화면 목록에 나타난다.

### 3-3. 원본과 같은지 대조한다 (SC-003의 절반)

```bash
python3 - <<'PY'
import pathlib, yaml
a = yaml.safe_load(pathlib.Path("/tmp/itb-a/itb/projects/<A>/tests/TC-001-....yaml").read_text())
b = yaml.safe_load(pathlib.Path("/tmp/itb-b/itb/projects/<B>/tests/TC-001-....yaml").read_text())
for k in ("steps", "variables", "start_url", "browser"):
    print(k, "일치" if a[k] == b[k] else "!!! 다름")
print("imported_from", b.get("imported_from"))   # 받는 쪽에만 있어야 한다
PY
```

`steps` 가 **로케이터 후보까지** 완전히 같아야 한다 (헌법 원칙 IV).

### 3-4. 이름 충돌 (US2 AS3)

같은 파일을 한 번 더 `target=new` 로 가져온다. 기존 프로젝트가 덮어써지지 않고 구분되는
이름으로 만들어지며, `project_renamed_from` 이 응답에 있고 `notices` 에 `REIMPORT` 가 붙는다.

### 3-4-1. 선언 없는 참조 (FR-047)

```bash
# 변수 선언 줄만 지운다 — 참조는 남는다
python3 - <<'PY'
import pathlib, re
t = pathlib.Path("/tmp/bundle.itbshare.yaml").read_text()
t = re.sub(r"\n    variables:\n(?:    - .*\n|      .*\n)+", "\n    variables: []\n", t, count=1)
pathlib.Path("/tmp/undeclared.yaml").write_text(t)
PY
curl -s -X POST localhost:8001/api/share/import/plan \
  -F 'file=@/tmp/undeclared.yaml' -F 'target=new' | python3 -m json.tool
```

**기대**: **거부되지 않는다.** `required_values` 에 그 변수가 `declared: false` 로 나타나고
`repaired_variables` 에도 같은 사실이 있다. `SECRET_` 로 시작하는 이름은 `sensitive: true`,
그 외는 `sensitive: false` 로 보충된다.

### 3-5. 나쁜 파일 (US2 AS4·AS5)

```bash
# 손상
sed 's/bundle_version: 1/bundle_version: [/' /tmp/bundle.itbshare.yaml > /tmp/broken.yaml
curl -s -X POST localhost:8001/api/share/import/plan -F 'file=@/tmp/broken.yaml' -F 'target=new'
# → SHARE_BUNDLE_MALFORMED, 아무것도 만들어지지 않음

# 미래 버전
sed 's/bundle_version: 1/bundle_version: 99/' /tmp/bundle.itbshare.yaml > /tmp/future.yaml
curl -s -X POST localhost:8001/api/share/import/plan -F 'file=@/tmp/future.yaml' -F 'target=new'
# → SHARE_BUNDLE_UNSUPPORTED_VERSION, 부분 복원 없음

# YAML 별칭 폭탄
printf 'bundle_version: 1\na: &x [1,1,1,1,1,1,1,1,1]\nb: &y [*x,*x,*x,*x,*x,*x,*x,*x,*x]\n' > /tmp/bomb.yaml
time curl -s -X POST localhost:8001/api/share/import/plan -F 'file=@/tmp/bomb.yaml' -F 'target=new'
# → SHARE_BUNDLE_MALFORMED, 즉시 (전개되지 않는다)
```

세 경우 모두 그 뒤 `ls /tmp/itb-b/itb/projects/` 가 그대로여야 한다.

---

## 4. 값 인계 (US3 / FR-040~FR-048)

### 4-1. 값 없이 실행하면 막힌다 (US3 AS2 / FR-044)

```bash
curl -s localhost:8001/api/tests/TC-001/readiness | python3 -m json.tool
# → runnable: false, missing_secrets: ["SECRET_INPUT_LOGIN_PW"]

curl -s -X POST localhost:8001/api/sessions \
  -H 'Content-Type: application/json' -d '{"test_id":"TC-001", ...}'
# → 409 SECRET_VALUE_MISSING
```

**브라우저가 뜨지 않아야 한다.** 이것이 이 검사의 요점이다 — 떴다면 차단 지점이 너무 뒤에 있다.

### 4-2. 키가 없을 때 (US3 AS4 / FR-045)

받는 쪽에서 키를 만들기 **전에** 가져오기를 해 본다. 가져오기 자체는 완료되고, 값을 채우려
할 때 키 생성 안내와 키 관리 화면 경로가 나온다.

```bash
curl -s localhost:8001/api/keys/status
```

### 4-3. 값을 채운다 (US3 AS1·AS3)

화면: 가져오기 결과 → 「필요한 값 채우기」 → 각 변수에 어느 테스트의 어느 스텝에서 쓰이는지가
보이는 상태로 입력.

```bash
curl -s -X PUT localhost:8001/api/secrets/SECRET_INPUT_LOGIN_PW \
  -H 'Content-Type: application/json' -d '{"value":"<받는 사람의 비밀번호>"}'

curl -s localhost:8001/api/tests/TC-001/readiness    # runnable: true
```

**평문이 다시 나타나지 않는지 확인한다**:

```bash
grep -r '<받는 사람의 비밀번호>' /tmp/itb-b/itb/projects/<B>/tests/   # 0건
curl -s localhost:8001/api/secrets                                    # 이름만, 값 없음
```

### 4-4. 실행한다 (SC-003 완성)

화면에서 테스트를 실행해 원본과 같은 결과가 나오는지 본다 — 스텝 수, 순서, 각 스텝의 성공/실패.

### 4-5. 이미 값이 있을 때 (US3 AS5 / FR-046)

같은 변수 이름을 쓰는 다른 묶음을 가져온다. 계획의 `already_stored: true` 가 나오고, 기존 값을
조용히 덮어쓰지 않으며 유지/재입력을 고를 수 있다.

### 4-5-1. 비민감 변수 값 채우기 (FR-048)

```bash
curl -s localhost:8001/api/tests/TC-001/readiness | python3 -m json.tool
# → empty_variables: ["LOGIN_ID"] 이지만 runnable 은 막히지 않는다

# 확정 시점에 함께 넣을 수도 있다
# POST /api/share/import/commit  body: {"plan_id":"...", "variable_values":{"LOGIN_ID":"platform-b"}}
grep -A3 'name: LOGIN_ID' /tmp/itb-b/itb/projects/<B>/tests/TC-001-*.yaml   # value 가 기록돼 있다
```

**민감 변수 이름을 `variable_values` 에 넣으면 400 이어야 한다** — 봉인 경로는 하나뿐이다.

### 4-6. 환경 변수로 공급 (R10)

```bash
SECRET_INPUT_LOGIN_PW='<값>' uv run uvicorn itb.api.app:app --port 8001
curl -s localhost:8001/api/tests/TC-001/readiness    # missing_secrets 비어 있음
```

봉인된 값이 없어도 막히지 않는다 — 해석 순서에서 환경 변수가 1순위다.

---

## 5. 기존 프로젝트로 합치기 (US5 / FR-021·FR-025·FR-027)

받는 쪽에 이미 `TC-001` 이 있는 프로젝트를 연 상태로 한다.

```bash
curl -s -X POST localhost:8001/api/share/import/plan \
  -F 'file=@/tmp/bundle.itbshare.yaml' -F 'target=current' | python3 -m json.tool
```

**기대** (US5 AS2): `tests[].renumbered: true`, `target_id` 가 빈 번호로 잡힌다.
확정 후 **기존 `TC-001` 과 새로 들어온 것이 둘 다** 남아 있다.

```bash
ls /tmp/itb-b/itb/projects/<B>/tests/
```

**그룹 대응** (US5 AS3): 묶음에 그룹이 있는 경우, 같은 이름의 그룹이 대상에 있으면 그 그룹의
접두어로 들어가고 없으면 만들어진다. `itb-project.yaml` 의 `groups` 를 확인한다.

**원자성** (US5 AS4): 쓰기 도중 실패를 흉내 내려면 `tests/` 의 권한을 잠깐 막는다.

```bash
chmod 500 /tmp/itb-b/itb/projects/<B>/tests
curl -s -X POST localhost:8001/api/share/import/commit -d '{"plan_id":"..."}' \
  -H 'Content-Type: application/json'
chmod 700 /tmp/itb-b/itb/projects/<B>/tests
ls /tmp/itb-b/itb/projects/<B>/tests/   # 새 파일이 하나도 없어야 한다
```

**응답이 `SHARE_IMPORT_FAILED` 인지 `SHARE_IMPORT_PARTIAL` 인지 본다.** 후자면 되돌리기까지
실패한 것이고, 남은 것이 응답에 실려 있어야 한다.

---

## 6. 규모 (SC-008)

테스트 50건짜리 프로젝트로 2장·3장을 다시 한다.

```bash
time curl -s -X POST localhost:8000/api/share/export -d '{}' \
  -H 'Content-Type: application/json' -o /tmp/big.itbshare.yaml
ls -lh /tmp/big.itbshare.yaml
time curl -s -X POST localhost:8001/api/share/import/plan \
  -F 'file=@/tmp/big.itbshare.yaml' -F 'target=new' -o /dev/null
```

**기대**: 각각 10초 이내, 화면에 진행 상황이 보이고 응답하지 않는 구간이 없다.

**상한 확인**:

```bash
# 20MB 초과 파일
python3 -c "open('/tmp/huge.yaml','w').write('bundle_version: 1\nfiller: ' + 'x'*21*1024*1024)"
curl -s -X POST localhost:8001/api/share/import/plan -F 'file=@/tmp/huge.yaml' -F 'target=new'
# → SHARE_BUNDLE_TOO_LARGE, 파싱하지 않고 거부
```

---

## 7. 완료 판정

아래가 전부 참이어야 한다.

- [ ] 1장의 자동 검사가 모두 통과한다 (특히 `lint-imports`)
- [ ] 2-3 에서 암호문·평문 비밀값이 **0건** 발견된다 (SC-004)
- [ ] 3-3 에서 스텝이 로케이터 후보까지 완전히 일치한다
- [ ] 3-5 의 세 가지 나쁜 파일 모두에서 디스크가 그대로다 (SC-006)
- [ ] 4-1 에서 브라우저가 뜨지 않고 막힌다 (FR-044) — **민감 변수만**. 빈 비민감 변수는 막지 않는다
- [ ] 3-4-1 에서 선언 없는 참조가 거부되지 않고 채울 목록에 나타난다 (FR-047)
- [ ] 4-4 에서 원본과 실행 결과가 일치한다 (SC-003)
- [ ] 5장에서 기존 테스트가 하나도 사라지지 않는다 (SC-005)
- [ ] 6장에서 50건 규모가 10초 안에 끝나고 화면이 멈추지 않는다 (SC-008)
- [ ] 2-1 → 2-2 를 화면에서 3회 조작 이내·1분 이내로 끝낼 수 있다 (SC-001)
- [ ] 3-1 → 4-3 을 화면에서 5분 이내로 끝낼 수 있다 (SC-002)
