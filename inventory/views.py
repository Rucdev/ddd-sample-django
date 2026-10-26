from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from inventory import services
from inventory.exceptions import InventoryError
from inventory.forms import IssueForm, QuantityForm
from inventory.models import Kit, Reservation, StockMovement

# 在庫の専用画面。キットの登録・名前の編集は admin、在庫数を動かす操作はすべてここ(と API)で行い、
# どれも services.py の関数を呼ぶだけにする。在庫不足などのエラーは messages に変換する。

RECENT_MOVEMENTS = 20


def kit_list_view(request):
    return render(
        request,
        "inventory/kit_list.html",
        {
            "kits": Kit.objects.all(),
            "reservations": Reservation.objects.select_related("kit").filter(
                status=Reservation.Status.HELD
            ),
            "movements": StockMovement.objects.select_related("kit")[:RECENT_MOVEMENTS],
        },
    )


def _run(request, operation, success_message: str):
    try:
        operation()
        messages.success(request, success_message)
    except InventoryError as exc:
        messages.error(request, str(exc))
    return redirect("inventory:kit_list")


def _run_with_form(request, form, operation, success_message: str):
    if not form.is_valid():
        messages.error(request, "入力内容を確認してください。")
        return redirect("inventory:kit_list")
    return _run(request, lambda: operation(form.cleaned_data), success_message)


@require_http_methods(["POST"])
def receive_view(request, kit_id):
    return _run_with_form(
        request,
        QuantityForm(request.POST),
        lambda data: services.receive(kit_id, data["quantity"], data["memo"]),
        "入庫しました。",
    )


@require_http_methods(["POST"])
def issue_view(request, kit_id):
    return _run_with_form(
        request,
        IssueForm(request.POST),
        lambda data: services.issue(kit_id, data["quantity"], data["memo"]),
        "出庫しました。",
    )


@require_http_methods(["POST"])
def reserve_view(request, kit_id):
    return _run_with_form(
        request,
        QuantityForm(request.POST),
        lambda data: services.reserve(kit_id, data["quantity"], data["memo"]),
        "予約を確保しました。",
    )


@require_http_methods(["POST"])
def deactivate_kit_view(request, kit_id):
    return _run(request, lambda: services.deactivate_kit(kit_id), "在庫管理を停止しました。")


@require_http_methods(["POST"])
def activate_kit_view(request, kit_id):
    return _run(request, lambda: services.activate_kit(kit_id), "在庫管理を再開しました。")


@require_http_methods(["POST"])
def use_reservation_view(request, reservation_id):
    return _run(request, lambda: services.use_reservation(reservation_id), "予約を使用しました。")


@require_http_methods(["POST"])
def cancel_reservation_view(request, reservation_id):
    return _run(request, lambda: services.cancel_reservation(reservation_id), "予約を取り消しました。")
