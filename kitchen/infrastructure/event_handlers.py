from kitchen.application.use_cases.cancel_ticket import CancelTicketUseCase
from kitchen.application.use_cases.open_ticket import OpenTicketUseCase
from kitchen.domain.value_objects import TicketItem
from kitchen.infrastructure.repositories import DjangoTicketRepository
from ordering.domain.events import OrderCancelled, OrderPlaced

# ordering が発行するイベントのハンドラ。kitchen/apps.py の ready() で event_bus に
# 購読登録する。イベントに載った ordering 側の明細(OrderedItem)を、kitchen の
# 値オブジェクト(TicketItem)に詰め替えるのがここの役目(ordering のモデルを kitchen の
# 内側に持ち込まない)。


def handle_order_placed(event: OrderPlaced) -> None:
    OpenTicketUseCase(repository=DjangoTicketRepository()).execute(
        order_id=event.order_id,
        items=[TicketItem(name=item.name, quantity=item.quantity) for item in event.items],
    )


def handle_order_cancelled(event: OrderCancelled) -> None:
    CancelTicketUseCase(repository=DjangoTicketRepository()).execute(order_id=event.order_id)
