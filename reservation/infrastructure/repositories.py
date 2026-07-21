import uuid
from datetime import date

from reservation.domain.entities import ReservationQueue
from reservation.domain.value_objects import Hold, Reservation
from reservation.infrastructure.models import HoldModel, ReservationModel


class DjangoReservationQueueRepository:
    """`ReservationQueueRepository` の Django ORM 実装。

    `save()` は集約が持つ予約・取置のリストを、その書誌分だけ一度 delete してから
    bulk_create で作り直す(差分更新はしない)。待ち行列は数件程度で済む規模のため、
    集約全体を丸ごと洗い替えるほうが diff ロジックより単純で、実装ミスも起きにくい。

    そのため予約 1 件ごとの DB 上の行 ID は保存のたびに変わりうる。「この予約を取り消す」
    という操作の URL/API は行 ID ではなく (title_id, member_id) の組をキーにしている
    (presentation 層・public.py 参照)。
    """

    def find_by_title(self, title_id: uuid.UUID) -> ReservationQueue:
        reservations = [
            Reservation(member_id=model.member_id, requested_at=model.requested_at)
            for model in ReservationModel.objects.filter(title_id=title_id).order_by(
                "requested_at"
            )
        ]
        holds = [
            Hold(copy_id=model.copy_id, member_id=model.member_id, expires_at=model.expires_at)
            for model in HoldModel.objects.filter(title_id=title_id)
        ]
        return ReservationQueue(title_id=title_id, reservations=reservations, holds=holds)

    def save(self, queue: ReservationQueue) -> None:
        # 洗い替え: 集約の予約・取置をそのまま作り直す(上のクラス docstring 参照)。
        ReservationModel.objects.filter(title_id=queue.title_id).delete()
        ReservationModel.objects.bulk_create(
            ReservationModel(
                title_id=queue.title_id,
                member_id=reservation.member_id,
                requested_at=reservation.requested_at,
            )
            for reservation in queue.reservations
        )

        HoldModel.objects.filter(title_id=queue.title_id).delete()
        HoldModel.objects.bulk_create(
            HoldModel(
                title_id=queue.title_id,
                copy_id=hold.copy_id,
                member_id=hold.member_id,
                expires_at=hold.expires_at,
            )
            for hold in queue.holds
        )

    def find_hold_by_copy(self, copy_id: uuid.UUID) -> Hold | None:
        model = HoldModel.objects.filter(copy_id=copy_id).first()
        if model is None:
            return None
        return Hold(copy_id=model.copy_id, member_id=model.member_id, expires_at=model.expires_at)

    def titles_with_expired_holds(self, today: date) -> list[uuid.UUID]:
        return list(
            HoldModel.objects.filter(expires_at__lt=today)
            .values_list("title_id", flat=True)
            .distinct()
        )
