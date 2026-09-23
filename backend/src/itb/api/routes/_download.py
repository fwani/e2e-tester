"""파일을 내려보낼 때 쓰는 공용 헤더 (019 T016).

014 가 엑셀 내보내기에서 만든 것을 019 공유 묶음이 그대로 필요로 한다. 베끼지 않고
**한 곳에서** 만든다 — 한쪽만 고쳐지는 날 한글 프로젝트 이름의 내려받기가 조용히
깨지고, 어느 쪽이 맞는지 정할 근거가 없다.
"""

from __future__ import annotations

import urllib.parse


def content_disposition(filename: str, *, fallback: str) -> str:
    """ASCII 대체 이름과 RFC 5987 이름을 함께 싣는다 (014 research R9).

    HTTP 헤더 값은 ISO-8859-1 이고 프로젝트 이름에는 한글이 들어간다. 두 이름을 함께
    보내면 ``filename*`` 을 이해하는 브라우저는 한글 이름을, 아닌 쪽은 ASCII 이름을 쓴다.

    이름에서 ASCII 가 하나도 남지 않을 수 있다 — 한글만으로 된 프로젝트 이름이 흔하다.
    그래서 ``fallback`` 을 받는다. 내려받는 쪽이 통로마다 다른 이름을 갖게 하려는 것이며,
    여기서 하나로 정하면 엑셀 파일이 ``.itbshare.yaml`` 로 떨어지는 날이 온다.
    """
    ascii_name = filename.encode("ascii", "ignore").decode("ascii") or fallback
    quoted = urllib.parse.quote(filename, safe="")
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quoted}"
