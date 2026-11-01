"""座席構成ファイル(YAML)を読み、ドメインの `SeatLayout` に変換する。

ファイル形式に関する知識(キー名・YAML であること)はここに閉じ込め、ドメイン層は
`SeatLayout` しか知らない。JSON に変えたくなってもこのファイルだけを差し替えればよい。

    areas:
      - code: counter          # エリアコード(一意)
        name: カウンター        # 画面に出す名前
        seats:
          - {code: C1, row: 1, col: 1}               # capacity を省くと 1 人席
          - {code: C2, row: 1, col: 2, capacity: 2}

エリアの並び順はファイルに書いた順番。席の row / col はエリアの見取り図の何行何列目か(1 始まり)。
"""

from pathlib import Path
from typing import Any

import yaml

from seating.domain.exceptions import InvalidSeatLayout
from seating.domain.value_objects import AreaSpec, SeatLayout, SeatPosition, SeatSpec


def load_seat_layout(path: str | Path) -> SeatLayout:
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise InvalidSeatLayout(f"Cannot read seat layout file {path}: {exc}") from exc
    return parse_seat_layout(text)


def parse_seat_layout(text: str) -> SeatLayout:
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise InvalidSeatLayout(f"Seat layout is not valid YAML: {exc}") from exc

    raw_areas = _require(data, "areas", list, where="file")
    areas: list[AreaSpec] = []
    seats: list[SeatSpec] = []
    for order, raw_area in enumerate(raw_areas, start=1):
        area_code = str(_require(raw_area, "code", (str, int), where=f"area #{order}"))
        areas.append(
            AreaSpec(
                code=area_code,
                name=str(raw_area.get("name") or area_code),
                display_order=order,
            )
        )
        for raw_seat in _require(raw_area, "seats", list, where=f"area {area_code}"):
            seat_code = str(_require(raw_seat, "code", (str, int), where=f"a seat in area {area_code}"))
            where = f"seat {seat_code}"
            seats.append(
                SeatSpec(
                    code=seat_code,
                    area_code=area_code,
                    capacity=_int(raw_seat.get("capacity", 1), "capacity", where),
                    position=SeatPosition(
                        row=_require(raw_seat, "row", int, where=where),
                        col=_require(raw_seat, "col", int, where=where),
                    ),
                )
            )
    return SeatLayout(areas=areas, seats=seats)


def _require(mapping: Any, key: str, kind: type | tuple[type, ...], *, where: str) -> Any:
    if not isinstance(mapping, dict):
        raise InvalidSeatLayout(f"{where} must be a mapping")
    if key not in mapping:
        raise InvalidSeatLayout(f"{where} is missing '{key}'")
    value = mapping[key]
    if not isinstance(value, kind) or isinstance(value, bool):
        raise InvalidSeatLayout(f"'{key}' of {where} has an invalid value: {value!r}")
    return value


def _int(value: Any, key: str, where: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise InvalidSeatLayout(f"'{key}' of {where} must be an integer: {value!r}")
    return value
