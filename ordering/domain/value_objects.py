import uuid
from dataclasses import dataclass
from enum import StrEnum

from ordering.domain.exceptions import InvalidQuantity
from shared.domain.value_object import ValueObject

# 1 明細あたりの数量の上限。
MAX_QUANTITY_PER_LINE = 10


class OrderType(StrEnum):
    """注文の種類。受け渡し方と、誰が注文の主体かが違う。

    - TAKEOUT(持ち帰り): 会員がモバイルオーダーで頼み、カウンターで受け取る。会員 ID が必須。
    - DINE_IN(店内): 席に座っているお客様が席から頼み、店員が席まで提供する。会員登録は不要で、
      代わりに席の会計(Bill)に紐づく。支払いは会計ごとにまとめて行う。
    """

    TAKEOUT = "TAKEOUT"
    DINE_IN = "DINE_IN"


class OrderStatus(StrEnum):
    """注文ステータス。遷移は Order エンティティのメソッドだけが行う。

                                 ┌──▶ PICKED_UP(持ち帰り: 受取)
    PLACED ──▶ PREPARING ──▶ READY
       │                         └──▶ SERVED(店内: 提供完了)
       └────▶ CANCELLED(調理開始前のみ)

    PREPARING / READY は注文が自分で決める: 明細の調理状況(LineCookingStatus)を見て、
    どれか 1 つでも作り始めたら PREPARING、全部できあがったら READY。
    READY は持ち帰りなら「受取可」、店内なら「提供待ち」と呼ぶ(ordering/CONTEXT.md 参照)。
    """

    PLACED = "PLACED"
    PREPARING = "PREPARING"
    READY = "READY"
    PICKED_UP = "PICKED_UP"
    SERVED = "SERVED"
    CANCELLED = "CANCELLED"


class LineCookingStatus(StrEnum):
    """注文明細 1 行ごとの調理状況。キッチンは明細(商品)ごとに作るので、明細ごとに持つ。

    WAITING ──▶ COOKING ──▶ DONE(kitchen の CookingStarted / CookingCompleted で進む)
    """

    WAITING = "WAITING"
    COOKING = "COOKING"
    DONE = "DONE"


# 「受取(提供)が済むまで」の注文。同時に進行中の注文数の上限チェックで数える対象。
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


class BillStatus(StrEnum):
    """会計のステータス。遷移は Bill エンティティのメソッドだけが行う。

    OPEN ──▶ PAID(席の利用が終わったとき = 退席)
    """

    OPEN = "OPEN"
    PAID = "PAID"


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
    # 調理状況は明細と一緒に持つ。値オブジェクトなので、進めるときは Order が
    # dataclasses.replace で新しい明細に差し替える。
    cooking_status: LineCookingStatus = LineCookingStatus.WAITING

    def __post_init__(self) -> None:
        # 値オブジェクトは「不正な値では生成できない」ようにしておく。
        if not 1 <= self.quantity <= MAX_QUANTITY_PER_LINE:
            raise InvalidQuantity(self.name, self.quantity)

    @property
    def subtotal(self) -> Money:
        return self.unit_price * self.quantity
