import uuid
from dataclasses import dataclass

from shared.domain.event import DomainEvent

# seating が発行するドメインイベント。席の「利用」の始まりと終わりを外に知らせる。
# seating 自身は誰が購読しているかを知らない(ordering が購読し、席の会計を開く / 締める。
# ordering/apps.py 参照)。


@dataclass(frozen=True, kw_only=True)
class SeatOccupied(DomainEvent):
    """席の利用が始まった(案内・着席で使用中になった)。"""

    seat_id: uuid.UUID
    seat_code: str


@dataclass(frozen=True, kw_only=True)
class SeatVacated(DomainEvent):
    """席の利用が終わった(退席で空きに戻った)。"""

    seat_id: uuid.UUID
    seat_code: str
