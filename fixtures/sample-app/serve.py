"""픽스처 앱 정적 서버.

검증용 대상 웹 앱을 로컬에서 띄운다. npm 의존을 두지 않기 위해 표준 라이브러리만 쓴다.

    python fixtures/sample-app/serve.py [--port 4300]
"""

from __future__ import annotations

import argparse
import functools
import http.server
import pathlib
import socketserver

ROOT = pathlib.Path(__file__).parent


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    """요청 로그를 줄인 핸들러. 캐시를 끄고 항상 최신 파일을 준다."""

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt: str, *args: object) -> None:  # noqa: A003
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=4300)
    args = parser.parse_args()

    handler = functools.partial(QuietHandler, directory=str(ROOT))
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", args.port), handler) as httpd:
        print(f"fixture app: http://127.0.0.1:{args.port}/login.html")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
