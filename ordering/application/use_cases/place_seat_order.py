from django.db import transaction

from menu.public import get_menu_item
from ordering.application.dto import OrderDTO, PlaceSeatOrderInput
from ordering.domain.entities import Order
from ordering.domain.exceptions import MenuItemNotAvailable, SeatNotInUse
from ordering.domain.repositories import BillRepository, OrderRepository
from ordering.domain.value_objects import Money, OrderLine
from shared.infrastructure.event_bus import publish


class PlaceSeatOrderUseCase:
    """席からの注文(店内注文)ユースケース。会員のチェックはせず、その席でいま開いている
    会計に注文を紐づける。会計が開いていない(席が使用中でない)なら受け付けない。

    商品のチェックと明細の作り方は持ち帰りの注文(PlaceOrderUseCase)と同じ。会員ではないので
    割引も、進行中の注文数の上限(会員ごとのルール)もない。
    """

    def __init__(self, order_repository: OrderRepository, bill_repository: BillRepository) -> None:
        self._order_repository = order_repository
        self._bill_repository = bill_repository

    def execute(self, data: PlaceSeatOrderInput) -> OrderDTO:
        with transaction.atomic():
            # 会計の行をロックして読む。同時に退席(会計の締め)が来ても、締めた会計に
            # 注文が紛れ込まないように。
            bill = self._bill_repository.find_open_by_seat(data.seat_id, for_update=True)
            if bill is None:
                raise SeatNotInUse(data.seat_id)

            lines = []
            for line in data.lines:
                item = get_menu_item(line.menu_item_id)
                if item is None or not item.is_available:
                    raise MenuItemNotAvailable(line.menu_item_id)
                lines.append(
                    OrderLine(
                        menu_item_id=item.id,
                        name=item.name,
                        unit_price=Money(item.price),
                        quantity=line.quantity,
                    )
                )

            order = Order.place_at_seat(bill=bill, lines=lines)
            self._order_repository.save(order)
            publish(order.collect_events())

        return OrderDTO.from_entity(order)
