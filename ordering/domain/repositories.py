import uuid
from typing import Protocol

from ordering.domain.entities import Order


class OrderRepository(Protocol):
    """`Order` 集約の永続化を抽象化するリポジトリ。domain 層はこの Protocol にだけ依存し、
    実装(ORM を使う `DjangoOrderRepository`)には依存しない。テストではインメモリの
    フェイク実装(`ordering/tests/test_application/fakes.py`)に差し替えられる。
    """

    def save(self, order: Order) -> None: ...

    def find_by_id(self, order_id: uuid.UUID, *, for_update: bool = False) -> Order | None:
        """`for_update=True` なら行ロックを取って読む(`select_for_update`)。状態を書き換える
        ユースケースはロックして読み、同時に来た更新が互いを上書きしないようにする
        (トランザクションの中で呼ぶこと)。
        """
        ...

    def count_in_progress_by_customer(self, customer_id: uuid.UUID) -> int: ...
