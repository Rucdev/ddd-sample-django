"""Public API of the customers module. Other modules must only import from here."""

import uuid
from dataclasses import dataclass

from django.db.models import F

from customers.models import Customer


@dataclass(frozen=True)
class CustomerDTO:
    id: uuid.UUID
    name: str
    email: str
    is_active: bool
    rank: str  # 会員ランク。`Customer.Rank` の値("REGULAR" / "SILVER" / "GOLD")。
    points: int


def _to_dto(customer: Customer) -> CustomerDTO:
    return CustomerDTO(
        id=customer.id,
        name=customer.name,
        email=customer.email,
        is_active=customer.status == Customer.Status.ACTIVE,
        rank=customer.rank,
        points=customer.points,
    )


def get_customer(customer_id: uuid.UUID) -> CustomerDTO | None:
    customer = Customer.objects.filter(id=customer_id).first()
    return _to_dto(customer) if customer else None


def add_points(customer_id: uuid.UUID, points: int) -> None:
    # F 式で DB 側で加算する(読んでから書く間に別の加算が入っても取りこぼさない)。
    Customer.objects.filter(id=customer_id).update(points=F("points") + points)
