from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from reservation.application.dto import CancelReservationInput, ReserveTitleInput
from reservation.application.queries import list_holds, list_reservations
from reservation.application.use_cases.cancel_reservation import CancelReservationUseCase
from reservation.application.use_cases.reserve_title import ReserveTitleUseCase
from reservation.domain.exceptions import ReservationError
from reservation.infrastructure.repositories import DjangoReservationQueueRepository
from reservation.presentation.forms import ReserveTitleForm


def reservation_list_view(request):
    reservations = list_reservations()
    holds = list_holds()
    form = ReserveTitleForm()
    return render(
        request,
        "reservation/reservation_list.html",
        {"reservations": reservations, "holds": holds, "form": form},
    )


@require_http_methods(["POST"])
def reserve_title_view(request):
    form = ReserveTitleForm(request.POST)
    if form.is_valid():
        use_case = ReserveTitleUseCase(repository=DjangoReservationQueueRepository())
        try:
            use_case.execute(
                ReserveTitleInput(
                    member_id=form.cleaned_data["member_id"],
                    title_id=form.cleaned_data["title_id"],
                )
            )
            messages.success(request, "予約を登録しました。")
        except ReservationError as exc:
            messages.error(request, str(exc))
    else:
        messages.error(request, "入力内容を確認してください。")
    return redirect("reservation:reservation_list")


@require_http_methods(["POST"])
def cancel_reservation_view(request, title_id, member_id):
    use_case = CancelReservationUseCase(repository=DjangoReservationQueueRepository())
    try:
        use_case.execute(CancelReservationInput(member_id=member_id, title_id=title_id))
        messages.success(request, "予約を取り消しました。")
    except ReservationError as exc:
        messages.error(request, str(exc))
    return redirect("reservation:reservation_list")
