from django.apps import AppConfig


class InventoryConfig(AppConfig):
    name = 'inventory'

    def ready(self) -> None:
        # ordering の OrderCancelled を購読して、注文で消費したキットを戻す
        # (customers/apps.py と同じく遅延 import で循環 import を避ける)。
        from inventory.event_handlers import handle_order_cancelled
        from ordering.domain.events import OrderCancelled
        from shared.infrastructure.event_bus import subscribe

        subscribe(OrderCancelled, handle_order_cancelled)
