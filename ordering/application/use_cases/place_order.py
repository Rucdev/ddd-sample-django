from django.db import transaction

from customers.public import get_customer
from inventory.public import InsufficientStock, allocate_for_order
from menu.public import get_menu_item
from ordering.application.dto import OrderDTO, PlaceOrderInput
from ordering.domain.entities import Order
from ordering.domain.exceptions import CustomerNotEligible, MenuItemNotAvailable, OutOfStock
from ordering.domain.repositories import OrderRepository
from ordering.domain.services import OrderPolicy
from ordering.domain.value_objects import Money, OrderLine, discount_rate_for_rank
from shared.infrastructure.event_bus import publish


class PlaceOrderUseCase:
    """注文ユースケース。お客様・商品のチェックはここ(application 層)で行い、
    注文そのものの成立判定(明細が空でないか、数量、進行中の注文数など)は
    domain 層(Order / OrderLine / OrderPolicy)に委ねる。

    リポジトリは呼び出し側(presentation 層)がコンストラクタに注入する。DI コンテナは
    使わず、view/API で具象クラスを直接組み立てる方針(directory-structure.md 参照)。
    """

    def __init__(self, order_repository: OrderRepository) -> None:
        self._order_repository = order_repository

    def execute(self, data: PlaceOrderInput) -> OrderDTO:
        with transaction.atomic():
            # お客様・商品の有効性チェックは、それぞれの公開 API(DTO)を通じて行う。
            # ORM モデルやエンティティを直接 import しない。
            customer = get_customer(data.customer_id)
            if customer is None or not customer.is_active:
                raise CustomerNotEligible(data.customer_id)

            lines = []
            for line in data.lines:
                item = get_menu_item(line.menu_item_id)
                if item is None or not item.is_available:
                    raise MenuItemNotAvailable(line.menu_item_id)
                # 商品名・単価は注文時点の値をスナップショットとして明細に写す。
                lines.append(
                    OrderLine(
                        menu_item_id=item.id,
                        name=item.name,
                        unit_price=Money(item.price),
                        quantity=line.quantity,
                    )
                )

            OrderPolicy(self._order_repository).ensure_customer_can_order(data.customer_id)

            # 割引率は会員ランクに応じて変わる(customers.public.CustomerDTO.rank)。
            order = Order.place(
                customer_id=data.customer_id,
                lines=lines,
                discount_rate=discount_rate_for_rank(customer.rank),
            )
            # キットの在庫を消費する。足りなければ inventory の例外を ordering の例外に
            # 詰め替えて投げ、トランザクションごと注文を取り消す。キャンセル時の戻しは
            # inventory が OrderCancelled を購読して行う。
            try:
                allocate_for_order(
                    order.id, [(line.menu_item_id, line.quantity) for line in order.lines]
                )
            except InsufficientStock as exc:
                raise OutOfStock(exc.menu_item_id, exc.name, exc.requested, exc.available) from exc
            self._order_repository.save(order)
            # 集約が保持していたイベントを取り出して発行する。同一トランザクション内で
            # 同期的にハンドラが呼ばれるため、ハンドラ(kitchen のチケット作成)が失敗すれば
            # 注文自体もロールバックされる。
            publish(order.collect_events())

        return OrderDTO.from_entity(order)
