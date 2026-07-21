"""Public API of the members module. Other modules must only import from here."""

import uuid
from dataclasses import dataclass

from members.models import Member


@dataclass(frozen=True)
class MemberDTO:
    id: uuid.UUID
    name: str
    email: str
    is_active: bool


def _to_dto(member: Member) -> MemberDTO:
    return MemberDTO(
        id=member.id,
        name=member.name,
        email=member.email,
        is_active=member.status == Member.Status.ACTIVE,
    )


def get_member(member_id: uuid.UUID) -> MemberDTO | None:
    member = Member.objects.filter(id=member_id).first()
    return _to_dto(member) if member else None


def suspend_member(member_id: uuid.UUID) -> None:
    Member.objects.filter(id=member_id).update(status=Member.Status.SUSPENDED)


def reinstate_member(member_id: uuid.UUID) -> None:
    Member.objects.filter(id=member_id).update(status=Member.Status.ACTIVE)
