from django.apps import AppConfig


class ReservationConfig(AppConfig):
    name = 'reservation'

    def ready(self) -> None:
        from lending.domain.events import BookReturned
        from reservation.infrastructure.event_handlers import handle_book_returned
        from shared.infrastructure.event_bus import subscribe

        subscribe(BookReturned, handle_book_returned)
