import uuid
from dataclasses import dataclass
from enum import StrEnum

from ordering.domain.exceptions import InvalidQuantity
from shared.domain.value_object import ValueObject

# 1 明細あたりの数量の上限。
MAX_QUANTITY_PER_LINE = 10


class OrderStatus(StrEnum):
    """注文ステータス。遷移は Order エンティティのメソッドだけが行う。

    PLACED ──▶ PREPARING ──▶ READY ──▶ PICKED_UP
       │
       └────▶ CANCELLED(調理開始前のみ)
    """

    PLACED = "PLACED"
    PREPARING = "PREPARING"
    READY = "READY"
    PICKED_UP = "PICKED_UP"
    CANCELLED = "CANCELLED"


# 「受取が済むまで」の注文。同時に進行中の注文数の上限チェックで数える対象。
IN_PROGRESS_STATUSES = frozenset({OrderStatus.PLACED, OrderStatus.PREPARING, OrderStatus.READY})


@dataclass(frozen=True)
class Money(ValueObject):
    """金額(円)。値オブジェクト。端数の出ない円単位の整数で持つ。"""

    amount: int

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError(f"Money cannot be negative: {self.amount}")

    def __add__(self, other: "Money") -> "Money":
        return Money(self.amount + other.amount)

    def __sub__(self, other: "Money") -> "Money":
        return Money(self.amount - other.amount)

    def __mul__(self, quantity: int) -> "Money":
        return Money(self.amount * quantity)


ZERO_YEN = Money(0)


@dataclass(frozen=True)
class DiscountRate(ValueObject):
    """割引率(%)。値オブジェクト。"""

    percent: int = 0

    def __post_init__(self) -> None:
        if not 0 <= self.percent <= 100:
            raise ValueError(f"Discount percent must be between 0 and 100: {self.percent}")

    def discount_for(self, subtotal: Money) -> Money:
        """割引額。1 円未満は切り捨てる(= お客様に有利な方向には丸めない)。"""
        return Money(subtotal.amount * self.percent // 100)


NO_DISCOUNT = DiscountRate()

# 会員ランクごとの割引率。キーは customers モジュールの公開 API が返す
# `CustomerDTO.rank` の値("REGULAR" / "SILVER" / "GOLD")。ordering は customers の
# 内部(`Customer.Rank`)を import せず、公開 API が返す文字列値だけで引き当てる。
DISCOUNT_RATE_BY_CUSTOMER_RANK: dict[str, DiscountRate] = {
    "REGULAR": NO_DISCOUNT,
    "SILVER": DiscountRate(percent=5),
    "GOLD": DiscountRate(percent=10),
}


def discount_rate_for_rank(rank: str | None) -> DiscountRate:
    """未知のランク・会員不明(None)は割引なしにフォールバックする。"""
    return DISCOUNT_RATE_BY_CUSTOMER_RANK.get(rank, NO_DISCOUNT)


@dataclass(frozen=True)
class OrderLine(ValueObject):
    """注文明細 1 行。値オブジェクト。

    商品名・単価は注文時点の値をスナップショットとして持つ。注文後にメニューの価格が
    変わっても、確定済みの注文の金額は変わらない。
    """

    menu_item_id: uuid.UUID
    name: str
    unit_price: Money
    quantity: int

    def __post_init__(self) -> None:
        # 値オブジェクトは「不正な値では生成できない」ようにしておく。
        if not 1 <= self.quantity <= MAX_QUANTITY_PER_LINE:
            raise InvalidQuantity(self.name, self.quantity)

    @property
    def subtotal(self) -> Money:
        return self.unit_price * self.quantity
