"""픽스처 앱 정적 서버.

검증용 대상 웹 앱을 로컬에서 띄운다. npm 의존을 두지 않기 위해 표준 라이브러리만 쓴다.

    python fixtures/sample-app/serve.py [--port 4300]

정적 화면 말고 **이상 경로**도 낸다 (003 T011). 대상 사이트가 느리거나, 응답을 끝내지
않거나, HTML 이 아닌 본문을 오류와 함께 돌려주는 상황은 제품 코드에 스위치를 넣어
흉내 낼 수 없다 — 그것은 바깥에서 벌어지는 일이므로 **바깥이 그렇게 굴어야** 한다
(헌법 원칙 II · research R4).

| 경로 | 무엇이 일어나는가 | 쓰는 시나리오 |
|---|---|---|
| `/slow?ms=2000` | 그만큼 늦게 정상 화면을 준다 | AS-031 |
| `/hang` | 헤더만 보내고 본문을 **끝내지 않는다** | AS-041 |
| `/boom?status=503` | HTML 이 아닌 본문을 오류 상태와 함께 준다 | AS-017 |
| `/noisy.html` | 아주 긴 텍스트와 제어문자를 담은 요소 | AS-015 |
| `/nameless.html` | 접근 가능한 이름이 전혀 없는 요소만 | AS-016 |
| `/twin-search.html` | 접근 가능한 이름이 **같은** 검색 칸 둘 | 2026-09-11 보고 |
| `/duplicate-id.html` | **같은 `id`** 를 쓰는 입력 칸 둘 | 2026-09-11 실측 |

이 파일은 **제품 코드가 아니다.**
"""

from __future__ import annotations

import argparse
import functools
import http.server
import pathlib
import socketserver
import threading
import time
import urllib.parse

ROOT = pathlib.Path(__file__).parent

# `/hang` 이 붙잡고 있는 시간의 상한. 검증이 끝나면 서버도 정리되어야 하므로
# 무한정 잡지 않는다 — 제품이 무한정 기다리는지 재는 데는 이만큼이면 충분하다.
HANG_LIMIT_S = 60.0

# `/slow` 가 받아들이는 지연의 상한. 오타 하나로 검증이 몇 분씩 멈추지 않게 한다.
SLOW_LIMIT_MS = 30_000


class FixtureHandler(http.server.SimpleHTTPRequestHandler):
    """정적 파일 + 이상 경로. 캐시를 끄고 항상 최신 파일을 준다."""

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt: str, *args: object) -> None:  # noqa: A003
        pass

    # ─── 이상 경로 ──────────────────────────────────────────────────────────

    def do_GET(self) -> None:  # noqa: N802 - 표준 라이브러리가 정한 이름
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)

        if parsed.path == "/slow":
            self._slow(query)
            return
        if parsed.path == "/hang":
            self._hang()
            return
        if parsed.path == "/boom":
            self._boom(query)
            return
        super().do_GET()

    def _slow(self, query: dict[str, list[str]]) -> None:
        """늦게 답한다. 기다린 뒤 평범한 화면을 준다 — 실패가 아니라 지연이다."""
        try:
            delay_ms = min(int(query.get("ms", ["1000"])[0]), SLOW_LIMIT_MS)
        except ValueError:
            delay_ms = 1000
        time.sleep(max(delay_ms, 0) / 1000)

        body = (
            "<!doctype html><html lang='ko'><head><meta charset='utf-8'>"
            f"<title>느린 화면</title></head><body><h1>느린 화면</h1>"
            f"<p data-testid='slow-marker'>{delay_ms}ms 뒤에 도착했습니다.</p>"
            "<button data-testid='slow-action'>계속</button></body></html>"
        ).encode()
        self._send(200, "text/html; charset=utf-8", body)

    def _hang(self) -> None:
        """헤더를 보내고 본문을 끝내지 않는다.

        `Content-Length` 를 크게 잡아 두면 클라이언트는 나머지를 계속 기다린다. 제품이
        무한정 기다리는지(AP-031) 재는 것이 목적이므로, **상한을 두고** 그 뒤 연결을 놓는다.
        """
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", "100000")
        self.end_headers()
        try:
            self.wfile.write(b"<!doctype html><html><body><h1>...")
            self.wfile.flush()
            deadline = time.monotonic() + HANG_LIMIT_S
            while time.monotonic() < deadline:
                time.sleep(0.2)
        except OSError:
            pass  # 클라이언트가 먼저 끊었다 — 제품이 기다리기를 그만뒀다는 뜻이다

    def _boom(self, query: dict[str, list[str]]) -> None:
        """HTML 이 아닌 본문을 오류 상태와 함께 준다 (AS-017)."""
        try:
            status = int(query.get("status", ["503"])[0])
        except ValueError:
            status = 503
        if not 400 <= status <= 599:
            status = 503
        self._send(status, "application/octet-stream", b"\x00\x01\x02NOT-HTML\xff\xfe")

    def _send(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class FixtureServer(socketserver.ThreadingTCPServer):
    """요청을 스레드로 받는다.

    `/hang` 이 한 연결을 붙잡고 있는 동안에도 다른 요청이 답을 받아야 한다. 단일 스레드
    서버였다면 무응답 시나리오 하나가 나머지 전부를 멈춰 세운다.
    """

    allow_reuse_address = True
    daemon_threads = True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=4300)
    args = parser.parse_args()

    handler = functools.partial(FixtureHandler, directory=str(ROOT))
    with FixtureServer(("127.0.0.1", args.port), handler) as httpd:
        print(f"fixture app: http://127.0.0.1:{args.port}/login.html")
        httpd.serve_forever()


if __name__ == "__main__":
    main()


# 다른 곳에서 이 서버를 그대로 띄울 수 있게 남겨 둔다.
def serve_in_thread(port: int) -> tuple[FixtureServer, threading.Thread]:
    handler = functools.partial(FixtureHandler, directory=str(ROOT))
    httpd = FixtureServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, thread
