# Contract: 미러 조작

**Feature**: 010-headless-mirror-control | **Date**: 2026-09-09

이 문서는 **001 의 계약을 개정한다.** 개정 대상과 유지 대상을 먼저 못 박는다.

| 001 계약 | 이 문서에서 |
|---|---|
| `contracts/websocket.md` — "서버 → 클라이언트 단방향. 클라이언트는 명령을 보내지 않는다" | **그 소켓에 대해서는 그대로 유지한다.** 조작은 **새 소켓**으로 받는다 (§2) |
| `contracts/rest-api.md` — 명령은 REST | 유지. 상태 기계를 전이시키는 명령은 종전대로 REST (§3) |
| FR-047a — 미러는 입력을 전달하지 않는다 | 개정. 조작 국면에서 전달한다 (§1) |

---

## §1. 국면과 조작 가능성

조작 가능 여부는 **국면 × 조작 권한표**가 정한다. 미러 컴포넌트는 결과만 받는다
(FR-316, research R9).

| 국면 | 미러 조작 | 실제 창 전환 | 근거 |
|---|---|---|---|
| 직접 녹화 (`recording`) | ● | ● | FR-314 |
| 사람 인수 (`takeover`) | ● | ● | FR-314 |
| 일시정지 (`paused`) | ● | ● | FR-314 |
| 실행 중 (`running`) | ✕ | ✕ | FR-315 — 러너가 전진하는 중이다 |
| AI 수행 중 | ✕ | ✕ | FR-315 |
| 일시정지 전이 중 (`pausing`) | ✕ | ✕ | 아직 멈추지 않았다 |
| 실행 종료 (`finished`) | ✕ | ✕ | 조작 국면이 아니다 |
| 세션 종료·유실 (`terminated`) | ✕ | ✕ | FR-347 |

**런타임 덮어쓰기** (국면과 무관한 사정 — 기존 덮어쓰기 체계로 처리):

| 사정 | 미러 조작 | 화면이 말해야 하는 것 |
|---|---|---|
| 프레임을 한 장도 받지 못했다 | ✕ | 표시를 기다리는 중이며 아직 조작할 수 없다 (FR-333) |
| 프레임이 끊겼다 | ✕ | 화면이 멈춘 것이며 페이지가 멈춘 것이 아니다 (FR-346) |
| 1 FPS 로 강등됐다 | ● (경고 동반) | 지금 조작은 정확하지 않을 수 있다 + 전환 수단 (FR-345·FR-353a) |
| 조작 채널이 붙지 않았다 | ✕ | 조작 통로가 준비되지 않았다 |

---

## §2. 조작 채널 (새 WebSocket)

```
WS /api/sessions/{session_id}/control
```

**방향**: 양방향. 클라이언트가 조작 사건을 보내고, 서버는 **거절 사유와 채널 상태만**
보낸다. 프레임은 이 소켓으로 흐르지 않는다.

**수립 조건**
- 세션이 존재하고 **조작 국면**이어야 한다. 아니면 수립을 거절한다 (FR-342).
- 세션당 하나. 이미 열려 있으면 새 접속을 거절한다 (명세 Out of Scope — 한 세션당 한 조작자).

**서버가 닫는 경우**
- 관찰 국면으로 전이 (FR-342)
- 세션 종료·유실 (FR-347)

닫을 때 사유를 보낸다. 클라이언트가 이유 없이 끊긴 것으로 보게 두지 않는다.

### 클라이언트 → 서버

```json
{ "kind": "pointer.down", "tab": 0, "x": 412.5, "y": 233.0,
  "button": "left", "frameSeq": 1841 }
```

받는 `kind` 는 [data-model.md §1](../data-model.md) 의 목록으로 **한정된다.**
목록 밖은 사건을 버리고 사유를 돌려준다 (FR-344).

| `kind` | 필수 필드 | 대상 브라우저로 보내는 것 |
|---|---|---|
| `pointer.down` / `pointer.up` | `x`,`y`,`button` | `Input.dispatchMouseEvent` mousePressed/mouseReleased |
| `pointer.move` | `x`,`y` | `Input.dispatchMouseEvent` mouseMoved |
| `wheel` | `x`,`y`,`deltaX`,`deltaY` | `Input.dispatchMouseEvent` mouseWheel |
| `key.down` / `key.up` | `key`,`code`,`modifiers` | `Input.dispatchKeyEvent` |
| `text.insert` | `text` | `Input.insertText` |
| `ime.compose` | `text`,`compositionRange` | `Input.imeSetComposition` |
| `ime.commit` | `text` | `Input.insertText` |
| `file.attach` | `fileIds` | `DOM.setFileInputFiles` |

