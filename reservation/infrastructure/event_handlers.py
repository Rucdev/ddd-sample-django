from catalog.public import get_copy
from lending.domain.events import BookReturned
from reservation.application.use_cases.assign_hold import AssignHoldUseCase
from reservation.infrastructure.repositories import DjangoReservationQueueRepository

# lending が発行する BookReturned イベントのハンドラ。reservation/apps.py の ready() で
# event_bus に購読登録する(Django signals ではなくドメインイベントを使う理由は
# directory-structure.md「ドメインイベントと Django signals」参照)。


def handle_book_returned(event: BookReturned) -> None:
    # copy_id から書誌(title_id)を引くために catalog モジュールに照会する。
    copy = get_copy(event.copy_id)
    if copy is None:
        return

    use_case = AssignHoldUseCase(repository=DjangoReservationQueueRepository())
    # today は event.returned_at(返却が成立した業務上の日付)を使う。イベント生成時刻
    # (occurred_at)を使うと、テストで today を差し替えて呼んだ場合に取置期限がずれる。
    use_case.execute(title_id=copy.title_id, copy_id=event.copy_id, today=event.returned_at)
