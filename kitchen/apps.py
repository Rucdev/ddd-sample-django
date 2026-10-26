from django.apps import AppConfig


class KitchenConfig(AppConfig):
    name = 'kitchen'

    def ready(self) -> None:
        # ordering の OrderPlaced / OrderCancelled を購読する配線ポイント
        # (ordering/apps.py と同じく遅延 import で循環 import を避ける)。
        from kitchen.infrastructure.event_handlers import (
            handle_order_cancelled,
            handle_order_placed,
        )
        from ordering.domain.events import OrderCancelled, OrderPlaced
        from shared.infrastructure.event_bus import subscribe

        subscribe(OrderPlaced, handle_order_placed)
        subscribe(OrderCancelled, handle_order_cancelled)
