from kitchen.domain.events import CookingCompleted, CookingStarted
from ordering.application.use_cases.complete_line_cooking import CompleteLineCookingUseCase
from ordering.application.use_cases.start_line_cooking import StartLineCookingUseCase
from ordering.infrastructure.repositories import DjangoOrderRepository

# kitchen が発行するイベントのハンドラ。ordering/apps.py の ready() で event_bus に
# 購読登録する(Django signals ではなくドメインイベントを使う理由は
# directory-structure.md「ドメインイベントと Django signals」参照)。
# キッチンのイベントは明細(調理チケット)単位で届くので、どの明細かを line_no で伝える。


def handle_cooking_started(event: CookingStarted) -> None:
    StartLineCookingUseCase(order_repository=DjangoOrderRepository()).execute(
        event.order_id, event.line_no
    )


def handle_cooking_completed(event: CookingCompleted) -> None:
    CompleteLineCookingUseCase(order_repository=DjangoOrderRepository()).execute(
        event.order_id, event.line_no
    )
