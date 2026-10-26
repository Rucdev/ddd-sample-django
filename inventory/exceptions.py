import uuid

from shared.domain.exceptions import ConflictError, DomainError, NotFoundError

# ordering/domain/exceptions.py と同じく shared の NotFoundError / ConflictError を多重継承し、
# DRF の exception handler で 404 / 409 に変換されるようにする。


class InventoryError(DomainError):
    """Base class for inventory errors."""


class KitNotFound(InventoryError, NotFoundError):
    def __init__(self, kit_id: uuid.UUID) -> None:
        self.kit_id = kit_id
        super().__init__(f"Kit {kit_id} was not found")


class ReservationNotFound(InventoryError, NotFoundError):
    def __init__(self, reservation_id: uuid.UUID) -> None:
        self.reservation_id = reservation_id
        super().__init__(f"Reservation {reservation_id} was not found")


class UnknownMenuItem(InventoryError, ConflictError):
    def __init__(self, menu_item_id: uuid.UUID) -> None:
        self.menu_item_id = menu_item_id
        super().__init__(f"Menu item {menu_item_id} does not exist")


class InsufficientStock(InventoryError, ConflictError):
    """注文可能数(実在庫 − 確保中の予約数)が足りない。"""

    def __init__(self, menu_item_id: uuid.UUID, name: str, requested: int, available: int) -> None:
        self.menu_item_id = menu_item_id
        self.name = name
        self.requested = requested
        self.available = available
        super().__init__(f"Only {available} of {name} available, {requested} requested")


class KitInactive(InventoryError, ConflictError):
    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Kit {name} is not managed (inactive)")


class KitHasHeldReservations(InventoryError, ConflictError):
    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"Kit {name} has held reservations")


class ReservationNotHeld(InventoryError, ConflictError):
    def __init__(self, reservation_id: uuid.UUID, status: str) -> None:
        self.reservation_id = reservation_id
        self.status = status
        super().__init__(f"Reservation {reservation_id} is already {status}")
