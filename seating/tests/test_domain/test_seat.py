from unittest import TestCase

from seating.domain.entities import Seat
from seating.domain.exceptions import InvalidSeatTransition
from seating.domain.value_objects import SeatStatus
from seating.tests.factories import seat_spec


def _seat() -> Seat:
    return Seat.install(seat_spec("T1"))


class SeatTransitionTests(TestCase):
    def test_installed_seat_is_available(self) -> None:
        self.assertEqual(_seat().status, SeatStatus.AVAILABLE)

    def test_reserve_then_occupy_then_vacate(self) -> None:
        seat = _seat()

        seat.reserve()
        self.assertEqual(seat.status, SeatStatus.RESERVED)
        seat.occupy()
        self.assertEqual(seat.status, SeatStatus.OCCUPIED)
        seat.vacate()
        self.assertEqual(seat.status, SeatStatus.AVAILABLE)

    def test_walk_in_occupies_available_seat(self) -> None:
        seat = _seat()

        seat.occupy()

        self.assertEqual(seat.status, SeatStatus.OCCUPIED)

    def test_cancel_reservation_frees_seat(self) -> None:
        seat = _seat()
        seat.reserve()

        seat.cancel_reservation()

        self.assertEqual(seat.status, SeatStatus.AVAILABLE)

    def test_invalid_transitions_are_rejected(self) -> None:
        cases = [
            (SeatStatus.RESERVED, Seat.reserve),
            (SeatStatus.OCCUPIED, Seat.reserve),
            (SeatStatus.AVAILABLE, Seat.cancel_reservation),
            (SeatStatus.OCCUPIED, Seat.cancel_reservation),
            (SeatStatus.OCCUPIED, Seat.occupy),
            (SeatStatus.AVAILABLE, Seat.vacate),
            (SeatStatus.RESERVED, Seat.vacate),
        ]
        for status, action in cases:
            with self.subTest(status=status, action=action.__name__):
                seat = _seat()
                seat.status = status

                with self.assertRaises(InvalidSeatTransition):
                    action(seat)
                self.assertEqual(seat.status, status)

    def test_only_available_seat_is_removable(self) -> None:
        seat = _seat()
        self.assertTrue(seat.is_removable)
        seat.reserve()
        self.assertFalse(seat.is_removable)

    def test_apply_spec_keeps_status(self) -> None:
        seat = _seat()
        seat.occupy()

        seat.apply_spec(seat_spec("T1", capacity=4, row=2, col=3))

        self.assertEqual(seat.capacity, 4)
        self.assertEqual((seat.position.row, seat.position.col), (2, 3))
        self.assertEqual(seat.status, SeatStatus.OCCUPIED)
