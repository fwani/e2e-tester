# quickstart 실행 결과 — T098

**실행일**: 2026-09-04
**방법**: 서버를 `/tmp` 에서 띄우고(실행 경로 무관함을 확인하기 위해) 홈을 임시 경로로
격리한 뒤 `quickstart.md` 의 명령을 그대로 돌렸다.

```bash
cd /tmp && HOME=/tmp/itb-smoke XDG_CONFIG_HOME=... XDG_DATA_HOME=... \
  backend/.venv/bin/uvicorn itb.api.app:app --host 127.0.0.1 --port 4399
```

## 자동으로 확인한 것 — 전부 통과

| 절 | 확인 | 결과 |
|---|---|---|
| §1 | 프로젝트 없는 첫 실행이 빈 목록 + 200 | `{"projects":[],"warning":null}` ✓ |
| §1 | **경로 없이** 프로젝트 생성 (DR-001) | 201, `root` 가 `~/.local/share/itb/projects/스모크-프로젝트` ✓ |
| §1 | 만든 프로젝트가 목록에 나타남 | `accessible:true`, `origin:"managed"` ✓ |
| §1 | **서버 재시작 후에도 목록 유지** (SC-101) | 재시작 후 같은 항목 그대로 ✓ |
| §1 | 홈 밖 탐색 거절 (`/etc`) | `400 INVALID_PATH` + 읽을 수 있는 사유 ✓ |
| §1 | `..` 탈출 거절 | `400 INVALID_PATH` ✓ |
| §1 | 탐색 응답에 파일 이름 없음 | `entries` 는 `name·path·is_project` 뿐 ✓ |
| §1 | 홈 최상위에서 `parent` 가 `null` | ✓ |
| §3 | `GET /api/ai/availability` | `200 {"available":true,"reason":null}` ✓ |
| §4 | 비밀 값 목록에 값이 오지 않음 | `names` 는 `name·present` 뿐 ✓ |
| §4 | **저장된 자산에 평문 없음** (SC-010) | `grep` 결과 0건, 이름만 존재 ✓ |
| §5 | **8자 미만 암호구가 계약 형태로 거절** (SC-107) | `{"error":{"code":"DEFINITION_INVALID","message":"passphrase: 8자 이상이어야 합니다."}}` ✓ |
| §5 | 암호구 없이 키 생성 | `201` ✓ |
| §7 | 백엔드 unit + contract | **853 passed** (기준선 726) ✓ |
| §7 | `lint-imports` (원칙 II) | 3 계약 유지 ✓ |
| §7 | 프런트엔드 | **118 passed** (기준선 62) ✓ |
| §7 | `tsc --noEmit` | 통과 ✓ |
| §7 | 통합 + e2e | **107 passed** ✓ |
| §6 | `frontend/src` 에 `border-radius` 없음 (DC-004) | 0건 ✓ |

**§5 의 결과가 이 라운드의 핵심이다.** 이전에는 같은 요청이
`{"detail":[...]}` 로 나가 화면에 "요청이 실패했습니다 (422)." 만 남았다.

## 실행하지 못한 것 — 사람이 해야 한다

아래는 사람이 화면을 조작해야 확인할 수 있다. **통과했다고 적지 않는다.**

| 절 | 확인 | 왜 못 했는가 |
|---|---|---|
| §1 | 화면에 경로 입력란이 0개인지 눈으로 확인 | 자동 단언은 `ProjectSetup.test.tsx` 가 하지만, 실제 화면 확인은 사람 몫 |
| §1 | 폴더 선택기로 기존 프로젝트를 골라 열기 | UI 조작 |
| §2 | **녹화 → 중지 → Step 확인 → 저장** | 실제 브라우저 조작. 서버 쪽은 `test_stop_then_save.py` 가 덮는다 |
| §2 | 저장 없이 나갈 때 유실 경고 | UI 조작 |
| §3 | 자격 증명이 있는 환경에서 AI 가 실제로 브라우저를 모는 것 | 언어모델 호출이 필요하다 |
| §4 | Step 편집에서 **화면 이동 0회**로 비밀 값 입력 (SC-106) | UI 조작 |
| §6 | **8화면 대조 판정** (SC-108·SC-109) | 리뷰어 몫 (T099) |

## 정리

임시 홈(`/tmp/itb-smoke`)은 확인 후 지웠다. 개발자의 실제 홈에는 아무것도 남기지
않았다 — 서버를 `/tmp` 에서 띄운 것 자체가 "실행 경로가 무관하다"는 DR-001 의
확인이기도 하다.
