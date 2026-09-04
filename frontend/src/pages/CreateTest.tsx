/**
 * 테스트 만들기. **`docs/design/CreateTest.dc.html`(1000×700) 전사.** DC-001~DC-007.
 *
 * 확정 디자인에는 **자연어 지시 입력이 없다.** 「AI로 만들기」 카드의 버튼은
 * 「지시문 쓰기」이고, 지시문은 `AiRecord.dc.html` 에서 쓴다. 001 구현이 이 화면에
 * textarea 를 끼워 넣은 것은 확정 디자인에 없는 요소를 더한 것이라 DC-007 위반이다 —
 * 여기서는 다음 화면으로 넘긴다 (DC-008).
 *
 * DR-021 — AI 를 쓸 수 없는 환경이면 **실행을 시도하기 전에** 무엇이 준비되지 않았고
 * 무엇을 하면 되는지 알린다. 눌렀는데 아무 일도 없는 것이 이 라운드가 고치는 결함이다.
 */
import { useEffect, useState } from "react";

import { ai, ApiError, type ProjectView } from "../api/client";

export interface CreateTestProps {
  project: ProjectView | null;
  onCancel: () => void;
  /** 직접 녹화 — 시작 URL 을 들고 녹화 세션으로 간다. */
  onRecord: (startUrl: string) => void;
  /** AI로 만들기 — 지시문은 다음 화면에서 쓴다 (DC-008). */
  onWriteInstruction: (startUrl: string) => void;
}

