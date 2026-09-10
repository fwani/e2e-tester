# API 계약 — 프로젝트 이름 변경과 삭제

**Feature**: 012-project-rename-delete | 기존 계약을 **더하기만** 한다. 기존 라우트의 요청·응답
형태는 바뀌지 않는다.

## §0 프로젝트 라우트 전체 (신규는 ★)

| 메서드 | 경로 | 하는 일 | 대상 지정 |
|---|---|---|---|
| GET | `/api/project` | 열린 프로젝트 조회 | 서버 상태 |
| GET | `/api/project/list` | 목록 | — |
| POST | `/api/project/create` | 만들기 | 위치를 묻지 않는다 |
| POST | `/api/project/open` | 열기 | 본문 `path` |
| DELETE | `/api/project/registry` | **목록에서만** 치우기 | 본문 `root` |
| ★ PATCH | `/api/project/name` | 표시 이름 변경 | 본문 `root` |
| ★ POST | `/api/project/trash` | **휴지통으로 보내기** | 본문 `root` |

**경로 이름이 결과를 말한다.** `registry` 는 레지스트리만 건드리고, `trash` 는 자산을 옮긴다.
둘을 한 라우트의 플래그로 합치지 않는다 — 되돌릴 수 있는 조작과 자산을 옮기는 조작이 같은
문 뒤에 있으면, 플래그 하나 잘못 보낸 것이 사용자 자산을 옮긴다.

---

## §1 `PATCH /api/project/name` — 표시 이름 변경

**요청**

```json
{ "root": "/Users/me/.local/share/itb/projects/결제", "name": "결제 회귀" }
```

| 필드 | 규칙 |
|---|---|
| `root` | 1~4096자. **도구가 아는 프로젝트**여야 한다 — 관리 위치 아래이거나 레지스트리에 있어야 한다 (FR-419 · research R7) |
| `name` | 앞뒤 공백 제거 후 1~100자 (프로젝트 생성과 동일 규칙, FR-403) |

`extra="forbid"`.

**응답 200** — 갱신된 목록 항목 하나. `GET /api/project/list` 의 항목과 **같은 형태**다.

```json
{
  "root": "/Users/me/.local/share/itb/projects/결제",
  "name": "결제 회귀",
  "last_opened_at": "2026-09-08T04:11:00Z",
  "origin": "managed",
  "accessible": true,
  "unavailable_reason": null
}
```

**`last_opened_at` 이 변하지 않는 것이 계약의 일부다** (research R2). 이름을 고친 것은 여는
행위가 아니므로 목록 순서가 흔들려서는 안 된다.

**오류**

| 상황 | HTTP | code |
|---|---|---|
| `root` 가 도구가 모르는 경로 | 400 | `INVALID_PATH` |
| 그 자리에 프로젝트가 없다 | 404 | `PROJECT_NOT_FOUND` |
| 프로젝트 파일이 깨져 읽을 수 없다 | 400 | `DEFINITION_INVALID` |
| 프로젝트 파일을 쓸 수 없다 | 500 | `STORAGE_WRITE_FAILED` |
| `name` 이 빈 값·공백뿐·100자 초과 | 422 | (검증 실패 계약 형태) |

**불변식**

- 프로젝트 파일 쓰기가 실패하면 **레지스트리를 건드리지 않는다** (FR-402).
- 새 이름이 기존과 같으면 **파일을 쓰지 않고** 200 을 돌려준다 (FR-407).
- 이 조작은 `AppState.repository` 를 바꾸지 않는다. 열린 프로젝트의 이름을 고쳐도 **열린
  채로 남고 세션이 끊기지 않는다** (FR-404). `GET /api/project` 는 파일을 다시 읽으므로
  다음 호출부터 새 이름을 돌려준다 (FR-405).

---

## §2 `POST /api/project/trash` — 휴지통으로 보내기

**요청**

```json
{ "root": "/Users/me/.local/share/itb/projects/옛-프로젝트" }
```

`root` 규칙은 §1 과 같다.

**응답 200**

```json
{
  "root": "/Users/me/.local/share/itb/projects/옛-프로젝트",
  "name": "옛 프로젝트",
  "trashed_to": "/Users/me/.local/share/itb/trash/20260910-071530-옛-프로젝트",
  "was_open": true
}
```

| 필드 | 뜻 |
|---|---|
| `trashed_to` | 옮겨진 위치. **이 값이 되돌리는 방법 전부다** (FR-410·FR-425). 화면은 이것을 그대로 보여준다 |
| `trashed_to: null` | 요청 시점에 디렉터리가 이미 없었다. 목록에서 빼는 것으로 끝냈다 (FR-420) |
| `was_open` | 이 삭제로 열린 프로젝트가 닫혔는가. 화면이 다음 행동을 정하는 근거 (FR-416) |

**204 가 아니라 200 인 이유**: 옮겨진 위치를 돌려주지 않으면 사용자는 되돌릴 수 없다. 삭제가
파괴가 아니라 이동이라는 이 기능의 성질이 응답 형태에 그대로 드러나야 한다.

**오류**

| 상황 | HTTP | code |
|---|---|---|
| `root` 가 도구가 모르는 경로 | 400 | `INVALID_PATH` |
| 대상이 열린 프로젝트이고 살아 있는 세션이 있다 | 409 | `PROJECT_IN_USE` |
| 옮기지 못했다 (권한·공간·볼륨) | 500 | `PROJECT_DELETE_FAILED` |

**불변식 — 순서가 계약이다** (FR-414 · research R5)

1. `root` 검증 → 2. 세션 검사 → 3. `shutil.move` → 4. `registry.forget()` →
5. 열려 있었으면 `state.repository = None`

3 에서 실패하면 4·5 를 **하지 않는다.** 그러므로 `PROJECT_DELETE_FAILED` 를 받은 화면은
목록을 다시 불러오면 그 프로젝트가 **그대로 있다.** 목록에서는 사라졌는데 자산은 원래 자리에
남는 상태는 이 계약에서 발생할 수 없다.

**휴지통 자리 규칙**: `<trash_dir>/<YYYYMMDD-HHMMSS>-<원래 디렉터리 이름>`. 겹치면 `-2`, `-3`.
**덮어쓰지 않는다** (FR-415).

---

## §3 `DELETE /api/project/registry` — 바뀌지 않는다

기존 그대로다. 요청 `{ "root": "..." }`, 응답 204. **디스크의 프로젝트를 지우지 않는다.**

§2 와의 차이를 계약 수준에서 못 박는다:

| | `DELETE /registry` | `POST /trash` |
|---|---|---|
| 디스크의 파일 | **그대로** | 휴지통으로 **이동** |
| 관리 위치 프로젝트에 대한 효과 | 없음 — 스캔에 다시 걸려 목록에 돌아온다 | 목록에서 사라진다 |
| 응답 | 204 (본문 없음) | 200 + 옮겨진 위치 |
| 되돌리기 | 불필요 | `trashed_to` 의 디렉터리를 원래 자리로 옮긴다 |

---

## §4 클라이언트 (`frontend/src/api/client.ts`)

```ts
project.renameProject(root: string, name: string): Promise<ProjectListItem>
project.trash(root: string): Promise<TrashProjectResponse>
```

기존 `project.forget(root)` 는 이름도 동작도 그대로 둔다. **`delete` 라는 이름을 쓰지
않는다** — 두 조작 중 어느 쪽이 `delete` 인지 읽는 사람이 헷갈리는 순간, 화면이 잘못된
쪽을 부른다.
