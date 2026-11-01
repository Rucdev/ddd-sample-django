from unittest import TestCase

from seating.domain.entities import Seat
from seating.domain.exceptions import InvalidSeatLayout, SeatsInUse
from seating.domain.services import plan_layout_changes
from seating.tests.factories import layout, seat_spec


class SeatLayoutTests(TestCase):
    def test_duplicate_seat_codes_are_rejected(self) -> None:
        with self.assertRaisesRegex(InvalidSeatLayout, "Duplicate seat code: T1"):
            layout(seat_spec("T1", col=1), seat_spec("T1", col=2))

    def test_duplicate_area_codes_are_rejected(self) -> None:
        with self.assertRaisesRegex(InvalidSeatLayout, "Duplicate area code"):
            layout(areas=("table", "table"))

    def test_seats_must_not_overlap_in_the_same_area(self) -> None:
        with self.assertRaisesRegex(InvalidSeatLayout, "Duplicate seat position"):
            layout(seat_spec("T1"), seat_spec("T2"))

    def test_same_position_in_different_areas_is_fine(self) -> None:
        layout(seat_spec("T1"), seat_spec("R1", area="terrace"), areas=("table", "terrace"))

    def test_seat_must_belong_to_known_area(self) -> None:
        with self.assertRaisesRegex(InvalidSeatLayout, "unknown area terrace"):
            layout(seat_spec("R1", area="terrace"))

    def test_capacity_and_position_must_be_positive(self) -> None:
        with self.assertRaises(InvalidSeatLayout):
            seat_spec("T1", capacity=0)
        with self.assertRaises(InvalidSeatLayout):
            seat_spec("T1", row=0)


class PlanLayoutChangesTests(TestCase):
    def test_diff_by_seat_code(self) -> None:
        kept = Seat.install(seat_spec("T1", col=1))
        moved = Seat.install(seat_spec("T2", col=2))
        gone = Seat.install(seat_spec("T3", col=3))

        changes = plan_layout_changes(
            [kept, moved, gone],
            layout(seat_spec("T1", col=1), seat_spec("T2", col=3, capacity=4), seat_spec("T9", col=2)),
        )

        self.assertEqual([s.code for s in changes.installed], ["T9"])
        self.assertEqual([s.code for s in changes.changed], ["T2"])
        self.assertEqual(changes.changed[0].capacity, 4)
        self.assertEqual([s.code for s in changes.removed], ["T3"])
        self.assertEqual(changes.unchanged, 1)

    def test_changed_seat_keeps_its_status(self) -> None:
        seat = Seat.install(seat_spec("T1"))
        seat.occupy()

        changes = plan_layout_changes([seat], layout(seat_spec("T1", capacity=6)))

        self.assertEqual(changes.changed[0].status, "OCCUPIED")

    def test_seats_in_use_cannot_be_removed(self) -> None:
        reserved = Seat.install(seat_spec("T1", col=1))
        reserved.reserve()
        occupied = Seat.install(seat_spec("T2", col=2))
        occupied.occupy()

        with self.assertRaises(SeatsInUse) as ctx:
            plan_layout_changes([reserved, occupied], layout())

        self.assertEqual(ctx.exception.codes, ("T1", "T2"))
