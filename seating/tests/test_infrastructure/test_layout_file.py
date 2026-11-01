from pathlib import Path
from unittest import TestCase

from django.conf import settings

from seating.domain.exceptions import InvalidSeatLayout
from seating.infrastructure.layout_file import load_seat_layout, parse_seat_layout

VALID = """
areas:
  - code: counter
    name: カウンター
    seats:
      - {code: C1, row: 1, col: 1}
  - code: table
    seats:
      - {code: T1, row: 1, col: 1, capacity: 4}
"""


class ParseSeatLayoutTests(TestCase):
    def test_parses_areas_in_file_order_and_seats(self) -> None:
        layout = parse_seat_layout(VALID)

        self.assertEqual([(a.code, a.name, a.display_order) for a in layout.areas], [
            ("counter", "カウンター", 1),
            ("table", "table", 2),  # name を省くとコードを名前にする
        ])
        c1 = layout.seat("C1")
        assert c1 is not None
        self.assertEqual((c1.area_code, c1.capacity), ("counter", 1))  # capacity の既定は 1
        t1 = layout.seat("T1")
        assert t1 is not None
        self.assertEqual(t1.capacity, 4)

    def test_rejects_broken_files(self) -> None:
        cases = {
            "not yaml": "areas: [",
            "no areas": "seats: []",
            "area without seats": "areas:\n  - {code: a}",
            "seat without row": "areas:\n  - {code: a, seats: [{code: S1, col: 1}]}",
            "non integer capacity": "areas:\n  - {code: a, seats: [{code: S1, row: 1, col: 1, capacity: many}]}",
            "boolean position": "areas:\n  - {code: a, seats: [{code: S1, row: true, col: 1}]}",
            "overlapping seats": "areas:\n  - {code: a, seats: [{code: S1, row: 1, col: 1}, {code: S2, row: 1, col: 1}]}",
        }
        for label, text in cases.items():
            with self.subTest(label), self.assertRaises(InvalidSeatLayout):
                parse_seat_layout(text)

    def test_missing_file(self) -> None:
        with self.assertRaisesRegex(InvalidSeatLayout, "Cannot read"):
            load_seat_layout(Path("/nonexistent/seat_layout.yaml"))

    def test_bundled_layout_file_is_valid(self) -> None:
        layout = load_seat_layout(settings.SEAT_LAYOUT_FILE)

        self.assertGreater(len(layout.seats), 0)
