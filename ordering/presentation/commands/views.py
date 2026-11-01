from django.contrib import messages
from django.shortcuts import redirect
from django.views.decorators.http import require_http_methods

from menu.public import list_available_menu_items
from ordering.application.dto import (
    CancelOrderInput,
    CancelSeatOrderInput,
    PickUpOrderInput,
    PlaceOrderInput,
    PlaceOrderLineInput,
    PlaceSeatOrderInput,
    ServeOrderInput,
)
from ordering.application.use_cases.cancel_order import CancelOrderUseCase
from ordering.application.use_cases.cancel_seat_order import CancelSeatOrderUseCase
from ordering.application.use_cases.pick_up_order import PickUpOrderUseCase
from ordering.application.use_cases.place_order import PlaceOrderUseCase
from ordering.application.use_cases.place_seat_order import PlaceSeatOrderUseCase
from ordering.application.use_cases.serve_order import ServeOrderUseCase
from ordering.domain.exceptions import OrderingError, SeatNotInUse
from ordering.infrastructure.repositories import DjangoBillRepository, DjangoOrderRepository
from ordering.presentation.forms import PlaceOrderForm, PlaceSeatOrderForm


# コマンド側(CQRS の C)の画面。DDD アプリでも画面は presentation 層の一部であり、
# ユースケースを呼び出すだけの薄い View にする。フォームは形式チェックまでを担当し、
# ビジネスルール違反(ドメイン例外)はここで捕まえて messages に変換する。
# ユースケースの組み立て(リポジトリの注入)は DI コンテナを使わず View で直接行う。
# 処理後は参照側の一覧画面へリダイレクトし、表示は参照側に任せる(PRG パターン)。


@require_http_methods(["POST"])
def place_order_view(request):
    form = PlaceOrderForm(request.POST, menu_items=list_available_menu_items())
    if form.is_valid():
        use_case = PlaceOrderUseCase(order_repository=DjangoOrderRepository())
        try:
            use_case.execute(
                PlaceOrderInput(
                    customer_id=form.cleaned_data["customer_id"],
                    lines=tuple(
                        PlaceOrderLineInput(menu_item_id=menu_item_id, quantity=quantity)
                        for menu_item_id, quantity in form.ordered_lines()
                    ),
                )
            )
            messages.success(request, "注文を受け付けました。")
        except OrderingError as exc:
            messages.error(request, str(exc))
    else:
        messages.error(request, "入力内容を確認してください。")
    return redirect("ordering:order_list")


@require_http_methods(["POST"])
def cancel_order_view(request, order_id):
    use_case = CancelOrderUseCase(order_repository=DjangoOrderRepository())
    try:
        use_case.execute(CancelOrderInput(order_id=order_id))
        messages.success(request, "注文をキャンセルしました。")
    except OrderingError as exc:
        messages.error(request, str(exc))
    return redirect("ordering:order_list")


@require_http_methods(["POST"])
def pick_up_order_view(request, order_id):
    use_case = PickUpOrderUseCase(order_repository=DjangoOrderRepository())
    try:
        use_case.execute(PickUpOrderInput(order_id=order_id))
        messages.success(request, "受取を登録しました。")
    except OrderingError as exc:
        messages.error(request, str(exc))
    return redirect("ordering:order_list")


# --- 店内(席からの注文と提供) -------------------------------------------------


@require_http_methods(["POST"])
def place_seat_order_view(request, seat_id):
    form = PlaceSeatOrderForm(request.POST, menu_items=list_available_menu_items())
    if form.is_valid():
        use_case = PlaceSeatOrderUseCase(
            order_repository=DjangoOrderRepository(), bill_repository=DjangoBillRepository()
        )
        try:
            use_case.execute(
                PlaceSeatOrderInput(
                    seat_id=seat_id,
                    lines=tuple(
                        PlaceOrderLineInput(menu_item_id=menu_item_id, quantity=quantity)
                        for menu_item_id, quantity in form.ordered_lines()
                    ),
                )
            )
            messages.success(request, "ご注文を承りました。できあがり次第お席までお持ちします。")
        except SeatNotInUse:
            messages.error(request, "このお席は現在ご注文を受け付けていません。スタッフにお声がけください。")
        except OrderingError as exc:
            messages.error(request, str(exc))
    else:
        messages.error(request, "入力内容を確認してください。")
    return redirect("ordering:seat_order", seat_id=seat_id)


@require_http_methods(["POST"])
def cancel_seat_order_view(request, seat_id, order_id):
    use_case = CancelSeatOrderUseCase(
        order_repository=DjangoOrderRepository(), bill_repository=DjangoBillRepository()
    )
    try:
        use_case.execute(CancelSeatOrderInput(seat_id=seat_id, order_id=order_id))
        messages.success(request, "ご注文をキャンセルしました。")
    except OrderingError as exc:
        messages.error(request, str(exc))
    return redirect("ordering:seat_order", seat_id=seat_id)


@require_http_methods(["POST"])
def serve_order_view(request, order_id):
    use_case = ServeOrderUseCase(order_repository=DjangoOrderRepository())
    try:
        use_case.execute(ServeOrderInput(order_id=order_id))
        messages.success(request, "提供完了を記録しました。")
    except OrderingError as exc:
        messages.error(request, str(exc))
    return redirect("ordering:floor")
