"""Public API of the inventory module. Other modules must only import from here."""

from inventory.exceptions import InsufficientStock
from inventory.services import allocate_for_order

# ordering は注文受付のトランザクションの中で allocate_for_order を呼び、足りなければ
# InsufficientStock を受け取る。キャンセル時の戻しは OrderCancelled の購読で行うので
# ここには出さない(inventory/event_handlers.py)。
__all__ = ["InsufficientStock", "allocate_for_order"]
