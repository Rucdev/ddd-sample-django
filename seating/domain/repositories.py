import uuid
from collections.abc import Iterable
from typing import Protocol

from seating.domain.entities import Seat
from seating.domain.value_objects import AreaSpec


class SeatRepository(Protocol):
    """`Seat` 集約の永続化を抽象化するリポジトリ。"""

    def save(self, seat: Seat) -> None: ...

    def remove(self, seat: Seat) -> None: ...

    def find_by_id(self, seat_id: uuid.UUID) -> Seat | None: ...

    def find_all(self) -> list[Seat]: ...


class AreaRepository(Protocol):
    """エリアの永続化。エリアは座席構成ファイルの写しで、ステータスを持たないので
    集約にはせず、構成の反映時にまとめて書き換えるだけにする。
    """

    def save_all(self, areas: Iterable[AreaSpec]) -> None:
        """`areas` を作る / 名前と並び順を合わせる。"""
        ...

    def remove_except(self, codes: Iterable[str]) -> None:
        """`codes` 以外のエリアを消す。席が残っているエリアを消してはならない。"""
        ...
