from django.apps import AppConfig


class ReservationConfig(AppConfig):
    name = 'reservation'

    def ready(self) -> None:
        # lending の BookReturned イベントを購読する配線ポイント。Django のアプリ初期化
        # フック(ready())をイベントハンドラの登録場所として使う。ready() の中で import
        # するのは、モジュール読み込み時の循環 import を避けるため(遅延 import)。
        from lending.domain.events import BookReturned
        from reservation.infrastructure.event_handlers import handle_book_returned
        from shared.infrastructure.event_bus import subscribe

        subscribe(BookReturned, handle_book_returned)
