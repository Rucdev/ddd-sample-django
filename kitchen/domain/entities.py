import uuid

from kitchen.domain.events import CookingCompleted, CookingStarted
from kitchen.domain.exceptions import InvalidTicketTransition
from kitchen.domain.value_objects import TicketItem, TicketStatus
from shared.domain.entity import Entity


class Ticket(Entity):
    """調理チケット。集約ルート。注文明細 1 行(商品 × 数量)につき 1 枚。

    ordering の `OrderPlaced` を受けて、明細の数だけ作られる(kitchen/CONTEXT.md 参照)。
    キッチンは商品ごとに作るので、チケットも商品ごとに独立して進む。同じ注文のチケット
    同士の足並みはそろえない(注文としての「受取可」は ordering が明細の状況から決める)。
    """

    def __init__(
        self,
        *,
        ticket_id: uuid.UUID,
        order_id: uuid.UUID,
        line_no: int,
        item: TicketItem,
        status: TicketStatus = TicketStatus.QUEUED,
    ) -> None:
        super().__init__()
        self.id = ticket_id
        self.order_id = order_id
        self.line_no = line_no  # 注文の中での明細の番号。ordering へ進み具合を返すときに使う
        self.item = item
        self.status = status

    @classmethod
    def open(cls, *, order_id: uuid.UUID, line_no: int, item: TicketItem) -> "Ticket":
        return cls(ticket_id=uuid.uuid4(), order_id=order_id, line_no=line_no, item=item)

    def start_cooking(self) -> None:
        self._transition(TicketStatus.QUEUED, TicketStatus.COOKING, "start cooking")
        self.record_event(
            CookingStarted(ticket_id=self.id, order_id=self.order_id, line_no=self.line_no)
        )

    def complete(self) -> None:
        self._transition(TicketStatus.COOKING, TicketStatus.DONE, "be completed")
        self.record_event(
            CookingCompleted(ticket_id=self.id, order_id=self.order_id, line_no=self.line_no)
        )

    def cancel(self) -> None:
        """注文のキャンセルを受けてチケットを取り消す。作り始めたものは取り消せない。

        ordering 側でも「どれか 1 品でも作り始めたらキャンセル不可」を判定しているので通常
        ここで失敗することはないが、キッチン自身の不変条件としても守っておく(失敗すれば
        同期イベントのため注文のキャンセルごとロールバックされる)。
        """
        self._transition(TicketStatus.QUEUED, TicketStatus.CANCELLED, "be cancelled")

    def _transition(self, expected: TicketStatus, to: TicketStatus, action: str) -> None:
        if self.status != expected:
            raise InvalidTicketTransition(self.id, self.status, action)
        self.status = to
