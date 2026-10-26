from django.apps import AppConfig


class OrderingConfig(AppConfig):
    name = 'ordering'

    def ready(self) -> None:
        # kitchen の CookingStarted / CookingCompleted を購読する配線ポイント。Django の
        # アプリ初期化フック(ready())をイベントハンドラの登録場所として使う。ready() の
        # 中で import するのは、モジュール読み込み時の循環 import を避けるため(遅延 import)。
        from kitchen.domain.events import CookingCompleted, CookingStarted
        from ordering.infrastructure.event_handlers import (
            handle_cooking_completed,
            handle_cooking_started,
        )
        from shared.infrastructure.event_bus import subscribe

        subscribe(CookingStarted, handle_cooking_started)
        subscribe(CookingCompleted, handle_cooking_completed)
