from django.apps import AppConfig


class MembersConfig(AppConfig):
    name = 'members'

    def ready(self) -> None:
        from lending.domain.events import BookReturned, LoanOverdue
        from members.event_handlers import handle_book_returned, handle_loan_overdue
        from shared.infrastructure.event_bus import subscribe

        subscribe(LoanOverdue, handle_loan_overdue)
        subscribe(BookReturned, handle_book_returned)
