from customers.public import add_points
from ordering.domain.events import OrderPickedUp

# ordering が発行する OrderPickedUp イベントのハンドラ。customers/apps.py の ready() で
# event_bus に購読登録する。CRUD モジュールでもイベントの購読はできる。

# 100 円(税込・割引後)につき 1 ポイント。
YEN_PER_POINT = 100


def handle_order_picked_up(event: OrderPickedUp) -> None:
    add_points(event.customer_id, event.total // YEN_PER_POINT)
