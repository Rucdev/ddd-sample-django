import uuid
from collections.abc import Iterable

from kitchen.domain.events import CookingCompleted, CookingStarted
from kitchen.domain.exceptions import InvalidTicketTransition
from kitchen.domain.value_objects import TicketItem, TicketStatus
from shared.domain.entity import Entity


class Ticket(Entity):
    """調理チケット。集約ルート。注文 1 件につき 1 枚。

    ordering の `OrderPlaced` を受けて作られる(kitchen/CONTEXT.md 参照)。キッチンは
    注文の金額やお客様には関心がなく、「何を作るか」と「調理の進み具合」だけを扱う。
    """

    def __init__(
        self,
        *,
        ticket_id: uuid.UUID,
        order_id: uuid.UUID,
        items: Iterable[TicketItem],
        status: TicketStatus = TicketStatus.QUEUED,
    ) -> None:
        super().__init__()
        self.id = ticket_id
        self.order_id = order_id
        self.items = tuple(items)
        self.status = status

    @classmethod
    def open(cls, *, order_id: uuid.UUID, items: Iterable[TicketItem]) -> "Ticket":
        return cls(ticket_id=uuid.uuid4(), order_id=order_id, items=items)

    def start_cooking(self) -> None:
        self._transition(TicketStatus.QUEUED, TicketStatus.COOKING, "start cooking")
        self.record_event(CookingStarted(ticket_id=self.id, order_id=self.order_id))

    def complete(self) -> None:
        self._transition(TicketStatus.COOKING, TicketStatus.DONE, "be completed")
        self.record_event(CookingCompleted(ticket_id=self.id, order_id=self.order_id))

    def cancel(self) -> None:
        """注文のキャンセルを受けてチケットを取り消す。作り始めたものは取り消せない。

        ordering 側でも「調理開始後はキャンセル不可」を判定しているので通常ここで
        失敗することはないが、キッチン自身の不変条件としても守っておく(失敗すれば
        同期イベントのため注文のキャンセルごとロールバックされる)。
        """
        self._transition(TicketStatus.QUEUED, TicketStatus.CANCELLED, "be cancelled")

    def _transition(self, expected: TicketStatus, to: TicketStatus, action: str) -> None:
        if self.status != expected:
            raise InvalidTicketTransition(self.id, self.status, action)
        self.status = to
