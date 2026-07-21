import uuid

from shared.domain.exceptions import ConflictError, DomainError, NotFoundError

# lending と同じパターン: shared.domain.exceptions の NotFoundError / ConflictError も
# 多重継承しておくことで、shared/infrastructure/exception_handler.py が reservation を
# 個別に知らなくても 404 / 409 への変換を行える。


class ReservationError(DomainError):
    """Base class for reservation domain errors."""


class TitleNotFound(ReservationError, NotFoundError):
    def __init__(self, title_id: uuid.UUID) -> None:
        self.title_id = title_id
        super().__init__(f"Title {title_id} was not found")


class MemberNotEligible(ReservationError, ConflictError):
    def __init__(self, member_id: uuid.UUID) -> None:
        self.member_id = member_id
        super().__init__(f"Member {member_id} is not eligible to reserve titles")


class DuplicateReservation(ReservationError, ConflictError):
    def __init__(self, title_id: uuid.UUID, member_id: uuid.UUID) -> None:
        self.title_id = title_id
        self.member_id = member_id
        super().__init__(
            f"Member {member_id} already has a reservation or hold for title {title_id}"
        )


class NotReserved(ReservationError, NotFoundError):
    def __init__(self, title_id: uuid.UUID, member_id: uuid.UUID) -> None:
        self.title_id = title_id
        self.member_id = member_id
        super().__init__(f"Member {member_id} has no pending reservation for title {title_id}")