**이 표가 채널의 상한이다.** 여기 없는 CDP 명령은 이 채널로 보낼 수 없다 — 미러의
`_ALLOWED_COMMANDS` 가 프레임 쪽에서 지키던 성질을 조작 쪽에서 유지한다 (research R5).

**검증** (경계에서, FR-341): `x`·`y` 는 프레임 표시 범위 안, `text` 길이 상한 이하,
`modifiers` 는 알려진 비트, `tab` 은 실재하는 탭. 하나라도 어기면 사건을 **버리고**
사유를 돌려준다 — 잘라서 보내지 않는다.

**끌어놓기** (FR-318): `pointer.down` → `pointer.move`* → `pointer.up` 으로 표현된다.
채널이 닫히거나 `suspended` 가 될 때 **누른 상태로 남은 포인터가 있으면 서버가
`pointer.up` 을 보낸다.** 클라이언트의 성실함에 의존하지 않는다.

### 서버 → 클라이언트

```json
{ "type": "control_rejected", "reason": "...", "kind": "pointer.down" }
{ "type": "control_state", "state": "open" | "suspended", "reason": "..." }
```

조작이 성공했다는 응답은 **보내지 않는다.** 성공의 증거는 프레임이다 — 응답을 기다리게
만들면 FR-327a·FR-336 이 깨진다.

---

## §3. REST

### 브라우저 요구 응답

```
POST /api/sessions/{session_id}/prompts/{prompt_id}
```

```json
{ "accept": true, "text": "...", "fileIds": ["f_a1b2"] }
```

요구가 이미 해소됐거나 `prompt_id` 가 그 세션의 것이 아니면 거절한다 (FR-340).

### 파일 업로드

```
POST /api/sessions/{session_id}/files      (multipart)
```

응답:

```json
{ "fileId": "f_a1b2", "displayName": "sample.txt", "size": 5 }
```

- 파일당 크기 상한·세션당 개수 상한을 넘으면 **사유와 함께 거절** (FR-337a).
- 저장 경로는 `fileId` 로 만든다. 사용자가 보낸 이름을 경로에 쓰지 않는다 (FR-337c).
- 세션 종료·유실 시 지운다 (FR-337b).

### 조작 위치 전환

```
POST /api/sessions/{session_id}/control-surface
```

```json
{ "surface": "window" }
```

- `window` 로 전환하면 실제 창을 열고, 세션 상태·녹화를 유지한다 (FR-349).
- 창을 띄울 수 없는 환경이면 **사유와 함께 거절한다** (FR-351).
- 이 전환은 **사용자 요청으로만** 일어난다. 서버가 스스로 하지 않는다 (FR-353).

---

## §4. 관찰 WS 의 변경 (기존 소켓)

방향은 **바뀌지 않는다.** 서버 → 클라이언트 단방향을 유지한다.

### `mirror_frame` — 필드 추가

```json
{ "type": "mirror_frame", "tab": 0,
  "data": "<base64 jpeg>",
  "width": 1600, "height": 1200,
  "pageScale": 1, "offsetTop": 0, "seq": 1841 }
```

`width`·`height` 의 의미는 **바뀌지 않는다** — 대상 화면 크기다. 프레임의 실제 픽셀
크기는 보내지 않는다 (data-model §2).

기존 클라이언트가 새 필드를 무시해도 종전과 같이 동작한다. 추가만 있고 제거·의미 변경이
없다.

### `browser_prompt` — 새 이벤트

```json
{ "type": "browser_prompt", "promptId": "p_7f3",
  "kind": "dialog.confirm", "message": "...", "blocking": true }
```

```json
{ "type": "browser_prompt_resolved", "promptId": "p_7f3" }
```

`message` 는 **대상 페이지에서 온 값**이다. 표시할 때 이스케이프한다 (헌법 보안 요건 —
외부 입력은 경계에서 검증한다).

### `control_surface` — 새 이벤트

```json
{ "type": "control_surface", "surface": "mirror" | "window" }
```

---

## §5. 계약 불변식

1. **관찰 소켓은 조작을 받지 않는다.** 방향 계약을 이 기능이 깨지 않는다.
2. **조작 채널은 프레임을 보내지 않는다.** 두 통로가 서로를 막지 않는 것이 FR-336 이다.
3. **조작 채널이 받을 수 있는 것은 §2 의 표로 한정된다.** 임의 CDP 명령·스크립트 실행
   경로가 없다 (FR-344).
4. **조작 채널의 어떤 상태도 실행 상태 기계를 전이시키지 않는다** (FR-348).
5. **조작 성공 응답이 없다.** 성공의 증거는 프레임이다.
6. **서버의 접근 범위는 넓어지지 않는다.** 루프백 바인딩 전제를 유지한다 (FR-343).
