from django.shortcuts import render

from customers.public import list_customers
from menu.public import list_available_menu_items
from ordering.application.queries import (
    get_open_bill_for_seat,
    list_open_bills,
    list_orders,
    list_recently_paid_bills,
)
from ordering.domain.value_objects import OrderType, discount_rate_for_rank
from ordering.presentation.forms import PlaceOrderForm, PlaceSeatOrderForm


# 参照側(CQRS の Q)の画面。queries.py を呼んで表示するだけで、ユースケースは通らない。
# 注文フォームも同じ画面に置くが、送信先はコマンド側の View(commands/views.py)。


# 画面に出すステータスの日本語表記(CONTEXT.md の用語に合わせる)。
STATUS_LABELS = {
    "PLACED": "受付済",
    "PREPARING": "調理中",
    "READY": "受取可",
    "PICKED_UP": "受取済",
    "CANCELLED": "キャンセル",
}

# 店内の注文は READY を「提供待ち」と呼び、受取ではなく提供で終わる。
DINE_IN_STATUS_LABELS = {
    **STATUS_LABELS,
    "READY": "提供待ち",
    "SERVED": "提供済",
}

# 会員ランクの日本語表記。ordering は customers の内部(Customer.Rank)を import しないので
# 公開 API が返す文字列値から引く。
RANK_LABELS = {
    "REGULAR": "一般会員",
    "SILVER": "シルバー会員",
    "GOLD": "ゴールド会員",
}


def _member_payload(customer) -> dict:
    """画面の擬似ログイン(会員の選択)に使う会員情報。JSON にして JS へ渡す。"""
    return {
        "id": str(customer.id),
        "name": customer.name,
        "rank": customer.rank,
        "rank_label": RANK_LABELS.get(customer.rank, customer.rank),
        "discount_percent": discount_rate_for_rank(customer.rank).percent,
        "points": customer.points,
        "is_active": customer.is_active,
    }


def order_list_view(request):
    customers = list_customers()
    customer_names = {customer.id: customer.name for customer in customers}
    rows = [
        {
            "order": order,
            "status_label": STATUS_LABELS[order.status],
            "customer_name": customer_names.get(order.customer_id, "退会済みの会員"),
        }
        # この画面は持ち帰り(モバイルオーダー)の注文だけ。店内の注文は席の画面とホール画面で扱う。
        for order in list_orders(OrderType.TAKEOUT)
    ]
    form = PlaceOrderForm(menu_items=list_available_menu_items())
    members = [_member_payload(customer) for customer in customers]
    return render(
        request, "ordering/order_list.html", {"rows": rows, "form": form, "members": members}
    )


def _dine_in_rows(orders) -> list[dict]:
    return [{"order": order, "status_label": DINE_IN_STATUS_LABELS[order.status]} for order in orders]


def seat_order_view(request, seat_id):
    """席からの注文画面(お客様が席の QR コードから開く想定)。会員の選択はない。

    席が使用中でない(会計が開いていない)ときは注文フォームを出さない。
    """
    bill = get_open_bill_for_seat(seat_id)
    context = {"seat_id": seat_id, "bill": bill}
    if bill is not None:
        context["form"] = PlaceSeatOrderForm(menu_items=list_available_menu_items())
        context["rows"] = _dine_in_rows(reversed(bill.orders))  # 新しい注文を上に
    return render(request, "ordering/seat_order.html", context)


def floor_view(request):
    """ホール画面(店員側)。利用中の席ごとに注文と会計の金額を出し、提供待ちの注文に
    「提供完了」ボタンを出す。
    """
    bills = []
    waiting_total = 0
    for bill in list_open_bills():
        waiting = sum(1 for order in bill.orders if order.status == "READY")  # 提供待ちの数
        waiting_total += waiting
        bills.append({"bill": bill, "rows": _dine_in_rows(bill.orders), "waiting": waiting})
    return render(
        request,
        "ordering/floor.html",
        {
            "bills": bills,
            "waiting_total": waiting_total,
            "paid_bills": list_recently_paid_bills(),
        },
    )
