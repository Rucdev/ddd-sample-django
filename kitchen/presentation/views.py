from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from kitchen.application.dto import CompleteCookingInput, StartCookingInput
from kitchen.application.queries import open_ticket_queryset
from kitchen.application.use_cases.complete_cooking import CompleteCookingUseCase
from kitchen.application.use_cases.start_cooking import StartCookingUseCase
from kitchen.domain.exceptions import KitchenError
from kitchen.infrastructure.repositories import DjangoTicketRepository


# ordering/presentation/views.py と同じ方針: 画面はユースケースを呼ぶだけの薄い View、
# ドメイン例外は捕まえて messages に変換する。


def ticket_list_view(request):
    return render(request, "kitchen/ticket_list.html", {"tickets": open_ticket_queryset()})


@require_http_methods(["POST"])
def start_cooking_view(request, ticket_id):
    use_case = StartCookingUseCase(repository=DjangoTicketRepository())
    try:
        use_case.execute(StartCookingInput(ticket_id=ticket_id))
        messages.success(request, "調理を開始しました。")
    except KitchenError as exc:
        messages.error(request, str(exc))
    return redirect("kitchen:ticket_list")


@require_http_methods(["POST"])
def complete_cooking_view(request, ticket_id):
    use_case = CompleteCookingUseCase(repository=DjangoTicketRepository())
    try:
        use_case.execute(CompleteCookingInput(ticket_id=ticket_id))
        messages.success(request, "調理が完了しました。")
    except KitchenError as exc:
        messages.error(request, str(exc))
    return redirect("kitchen:ticket_list")
