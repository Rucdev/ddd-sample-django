from django.apps import AppConfig


class CustomersConfig(AppConfig):
    name = 'customers'

    def ready(self) -> None:
        from customers.event_handlers import handle_order_picked_up
        from ordering.domain.events import OrderPickedUp
        from shared.infrastructure.event_bus import subscribe

        subscribe(OrderPickedUp, handle_order_picked_up)
