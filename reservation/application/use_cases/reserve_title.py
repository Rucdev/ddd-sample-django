from datetime import date

from django.db import transaction

from catalog.public import get_title
from members.public import get_member
from reservation.application.dto import ReservationDTO, ReserveTitleInput
from reservation.domain.exceptions import MemberNotEligible, TitleNotFound
from reservation.domain.repositories import ReservationQueueRepository
from shared.infrastructure.event_bus import publish


class ReserveTitleUseCase:
    def __init__(self, repository: ReservationQueueRepository) -> None:
        self._repository = repository

    def execute(self, data: ReserveTitleInput, *, today: date | None = None) -> ReservationDTO:
        today = today or date.today()

        with transaction.atomic():
            member = get_member(data.member_id)
            if member is None or not member.is_active:
                raise MemberNotEligible(data.member_id)

            title = get_title(data.title_id)
            if title is None:
                raise TitleNotFound(data.title_id)

            queue = self._repository.find_by_title(data.title_id)
            queue.add_reservation(member_id=data.member_id, today=today)
            self._repository.save(queue)
            publish(queue.collect_events())

            position = next(
                index
                for index, reservation in enumerate(queue.reservations, start=1)
                if reservation.member_id == data.member_id
            )

        return ReservationDTO(
            title_id=data.title_id,
            member_id=data.member_id,
            requested_at=today,
            position=position,
        )
