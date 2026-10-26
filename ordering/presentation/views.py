from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from menu.public import list_available_menu_items
from ordering.application.dto import (
    CancelOrderInput,
    PickUpOrderInput,
    PlaceOrderInput,
    PlaceOrderLineInput,
)
from ordering.application.queries import list_orders
from ordering.application.use_cases.cancel_order import CancelOrderUseCase
from ordering.application.use_cases.pick_up_order import PickUpOrderUseCase
from ordering.application.use_cases.place_order import PlaceOrderUseCase
from ordering.domain.exceptions import OrderingError
from ordering.infrastructure.repositories import DjangoOrderRepository
from ordering.presentation.forms import PlaceOrderForm


# 画面(Django テンプレート)。DDD アプリでも画面は presentation 層の一部であり、
# ユースケースを呼び出すだけの薄い View にする。フォームは形式チェックまでを担当し、
# ビジネスルール違反(ドメイン例外)はここで捕まえて messages に変換する。
# ユースケースの組み立て(リポジトリの注入)は DI コンテナを使わず View で直接行う。


# 画面に出すステータスの日本語表記(CONTEXT.md の用語に合わせる)。
STATUS_LABELS = {
    "PLACED": "受付済",
    "PREPARING": "調理中",
    "READY": "受取可",
    "PICKED_UP": "受取済",
    "CANCELLED": "キャンセル",
}


def order_list_view(request):
    rows = [{"order": order, "status_label": STATUS_LABELS[order.status]} for order in list_orders()]
    form = PlaceOrderForm(menu_items=list_available_menu_items())
    return render(request, "ordering/order_list.html", {"rows": rows, "form": form})


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
