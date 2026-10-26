from dataclasses import dataclass
from enum import StrEnum

from shared.domain.value_object import ValueObject


class TicketStatus(StrEnum):
    """調理チケットのステータス。遷移は Ticket エンティティのメソッドだけが行う。

    QUEUED ──▶ COOKING ──▶ DONE
       │
       └────▶ CANCELLED(調理開始前のみ)
    """

    QUEUED = "QUEUED"
    COOKING = "COOKING"
    DONE = "DONE"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class TicketItem(ValueObject):
    """チケットに載る「何を何個作るか」。値オブジェクト。

    キッチンは価格に関心がないので、商品名と数量だけを持つ(同じ「商品」でも
    ordering の OrderLine とはコンテキストごとに別のモデルになる)。
    """

    name: str
    quantity: int
