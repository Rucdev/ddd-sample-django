import uuid
from collections.abc import Iterable
from dataclasses import replace

from ordering.domain.events import OrderCancelled, OrderedItem, OrderPickedUp, OrderPlaced
from ordering.domain.exceptions import (
    EmptyOrder,
    InvalidBillTransition,
    InvalidOrderTransition,
    OrderLineNotFound,
    SeatNotInUse,
)
from ordering.domain.value_objects import (
    NO_DISCOUNT,
    ZERO_YEN,
    BillStatus,
    DiscountRate,
    LineCookingStatus,
    Money,
    OrderLine,
    OrderStatus,
    OrderType,
)
from shared.domain.entity import Entity


class Order(Entity):
    """注文。集約ルート。

    「お客様が 1 回の会計でまとめて頼んだ商品と、その受け渡しの進み具合」を表す
    (ordering/CONTEXT.md 参照)。明細(OrderLine)は集約の内側にあり、外から個別に
    変更させない。

    注文には持ち帰り(TAKEOUT)と店内(DINE_IN)の 2 種類がある(OrderType 参照)。
    持ち帰りは会員(`customer_id`)が、店内は席の会計(`bill_id`)が注文の持ち主になる。
    どちらか一方だけを持つ。
    """

    def __init__(
        self,
        *,
        order_id: uuid.UUID,
        lines: Iterable[OrderLine],
        order_type: OrderType = OrderType.TAKEOUT,
        customer_id: uuid.UUID | None = None,
        bill_id: uuid.UUID | None = None,
        discount_rate: DiscountRate = NO_DISCOUNT,
        status: OrderStatus = OrderStatus.PLACED,
    ) -> None:
        super().__init__()
        if order_type == OrderType.TAKEOUT and (customer_id is None or bill_id is not None):
            raise ValueError("A takeout order belongs to a customer, not to a bill")
        if order_type == OrderType.DINE_IN and (bill_id is None or customer_id is not None):
            raise ValueError("A dine-in order belongs to a bill, not to a customer")
        self.id = order_id
        self.order_type = order_type
        self.customer_id = customer_id
        self.bill_id = bill_id
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
        """持ち帰りの注文を受け付ける。ID はここで採番する(DB の自動採番に頼ると、保存前の
        エンティティが ID を持てない)。

        `discount_rate` は会員ランクに応じた割引率(ordering.domain.value_objects.discount_rate_for_rank
        参照)。呼び出し側(application 層)が会員ランクから引き当てて渡す。
        """
        order = cls(
            order_id=uuid.uuid4(),
            order_type=OrderType.TAKEOUT,
            customer_id=customer_id,
            lines=lines,
            discount_rate=discount_rate,
        )
        order._record_placed()
        return order

    @classmethod
    def place_at_seat(cls, *, bill: "Bill", lines: Iterable[OrderLine]) -> "Order":
        """席からの注文(店内)を受け付ける。会員登録は要らず、席の会計に紐づける。

        会計が開いている(= 席が使用中)ときだけ受け付ける。会員ではないので割引はない。
        """
        bill.ensure_open()
        order = cls(
            order_id=uuid.uuid4(),
            order_type=OrderType.DINE_IN,
            bill_id=bill.id,
            lines=lines,
        )
        order._record_placed()
        return order

    def _record_placed(self) -> None:
        if not self.lines:
            raise EmptyOrder()
        self.record_event(
            OrderPlaced(
                order_id=self.id,
                customer_id=self.customer_id,
                items=tuple(
                    OrderedItem(line_no=no, name=line.name, quantity=line.quantity)
                    for no, line in enumerate(self.lines, start=1)
                ),
            )
        )

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
        """持ち帰りの注文をお客様が受け取る。店内の注文は受け取りではなく提供(serve)する。"""
        self._ensure_type(OrderType.TAKEOUT, "be picked up")
        self._transition(OrderStatus.READY, OrderStatus.PICKED_UP, "be picked up")
        assert self.customer_id is not None  # 持ち帰りの注文は必ず会員がいる(__init__ で検査済み)
        self.record_event(
            OrderPickedUp(order_id=self.id, customer_id=self.customer_id, total=self.total.amount)
        )

    def serve(self) -> None:
        """店内の注文を店員が席まで運んだ(提供完了)。支払いは会計でまとめて行うので、
        ここではイベントを出さない。
        """
        self._ensure_type(OrderType.DINE_IN, "be served")
        self._transition(OrderStatus.READY, OrderStatus.SERVED, "be served")

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

    def _ensure_type(self, expected: OrderType, action: str) -> None:
        if self.order_type != expected:
            raise InvalidOrderTransition(self.id, f"{self.order_type} order", action)

    def _transition(self, expected: OrderStatus, to: OrderStatus, action: str) -> None:
        if self.status != expected:
            raise InvalidOrderTransition(self.id, self.status, action)
        self.status = to


class Bill(Entity):
    """会計。集約ルート。

    「席の利用 1 回分の、店内注文のまとめ払い」を表す(ordering/CONTEXT.md 参照)。席の利用が
    始まると開き(OPEN)、その間に席から頼んだ注文はすべてこの会計に紐づいて明細として残る。
    席の利用が終わると支払済(PAID)になり、次にその席が使われるときは新しい会計が開く。

    注文(Order)は別の集約なので、会計は注文を抱えず、注文の側が `bill_id` を持つ。会計の
    金額は紐づく注文から計算する(`amount_due`)。
    """

    def __init__(
        self,
        *,
        bill_id: uuid.UUID,
        seat_id: uuid.UUID,
        seat_code: str,
        status: BillStatus = BillStatus.OPEN,
    ) -> None:
        super().__init__()
        self.id = bill_id
        # 席は seating モジュールのもの。ID を値として持ち、表示用に席コードを写しておく。
        self.seat_id = seat_id
        self.seat_code = seat_code
        self.status = status

    @classmethod
    def open(cls, *, seat_id: uuid.UUID, seat_code: str) -> "Bill":
        """席の利用が始まったときに会計を開く。"""
        return cls(bill_id=uuid.uuid4(), seat_id=seat_id, seat_code=seat_code)

    @property
    def is_open(self) -> bool:
        return self.status == BillStatus.OPEN

    def ensure_open(self) -> None:
        """この会計に注文を足してよいか。支払済の会計には足せない(席の利用が終わっている)。"""
        if not self.is_open:
            raise SeatNotInUse(self.seat_id)

    def settle(self) -> None:
        """支払完了。席の利用が終わったとき(退席)に呼ばれる。"""
        if not self.is_open:
            raise InvalidBillTransition(self.id, self.status, "be settled")
        self.status = BillStatus.PAID

    def amount_due(self, orders: Iterable[Order]) -> Money:
        """会計の金額 = この会計に紐づく注文の合計の和。キャンセルした注文は含めない。"""
        return sum(
            (
                order.total
                for order in orders
                if order.bill_id == self.id and order.status != OrderStatus.CANCELLED
            ),
            ZERO_YEN,
        )
