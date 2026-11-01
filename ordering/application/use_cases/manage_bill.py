"""席の会計を開く / 締めるユースケース。seating の `SeatOccupied` / `SeatVacated` イベント
(`ordering/infrastructure/event_handlers.py`)から呼ばれ、画面・API からは呼ばれない。
"""

import uuid

from django.db import transaction

from ordering.domain.entities import Bill
from ordering.domain.repositories import BillRepository


class OpenBillUseCase:
    """席の利用が始まったら、その席の会計を開く。"""

    def __init__(self, bill_repository: BillRepository) -> None:
        self._bill_repository = bill_repository

    def execute(self, seat_id: uuid.UUID, seat_code: str) -> None:
        with transaction.atomic():
            # 同じ席に開いている会計が残っていたら、それを使い続ける(二重に開かない)。
            # 席は「使用中 → 使用中」には遷移しないので通常は起きないが、イベントが
            # 二度届いても会計が分かれないように冪等にしておく。
            if self._bill_repository.find_open_by_seat(seat_id, for_update=True) is not None:
                return
            self._bill_repository.save(Bill.open(seat_id=seat_id, seat_code=seat_code))


class SettleBillUseCase:
    """席の利用が終わったら、その席の会計を支払済にする。"""

    def __init__(self, bill_repository: BillRepository) -> None:
        self._bill_repository = bill_repository

    def execute(self, seat_id: uuid.UUID) -> None:
        with transaction.atomic():
            bill = self._bill_repository.find_open_by_seat(seat_id, for_update=True)
            # 会計がない = この機能を入れる前から使用中だった席。締めるものがないので何もしない。
            if bill is None:
                return
            bill.settle()
            self._bill_repository.save(bill)
