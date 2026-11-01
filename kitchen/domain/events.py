import uuid
from dataclasses import dataclass

from shared.domain.event import DomainEvent


@dataclass(frozen=True, kw_only=True)
class CookingStarted(DomainEvent):
    """チケット(注文明細 1 行)の調理が始まったことを表すドメインイベント。ordering
    モジュールが購読し、その明細を調理中にする(ordering/infrastructure/event_handlers.py)。
    """

    ticket_id: uuid.UUID
    order_id: uuid.UUID
    line_no: int  # 注文の中での明細の番号(ordering の OrderPlaced から写したもの)


@dataclass(frozen=True, kw_only=True)
class CookingCompleted(DomainEvent):
    """チケット(注文明細 1 行)の調理が終わったことを表すドメインイベント。ordering
    モジュールが購読し、その明細をできあがりにする(全明細がそろえば注文は「受取可」)。
    """

    ticket_id: uuid.UUID
    order_id: uuid.UUID
    line_no: int