export function CreateTest({ project, onCancel, onRecord, onWriteInstruction }: CreateTestProps) {
  const [startUrl, setStartUrl] = useState(project?.default_start_url ?? "");
  const [aiReady, setAiReady] = useState<{ available: boolean; reason: string | null } | null>(null);

  // DR-021 — 화면에 들어오는 순간 확인한다. 눌러 봐야 아는 것은 늦다.
  useEffect(() => {
    void ai
      .availability()
      .then(setAiReady)
      .catch((exc: unknown) =>
        setAiReady({
          available: false,
          reason: exc instanceof ApiError ? exc.message : String(exc),
        }),
      );
  }, []);

  const urlReady = /^https?:\/\//.test(startUrl.trim());

  return (
    <div
      style={{
        width: "1000px",
        minHeight: "700px",
        background: "#EFEBE0",
        padding: "40px",
        display: "flex",
        margin: "0 auto",
      }}
    >
      <div
        style={{
          flex: "1",
          border: "3px solid #14130F",
          background: "#FFFDF6",
          boxShadow: "10px 10px 0 #14130F",
          display: "flex",
          flexDirection: "column",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "14px",
            padding: "22px 28px",
            borderBottom: "3px solid #14130F",
          }}
        >
          <div
            style={{
              fontFamily: "'Black Han Sans', 'Arial Black', Impact, sans-serif",
              fontSize: "28px",
              lineHeight: "1",
            }}
          >
            테스트 만들기
          </div>
          <div style={{ flex: "1" }} />
          <button
            aria-label="닫기"
            onClick={onCancel}
            style={{
              width: "44px",
              height: "44px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              border: "3px solid #14130F",
              background: "#EFEBE0",
              padding: 0,
              boxShadow: "none",
            }}
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="#14130F" strokeWidth="2.6">
              <path d="M4 4l8 8M12 4l-8 8" />
            </svg>
          </button>
        </div>

        <div
          style={{
            padding: "26px 28px 28px",
            display: "flex",
            flexDirection: "column",
            gap: "22px",
          }}
        >
          <div
            style={{
              font: "500 15px/1.5 'IBM Plex Sans KR', system-ui, sans-serif",
              color: "#4A473F",
              maxWidth: "620px",
              textWrap: "pretty",
            }}
          >
            만드는 방법을 고르세요. 어느 쪽으로 만들어도 같은 Step 모델로 저장되고, 실행은
            Playwright가 합니다.
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: "20px" }}>
            {/* 직접 녹화 */}
            <div
              style={{
                border: "3px solid #14130F",
                background: "#FFFDF6",
                boxShadow: "6px 6px 0 #14130F",
                padding: "22px",
                display: "flex",
                flexDirection: "column",
                gap: "14px",
                minHeight: "232px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <div
                  style={{
                    width: "46px",
                    height: "46px",
                    border: "3px solid #14130F",
                    background: "#D9502F",
                    color: "#FFFDF6",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <svg width="22" height="22" viewBox="0 0 22 22">
                    <circle cx="11" cy="11" r="6.5" fill="currentColor" />
                  </svg>
                </div>
                <div
                  style={{
                    fontFamily: "'Black Han Sans', 'Arial Black', Impact, sans-serif",
                    fontSize: "22px",
                    lineHeight: "1",
                  }}
                >
                  직접 녹화
                </div>
              </div>
              <div style={{ font: "500 15px/1.55 'IBM Plex Sans KR', system-ui, sans-serif", textWrap: "pretty" }}>
                브라우저를 직접 조작해서 테스트를 만듭니다.
              </div>
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "7px",
                  font: "400 13px/1.4 'IBM Plex Mono', ui-monospace, monospace",
                  color: "#6B675C",
                }}
              >
                <div>클릭 · 입력 · 선택 · 화면 이동을 그대로 기록</div>
                <div>기록 중 언제든 멈추고 고칠 수 있음</div>
              </div>
              <div style={{ flex: "1" }} />
              <button
                disabled={!urlReady}
                onClick={() => onRecord(startUrl.trim())}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "9px",
                  height: "48px",
                  background: "#14130F",
                  color: "#F5F2E9",
                  border: "3px solid #14130F",
                  font: "600 15px/1 'IBM Plex Sans KR', system-ui, sans-serif",
                  boxShadow: "none",
                }}
              >
                녹화 시작
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <path d="M3 8h9M8.5 4.5L12.5 8l-4 3.5" />
                </svg>
              </button>
            </div>

            {/* AI로 만들기 */}
            <div
              style={{
                border: "3px solid #14130F",
                background: "#F0EBFC",
                boxShadow: "6px 6px 0 #14130F",
                padding: "22px",
                display: "flex",
                flexDirection: "column",
                gap: "14px",
                minHeight: "232px",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <div
                  style={{
                    width: "46px",
                    height: "46px",
                    border: "3px solid #14130F",
                    background: "#7C4DDB",
                    color: "#FFFDF6",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4">
                    <path d="M12 3v5M12 16v5M3 12h5M16 12h5M6 6l3 3M15 15l3 3M18 6l-3 3M9 15l-3 3" />
                  </svg>
                </div>
                <div
                  style={{
                    fontFamily: "'Black Han Sans', 'Arial Black', Impact, sans-serif",
                    fontSize: "22px",
                    lineHeight: "1",
                  }}
                >
                  AI로 만들기
                </div>
              </div>
              <div style={{ font: "500 15px/1.55 'IBM Plex Sans KR', system-ui, sans-serif", textWrap: "pretty" }}>
                할 일을 말로 적으면 AI가 브라우저에서 해봅니다.
              </div>
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "7px",
                  font: "400 13px/1.4 'IBM Plex Mono', ui-monospace, monospace",
                  color: "#55507A",
                }}
              >
                <div>성공한 동작만 Step으로 기록</div>
                <div>다시 돌릴 때는 AI를 쓰지 않음</div>
              </div>

              {/* DR-021 — 확정 디자인이 정의하지 않은 상태. 실행 전에 알린다. */}
              {aiReady !== null && !aiReady.available && (
                <div
                  role="status"
                  style={{
                    border: "2px solid #14130F",
                    background: "#FFF9D6",
                    padding: "10px 12px",
                    font: "500 13px/1.5 'IBM Plex Sans KR', system-ui, sans-serif",
                    whiteSpace: "pre-wrap",
                  }}
                >
                  {aiReady.reason ?? "AI 를 사용할 수 없습니다."}
                </div>
              )}

              <div style={{ flex: "1" }} />
              <button
                disabled={!urlReady || aiReady === null || !aiReady.available}
                onClick={() => onWriteInstruction(startUrl.trim())}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: "9px",
                  height: "48px",
                  background: "#7C4DDB",
                  color: "#FFFDF6",
                  border: "3px solid #14130F",
                  font: "600 15px/1 'IBM Plex Sans KR', system-ui, sans-serif",
                  boxShadow: "none",
                }}
              >
                지시문 쓰기
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2.5">
                  <path d="M3 8h9M8.5 4.5L12.5 8l-4 3.5" />
                </svg>
              </button>
            </div>
          </div>

          <div
            style={{
              display: "flex",
              alignItems: "flex-end",
              gap: "16px",
              borderTop: "3px solid #14130F",
              paddingTop: "22px",
            }}
          >
            <div style={{ flex: "1", display: "flex", flexDirection: "column", gap: "8px" }}>
              <label
                htmlFor="start-url"
                style={{
                  font: "600 12px/1 'IBM Plex Mono', ui-monospace, monospace",
                  letterSpacing: "0.12em",
                  color: "#6B675C",
                  margin: 0,
                  textTransform: "none",
                }}
              >
                시작 URL
              </label>
              <input
                id="start-url"
                value={startUrl}
                onChange={(e) => setStartUrl(e.target.value)}
                placeholder="https://[대상 앱 URL]/login"
                style={{
                  display: "flex",
                  alignItems: "center",
                  height: "48px",
                  minHeight: "48px",
                  padding: "0 14px",
                  border: "3px solid #14130F",
                  background: "#FFFDF6",
                  font: "400 15px/1 'IBM Plex Mono', ui-monospace, monospace",
                }}
              />
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              <div
                style={{
                  font: "600 12px/1 'IBM Plex Mono', ui-monospace, monospace",
                  letterSpacing: "0.12em",
                  color: "#6B675C",
                }}
              >
                브라우저
              </div>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  height: "48px",
                  padding: "0 14px",
                  border: "3px solid #14130F",
                  background: "#FFFDF6",
                  font: "600 15px/1 'IBM Plex Sans KR', system-ui, sans-serif",
                }}
              >
                Chromium
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="#14130F" strokeWidth="2.4">
                  <path d="M3.5 5L7 9l3.5-4" />
                </svg>
              </div>
            </div>
          </div>

          {/* 확정 디자인이 정의하지 않은 상태 — URL 이 규격에 맞지 않을 때 (DC-009). */}
          {startUrl.trim() !== "" && !urlReady && (
            <div style={{ color: "#A83A22", font: "500 13px/1.5 'IBM Plex Sans KR', system-ui, sans-serif" }}>
              시작 URL 은 http:// 또는 https:// 로 시작해야 합니다.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
