import uuid
from collections.abc import Iterable
from dataclasses import replace

from ordering.domain.events import OrderCancelled, OrderedItem, OrderPickedUp, OrderPlaced
from ordering.domain.exceptions import EmptyOrder, InvalidOrderTransition, OrderLineNotFound
from ordering.domain.value_objects import (
    NO_DISCOUNT,
    ZERO_YEN,
    DiscountRate,
    LineCookingStatus,
    Money,
    OrderLine,
    OrderStatus,
)
from shared.domain.entity import Entity


class Order(Entity):
    """注文。集約ルート。

    「お客様が 1 回の会計でまとめて頼んだ商品と、その受け渡しの進み具合」を表す
    (ordering/CONTEXT.md 参照)。明細(OrderLine)は集約の内側にあり、外から個別に
    変更させない。
    """

    def __init__(
        self,
        *,
        order_id: uuid.UUID,
        customer_id: uuid.UUID,
        lines: Iterable[OrderLine],
        discount_rate: DiscountRate = NO_DISCOUNT,
        status: OrderStatus = OrderStatus.PLACED,
    ) -> None:
        super().__init__()
        self.id = order_id
        self.customer_id = customer_id
        self.lines = tuple(lines)
        self.discount_rate = discount_rate
        self.status = status

    @classmethod
    def place(
        cls,
        *,
        customer_id: uuid.UUID,
        lines: Iterable[OrderLine],
        discount_rate: DiscountRate = NO_DISCOUNT,
    ) -> "Order":
        """注文を受け付ける。ID はここで採番する(DB の自動採番に頼ると、保存前のエンティティが ID を持てない)。

        `discount_rate` は会員ランクに応じた割引率(ordering.domain.value_objects.discount_rate_for_rank
        参照)。呼び出し側(application 層)が会員ランクから引き当てて渡す。
        """
        order = cls(
            order_id=uuid.uuid4(),
            customer_id=customer_id,
            lines=lines,
            discount_rate=discount_rate,
        )
        if not order.lines:
            raise EmptyOrder()
        order.record_event(
            OrderPlaced(
                order_id=order.id,
                customer_id=customer_id,
                items=tuple(
                    OrderedItem(line_no=no, name=line.name, quantity=line.quantity)
                    for no, line in enumerate(order.lines, start=1)
                ),
            )
        )
        return order

    # --- 金額 ---------------------------------------------------------------

    @property
    def subtotal(self) -> Money:
        return sum((line.subtotal for line in self.lines), ZERO_YEN)

    @property
    def discount(self) -> Money:
        return self.discount_rate.discount_for(self.subtotal)

    @property
    def total(self) -> Money:
        return self.subtotal - self.discount

    # --- ステータス遷移 -------------------------------------------------------
    # 遷移元が想定外なら InvalidOrderTransition を投げる。どの遷移が許されるかは
    # OrderStatus の docstring の図を参照。

    # キッチンは明細(商品)ごとに作るので、調理の進み具合は明細単位で届く。注文としての
    # 「調理中」「受取可」は、届いた明細の状況から注文自身が決める(キッチンは注文単位の
    # 足並みを気にしない)。

    def start_cooking_line(self, line_no: int) -> None:
        """明細 1 行の調理が始まった(kitchen の `CookingStarted` を受けて呼ばれる)。
        最初の 1 行が始まったところで注文は「調理中」になる。
        """
        if self.status not in (OrderStatus.PLACED, OrderStatus.PREPARING):
            raise InvalidOrderTransition(self.id, self.status, "start cooking")
        self._advance_line(line_no, LineCookingStatus.WAITING, LineCookingStatus.COOKING)
        self.status = OrderStatus.PREPARING

    def complete_cooking_line(self, line_no: int) -> None:
        """明細 1 行の調理が終わった(kitchen の `CookingCompleted` を受けて呼ばれる)。
        全部の明細ができあがったら注文は「受取可」になる。
        """
        if self.status != OrderStatus.PREPARING:
            raise InvalidOrderTransition(self.id, self.status, "complete cooking")
        self._advance_line(line_no, LineCookingStatus.COOKING, LineCookingStatus.DONE)
        if all(line.cooking_status == LineCookingStatus.DONE for line in self.lines):
            self.status = OrderStatus.READY

    @property
    def cooked_line_count(self) -> int:
        """できあがった明細の数(画面で「2/3 品できあがり」と出す用)。"""
        return sum(1 for line in self.lines if line.cooking_status == LineCookingStatus.DONE)

    def pick_up(self) -> None:
        self._transition(OrderStatus.READY, OrderStatus.PICKED_UP, "be picked up")
        self.record_event(
            OrderPickedUp(order_id=self.id, customer_id=self.customer_id, total=self.total.amount)
        )

    def cancel(self) -> None:
        """キャンセルできるのは調理開始前(PLACED)だけ。作り始めた商品は取り消せない。"""
        self._transition(OrderStatus.PLACED, OrderStatus.CANCELLED, "be cancelled")
        self.record_event(OrderCancelled(order_id=self.id, customer_id=self.customer_id))

    def _advance_line(self, line_no: int, expected: LineCookingStatus, to: LineCookingStatus) -> None:
        if not 1 <= line_no <= len(self.lines):
            raise OrderLineNotFound(self.id, line_no)
        line = self.lines[line_no - 1]
        if line.cooking_status != expected:
            raise InvalidOrderTransition(
                self.id, f"line {line_no} {line.cooking_status}", f"move line {line_no} to {to}"
            )
        lines = list(self.lines)
        lines[line_no - 1] = replace(line, cooking_status=to)
        self.lines = tuple(lines)

    def _transition(self, expected: OrderStatus, to: OrderStatus, action: str) -> None:
        if self.status != expected:
            raise InvalidOrderTransition(self.id, self.status, action)
        self.status = to
