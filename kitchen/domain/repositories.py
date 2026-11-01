import uuid
from typing import Protocol

from kitchen.domain.entities import Ticket


class TicketRepository(Protocol):
    """`Ticket` 集約の永続化を抽象化するリポジトリ。"""

    def save(self, ticket: Ticket) -> None: ...

    def find_by_id(self, ticket_id: uuid.UUID, *, for_update: bool = False) -> Ticket | None:
        """`for_update=True` なら行ロックを取って読む(`select_for_update`)。状態を書き換える
        ユースケースはロックして読み、同時に来た更新が互いを上書きしないようにする
        (トランザクションの中で呼ぶこと)。
        """
        ...

    def find_by_order(self, order_id: uuid.UUID) -> list[Ticket]:
        """注文の全チケット(明細の番号順)。"""
        ...
