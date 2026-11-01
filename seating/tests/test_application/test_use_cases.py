import uuid

from django.test import TestCase

from seating.application.dto import SeatCommandInput
from seating.application.use_cases.apply_seat_layout import ApplySeatLayoutUseCase
from seating.application.use_cases.change_seat_status import (
    CancelSeatReservationUseCase,
    OccupySeatUseCase,
    ReserveSeatUseCase,
    VacateSeatUseCase,
)
from seating.domain.exceptions import InvalidSeatTransition, SeatNotFound, SeatsInUse
from seating.tests.factories import layout, seat_spec
from seating.tests.test_application.fakes import FakeAreaRepository, FakeSeatRepository

# ユースケースは transaction.atomic() を張るので django.test.TestCase で動かす(DB には触らない)。


class ApplySeatLayoutUseCaseTests(TestCase):
    def setUp(self) -> None:
        self.seats = FakeSeatRepository()
        self.areas = FakeAreaRepository()
        self.use_case = ApplySeatLayoutUseCase(seat_repository=self.seats, area_repository=self.areas)

    def test_first_apply_installs_all_seats_as_available(self) -> None:
        result = self.use_case.execute(layout(seat_spec("T1", col=1), seat_spec("T2", col=2)))

        self.assertEqual(self.seats.lock_count, 1)  # 反映中にステータスが変わらないよう全席をロックする

        self.assertEqual(result.installed, ("T1", "T2"))
        self.assertEqual({s.status for s in self.seats.seats.values()}, {"AVAILABLE"})
        self.assertEqual(list(self.areas.areas), ["table"])

    def test_reapplying_same_layout_changes_nothing(self) -> None:
        same = layout(seat_spec("T1"))
        self.use_case.execute(same)

        result = self.use_case.execute(same)

        self.assertEqual((result.installed, result.changed, result.removed, result.unchanged), ((), (), (), 1))

    def test_moving_seat_to_new_area_keeps_status_and_drops_old_area(self) -> None:
        self.use_case.execute(layout(seat_spec("T1")))
        seat = self.seats.by_code("T1")
        seat.occupy()
        self.seats.save(seat)

        result = self.use_case.execute(layout(seat_spec("T1", area="terrace"), areas=("terrace",)))

        self.assertEqual(result.changed, ("T1",))
        moved = self.seats.by_code("T1")
        self.assertEqual((moved.area_code, moved.status), ("terrace", "OCCUPIED"))
        self.assertEqual(list(self.areas.areas), ["terrace"])

    def test_removing_seat_in_use_is_refused(self) -> None:
        self.use_case.execute(layout(seat_spec("T1")))
        seat = self.seats.by_code("T1")
        seat.reserve()
        self.seats.save(seat)

        with self.assertRaises(SeatsInUse):
            self.use_case.execute(layout())

        self.assertEqual(self.seats.by_code("T1").status, "RESERVED")


class ChangeSeatStatusUseCaseTests(TestCase):
    def setUp(self) -> None:
        self.repository = FakeSeatRepository()
        ApplySeatLayoutUseCase(
            seat_repository=self.repository, area_repository=FakeAreaRepository()
        ).execute(layout(seat_spec("T1")))
        self.seat_id = self.repository.by_code("T1").id

    def _run(self, use_case_class):
        return use_case_class(repository=self.repository).execute(SeatCommandInput(seat_id=self.seat_id))

    def test_reservation_flow(self) -> None:
        self.assertEqual(self._run(ReserveSeatUseCase).status, "RESERVED")
        self.assertEqual(self._run(OccupySeatUseCase).status, "OCCUPIED")
        self.assertEqual(self._run(VacateSeatUseCase).status, "AVAILABLE")
        self.assertEqual(self.repository.by_code("T1").status, "AVAILABLE")

    def test_cancel_reservation(self) -> None:
        self._run(ReserveSeatUseCase)

        self.assertEqual(self._run(CancelSeatReservationUseCase).status, "AVAILABLE")

    def test_invalid_transition_is_not_saved(self) -> None:
        with self.assertRaises(InvalidSeatTransition):
            self._run(VacateSeatUseCase)

        self.assertEqual(self.repository.by_code("T1").status, "AVAILABLE")

    def test_status_change_reads_the_seat_with_a_lock(self) -> None:
        # 予約と案内が同時に来ても、両方が「空き」を読んで両方成功しないように行ロックを取る
        before = self.repository.lock_count

        self._run(ReserveSeatUseCase)

        self.assertEqual(self.repository.lock_count, before + 1)

    def test_unknown_seat(self) -> None:
        with self.assertRaises(SeatNotFound):
            ReserveSeatUseCase(repository=self.repository).execute(SeatCommandInput(seat_id=uuid.uuid4()))
