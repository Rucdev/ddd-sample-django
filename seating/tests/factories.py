from seating.domain.value_objects import AreaSpec, SeatLayout, SeatPosition, SeatSpec


def seat_spec(code: str, *, area: str = "table", capacity: int = 2, row: int = 1, col: int = 1) -> SeatSpec:
    return SeatSpec(code=code, area_code=area, capacity=capacity, position=SeatPosition(row=row, col=col))


def layout(*seats: SeatSpec, areas: tuple[str, ...] = ("table",)) -> SeatLayout:
    return SeatLayout(
        areas=[AreaSpec(code=code, name=code, display_order=i) for i, code in enumerate(areas, start=1)],
        seats=seats,
    )
