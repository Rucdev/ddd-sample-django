from django.shortcuts import render

from customers.public import list_customers
from menu.public import list_available_menu_items
from ordering.application.queries import list_orders
from ordering.domain.value_objects import discount_rate_for_rank
from ordering.presentation.forms import PlaceOrderForm


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
        for order in list_orders()
    ]
    form = PlaceOrderForm(menu_items=list_available_menu_items())
    members = [_member_payload(customer) for customer in customers]
    return render(
        request, "ordering/order_list.html", {"rows": rows, "form": form, "members": members}
    )
