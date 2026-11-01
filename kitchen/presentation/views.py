from collections import Counter

from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from kitchen.application.dto import CompleteCookingInput, StartCookingInput
from kitchen.application.queries import open_ticket_queryset, recent_done_ticket_queryset
from kitchen.application.use_cases.complete_cooking import CompleteCookingUseCase
from kitchen.application.use_cases.start_cooking import StartCookingUseCase
from kitchen.infrastructure.models import TicketModel
from kitchen.infrastructure.repositories import DjangoTicketRepository
from shared.domain.exceptions import DomainError


# ordering/presentation/commands/views.py と同じ方針: 画面はユースケースを呼ぶだけの薄い View、
# ドメイン例外は捕まえて messages に変換する。
# 調理開始・完了は同期イベントで ordering の明細も進めるので、ordering 側の例外(明細の状態の
# 食い違いなど)もここに上がってくる。kitchen の例外に限らず DomainError でまとめて捕まえる。


def ticket_list_view(request):
    tickets = list(open_ticket_queryset())
    queued = [t for t in tickets if t.status == TicketModel.Status.QUEUED]
    cooking = [t for t in tickets if t.status == TicketModel.Status.COOKING]
    # 全チケットを横断した「いま作るべき数」。同じ商品はまとめて作れるので画面の脇に出す。
    totals: Counter[str] = Counter()
    for ticket in tickets:
        totals[ticket.name] += ticket.quantity
    return render(
        request,
        "kitchen/ticket_list.html",
        {
            "queued": queued,
            "cooking": cooking,
            "done": list(recent_done_ticket_queryset()),
            "item_totals": totals.most_common(),
        },
    )


@require_http_methods(["POST"])
def start_cooking_view(request, ticket_id):
    use_case = StartCookingUseCase(repository=DjangoTicketRepository())
    try:
        use_case.execute(StartCookingInput(ticket_id=ticket_id))
        messages.success(request, "調理を開始しました。")
    except DomainError as exc:
        messages.error(request, str(exc))
    return redirect("kitchen:ticket_list")


@require_http_methods(["POST"])
def complete_cooking_view(request, ticket_id):
    use_case = CompleteCookingUseCase(repository=DjangoTicketRepository())
    try:
        use_case.execute(CompleteCookingInput(ticket_id=ticket_id))
        messages.success(request, "調理が完了しました。")
    except DomainError as exc:
        messages.error(request, str(exc))
    return redirect("kitchen:ticket_list")
