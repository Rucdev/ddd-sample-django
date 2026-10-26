from inventory.services import release_for_order
from ordering.domain.events import OrderCancelled

# ordering が発行する OrderCancelled のハンドラ。inventory/apps.py の ready() で購読登録する。


def handle_order_cancelled(event: OrderCancelled) -> None:
    release_for_order(event.order_id)
