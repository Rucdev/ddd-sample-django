from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from seating.application.dto import SeatCommandInput
from seating.application.queries import area_queryset_with_seats, status_summary
from seating.application.use_cases.change_seat_status import (
    CancelSeatReservationUseCase,
    OccupySeatUseCase,
    ReserveSeatUseCase,
    VacateSeatUseCase,
)
from seating.domain.exceptions import SeatingError
from seating.infrastructure.repositories import DjangoSeatRepository

# kitchen/presentation/views.py と同じ方針: 画面はユースケースを呼ぶだけの薄い View、
# ドメイン例外は捕まえて messages に変換する。


def seat_board_view(request):
    summary = status_summary()
    total_seats = sum(s.seats for s in summary)
    total_capacity = sum(s.capacity for s in summary)
    occupied = next(s for s in summary if s.status == "OCCUPIED")
    return render(
        request,
        "seating/seat_board.html",
        {
            "areas": list(area_queryset_with_seats()),
            "summary": summary,
            "total_seats": total_seats,
            "total_capacity": total_capacity,
            # 使用率は「使用中の席数 / 全席数」。人数ベースだと相席の有無で揺れるので席数で出す。
            "occupancy_rate": round(occupied.seats * 100 / total_seats) if total_seats else 0,
        },
    )


def _run(request, use_case_class, seat_id, success_message):
    use_case = use_case_class(repository=DjangoSeatRepository())
    try:
        seat = use_case.execute(SeatCommandInput(seat_id=seat_id))
        messages.success(request, success_message.format(code=seat.code))
    except SeatingError as exc:
        messages.error(request, str(exc))
    return redirect("seating:seat_board")


@require_http_methods(["POST"])
def reserve_seat_view(request, seat_id):
    return _run(request, ReserveSeatUseCase, seat_id, "{code} を予約にしました。")


@require_http_methods(["POST"])
def cancel_reservation_view(request, seat_id):
    return _run(request, CancelSeatReservationUseCase, seat_id, "{code} の予約を取り消しました。")


@require_http_methods(["POST"])
def occupy_seat_view(request, seat_id):
    return _run(request, OccupySeatUseCase, seat_id, "{code} にご案内しました。")


@require_http_methods(["POST"])
def vacate_seat_view(request, seat_id):
    return _run(request, VacateSeatUseCase, seat_id, "{code} が空きました。")
