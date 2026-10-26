from kitchen.domain.events import CookingCompleted, CookingStarted
from ordering.application.use_cases.mark_ready import MarkReadyUseCase
from ordering.application.use_cases.start_preparing import StartPreparingUseCase
from ordering.infrastructure.repositories import DjangoOrderRepository

# kitchen が発行するイベントのハンドラ。ordering/apps.py の ready() で event_bus に
# 購読登録する(Django signals ではなくドメインイベントを使う理由は
# directory-structure.md「ドメインイベントと Django signals」参照)。


def handle_cooking_started(event: CookingStarted) -> None:
    StartPreparingUseCase(order_repository=DjangoOrderRepository()).execute(event.order_id)


def handle_cooking_completed(event: CookingCompleted) -> None:
    MarkReadyUseCase(order_repository=DjangoOrderRepository()).execute(event.order_id)
