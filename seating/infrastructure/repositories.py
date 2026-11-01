import uuid
from collections.abc import Iterable

from django.utils import timezone

from seating.domain.entities import Seat
from seating.domain.value_objects import AreaSpec, SeatPosition, SeatStatus
from seating.infrastructure.models import AreaModel, SeatModel


class DjangoSeatRepository:
    """`SeatRepository` の Django ORM 実装。`Seat` エンティティ ⇔ `SeatModel` の変換をここに閉じ込める。"""

    def save(self, seat: Seat) -> None:
        current_status = SeatModel.objects.filter(id=seat.id).values_list("status", flat=True).first()
        defaults = {
            "code": seat.code,
            "area": AreaModel.objects.get(code=seat.area_code),
            "capacity": seat.capacity,
            "row": seat.position.row,
            "col": seat.position.col,
            "status": seat.status.value,
        }
        if current_status is not None and current_status != seat.status.value:
            defaults["status_changed_at"] = timezone.now()
        SeatModel.objects.update_or_create(id=seat.id, defaults=defaults)

    def remove(self, seat: Seat) -> None:
        SeatModel.objects.filter(id=seat.id).delete()

    def find_by_id(self, seat_id: uuid.UUID) -> Seat | None:
        model = SeatModel.objects.select_related("area").filter(id=seat_id).first()
        return self._to_entity(model) if model else None

    def find_all(self) -> list[Seat]:
        return [self._to_entity(model) for model in SeatModel.objects.select_related("area")]

    @staticmethod
    def _to_entity(model: SeatModel) -> Seat:
        return Seat(
            seat_id=model.id,
            code=model.code,
            area_code=model.area.code,
            capacity=model.capacity,
            position=SeatPosition(row=model.row, col=model.col),
            status=SeatStatus(model.status),
        )


class DjangoAreaRepository:
    """`AreaRepository` の Django ORM 実装。"""

    def save_all(self, areas: Iterable[AreaSpec]) -> None:
        for area in areas:
            AreaModel.objects.update_or_create(
                code=area.code,
                defaults={"name": area.name, "display_order": area.display_order},
            )

    def remove_except(self, codes: Iterable[str]) -> None:
        # 席が残っていれば on_delete=PROTECT で ProtectedError になる(ユースケースの順番の誤りを検知する)。
        AreaModel.objects.exclude(code__in=list(codes)).delete()
