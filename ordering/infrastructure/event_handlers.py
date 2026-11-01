from kitchen.domain.events import CookingCompleted, CookingStarted
from ordering.application.use_cases.complete_line_cooking import CompleteLineCookingUseCase
from ordering.application.use_cases.manage_bill import OpenBillUseCase, SettleBillUseCase
from ordering.application.use_cases.start_line_cooking import StartLineCookingUseCase
from ordering.infrastructure.repositories import DjangoBillRepository, DjangoOrderRepository
from seating.domain.events import SeatOccupied, SeatVacated

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


# seating が発行するイベントのハンドラ。席の利用の始まり・終わりに合わせて、その席の
# 会計を開く / 支払済にする。seating は ordering を知らない(一方向の依存)。


def handle_seat_occupied(event: SeatOccupied) -> None:
    OpenBillUseCase(bill_repository=DjangoBillRepository()).execute(event.seat_id, event.seat_code)


def handle_seat_vacated(event: SeatVacated) -> None:
    SettleBillUseCase(bill_repository=DjangoBillRepository()).execute(event.seat_id)
