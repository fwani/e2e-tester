"""암호구로 잠긴 비밀키의 **잠금 해제 상태**. FR-089e-3.

암호구는 비밀키 파일을 **디스크에서** 보호한다 — 파일이 유출돼도 그것만으로는 봉인된
값을 열 수 없다는 층이다. 그 보호는 파일에 관한 것이고, **실행 중인 프로세스가 암호구를
들고 있는 것과 상충하지 않는다.** `ssh-agent` 가 같은 모양이다.

예전에는 실행 시점 암호구를 환경 변수 ``ITB_KEY_PASSPHRASE`` 로만 받았다. 그러면
**키 관리 화면에서 암호구를 입력해 키를 만든 사용자가, 같은 암호구를 셸에 다시 넣고
백엔드를 재기동해야** 민감 변수를 쓸 수 있었다. 화면에서 이미 받은 것을 화면이 쓰지
못하는 것은 결함이다. 이 자리가 그것을 잇는다 — 생성·교체·잠금 해제로 확인된 암호구를
프로세스가 기억하고, 실행 시점 복호화가 그것을 쓴다.

**디스크에 쓰지 않는다.** 기억은 이 프로세스의 수명까지다. 백엔드를 다시 띄우면 다시
잠기고, 사용자는 화면에서 잠금을 해제한다. 환경 변수 경로는 사람이 없는 실행(CI·헤드리스)
을 위해 그대로 남는다 — `app.py` 가 기동 시점에 한 번 확인해 이 자리에 넣는다.

**응답에 절대 담지 않는다.** 밖으로 나가는 것은 `held` — 들고 있는지 여부뿐이다.
"""

from __future__ import annotations

from itb.secrets.keys import KeyPaths, load_private


class KeyUnlock:
    """이 프로세스가 들고 있는 암호구. 메모리에만 있다.

    `slots` 로 속성을 고정한다 — 이 객체에 다른 이름으로 값이 붙는 일을 막는다.
    """

    __slots__ = ("_passphrase",)

    def __init__(self) -> None:
        self._passphrase: str | None = None

    @property
    def held(self) -> bool:
        """암호구를 들고 있는가. **값 자체는 노출하지 않는다.**"""
        return self._passphrase is not None

    @property
    def passphrase(self) -> str | None:
        """실행 시점 복호화에 넘길 암호구.

        호출자는 이것을 `load_private_or_reason` 에 그대로 넘긴다. `None` 이면 그쪽이
        환경 변수를 본다 — 두 경로가 한 줄로 합쳐진다.
        """
        return self._passphrase

    def remember(self, passphrase: str) -> None:
        """확인된 암호구를 기억한다. **확인은 호출자 책임이다** — `unlock` 을 쓰면 함께 된다.

        생성·교체 직후에 쓴다. 그 시점의 암호구는 방금 그 키를 만든 값이므로 맞는 것이
        확실하다. 다시 KDF 를 돌려 확인하는 것은 낭비다.
        """
        self._passphrase = passphrase

    def forget(self) -> bool:
        """기억을 지운다. 들고 있던 것이 있었으면 True.

        키를 지우거나 사용자가 다시 잠글 때 부른다. 남겨 두면 새로 만든 다른 암호구의
        키에 옛 암호구를 시도해 "암호구가 올바르지 않습니다" 로 헤매게 된다.
        """
        had = self._passphrase is not None
        self._passphrase = None
        return had

    def unlock(self, paths: KeyPaths, passphrase: str) -> None:
        """암호구가 **실제로 이 키를 여는지 확인한 뒤** 기억한다.

        확인 없이 기억하면 틀린 암호구가 조용히 들어앉고, 사용자는 잠금이 해제된 줄 알다가
        실행 도중에 실패를 본다. 여기서 걸러 그 자리에서 알린다.

        `load_private` 가 사유를 구분해 던진다 — 키가 없으면 `KeyMissingError`, 암호구가
        틀리면 `PassphraseError`, 암호구가 걸려 있지 않은 키면 역시 `PassphraseError`.
        호출자가 그대로 사용자에게 보여줄 수 있다.
        """
        load_private(paths, passphrase)
        self._passphrase = passphrase
