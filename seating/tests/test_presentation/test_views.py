import uuid
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

from django.core.management import CommandError, call_command
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from seating.infrastructure.models import AreaModel, SeatModel

LAYOUT = """
areas:
  - code: counter
    name: カウンター
    seats:
      - {code: C1, row: 1, col: 1}
  - code: table
    name: テーブル席
    seats:
      - {code: T1, row: 1, col: 1, capacity: 4}
      - {code: T2, row: 1, col: 2, capacity: 2}
"""


class _LayoutMixin:
    def setUp(self) -> None:
        super().setUp()  # type: ignore[misc]
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)  # type: ignore[attr-defined]
        self.apply(LAYOUT)

    def apply(self, text: str) -> str:
        path = Path(self.tmp.name) / "layout.yaml"
        path.write_text(text, encoding="utf-8")
        out = StringIO()
        call_command("apply_seat_layout", file=str(path), stdout=out)
        return out.getvalue()

    def seat(self, code: str) -> SeatModel:
        return SeatModel.objects.get(code=code)


class ApplySeatLayoutCommandTests(_LayoutMixin, TestCase):
    def test_layout_is_written_to_db(self) -> None:
        self.assertEqual(list(AreaModel.objects.values_list("code", "name")), [
            ("counter", "カウンター"),
            ("table", "テーブル席"),
        ])
        self.assertEqual(
            list(SeatModel.objects.values_list("code", "area__code", "capacity", "status")),
            [("C1", "counter", 1, "AVAILABLE"), ("T1", "table", 4, "AVAILABLE"), ("T2", "table", 2, "AVAILABLE")],
        )

    def test_reapply_reports_changes_and_keeps_status(self) -> None:
        SeatModel.objects.filter(code="T1").update(status="OCCUPIED")

        out = self.apply(LAYOUT.replace("capacity: 4", "capacity: 6").replace(
            "      - {code: T2, row: 1, col: 2, capacity: 2}\n", "      - {code: T3, row: 2, col: 1}\n"
        ))

        self.assertIn("追加 1 / 変更 1 / 撤去 1 / 変更なし 1", out)
        self.assertEqual((self.seat("T1").capacity, self.seat("T1").status), (6, "OCCUPIED"))
        self.assertFalse(SeatModel.objects.filter(code="T2").exists())

    def test_removing_area_with_its_seats(self) -> None:
        self.apply(LAYOUT.split("  - code: table")[0])

        self.assertEqual(list(AreaModel.objects.values_list("code", flat=True)), ["counter"])
        self.assertEqual(list(SeatModel.objects.values_list("code", flat=True)), ["C1"])

    def test_seat_in_use_blocks_the_whole_apply(self) -> None:
        SeatModel.objects.filter(code="T2").update(status="RESERVED")

        with self.assertRaisesRegex(CommandError, "T2"):
            self.apply(LAYOUT.replace("capacity: 4", "capacity: 6").replace(
                "      - {code: T2, row: 1, col: 2, capacity: 2}\n", ""
            ))

        self.assertEqual(self.seat("T1").capacity, 4)  # 何も変わっていない
        self.assertTrue(SeatModel.objects.filter(code="T2").exists())

    def test_invalid_file_is_reported(self) -> None:
        with self.assertRaisesRegex(CommandError, "Duplicate seat code"):
            self.apply(LAYOUT.replace("code: T2", "code: T1"))


class SeatBoardViewTests(_LayoutMixin, TestCase):
    def test_board_shows_areas_seats_and_summary(self) -> None:
        SeatModel.objects.filter(code="T1").update(status="OCCUPIED")
        SeatModel.objects.filter(code="T2").update(status="RESERVED")

        response = self.client.get(reverse("seating:seat_board"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "テーブル席")
        self.assertContains(response, '<span class="seat__code">T1</span>', html=True)
        summary = {s.status: (s.seats, s.capacity) for s in response.context["summary"]}
        self.assertEqual(summary, {"AVAILABLE": (1, 1), "RESERVED": (1, 2), "OCCUPIED": (1, 4)})
        self.assertEqual(response.context["occupancy_rate"], 33)
        self.assertContains(response, reverse("seating:vacate", args=[self.seat("T1").id]))
        self.assertContains(response, reverse("seating:cancel_reservation", args=[self.seat("T2").id]))

    def test_board_without_seats_explains_how_to_load_layout(self) -> None:
        SeatModel.objects.all().delete()
        AreaModel.objects.all().delete()

        response = self.client.get(reverse("seating:seat_board"))

        self.assertContains(response, "apply_seat_layout")
        self.assertEqual(response.context["occupancy_rate"], 0)

    def test_reserve_occupy_vacate(self) -> None:
        seat_id = self.seat("T1").id

        response = self.client.post(reverse("seating:reserve", args=[seat_id]))
        self.assertRedirects(response, reverse("seating:seat_board"))
        self.assertEqual(self.seat("T1").status, "RESERVED")
        reserved_at = self.seat("T1").status_changed_at

        self.client.post(reverse("seating:occupy", args=[seat_id]))
        self.assertEqual(self.seat("T1").status, "OCCUPIED")
        self.assertGreater(self.seat("T1").status_changed_at, reserved_at)

        self.client.post(reverse("seating:vacate", args=[seat_id]))
        self.assertEqual(self.seat("T1").status, "AVAILABLE")

    def test_cancel_reservation(self) -> None:
        seat_id = self.seat("T1").id
        self.client.post(reverse("seating:reserve", args=[seat_id]))

        response = self.client.post(reverse("seating:cancel_reservation", args=[seat_id]), follow=True)

        self.assertEqual(self.seat("T1").status, "AVAILABLE")
        self.assertIn("T1 の予約を取り消しました。", [str(m) for m in response.context["messages"]])

    def test_invalid_transition_becomes_message(self) -> None:
        response = self.client.post(reverse("seating:vacate", args=[self.seat("T1").id]), follow=True)

        self.assertTrue(any("cannot be vacated" in str(m) for m in response.context["messages"]))

    def test_get_is_not_allowed_for_commands(self) -> None:
        response = self.client.get(reverse("seating:reserve", args=[self.seat("T1").id]))

        self.assertEqual(response.status_code, 405)


class SeatAPITests(_LayoutMixin, TestCase):
    def setUp(self) -> None:
        super().setUp()
        self.api = APIClient()

    def test_list_and_filter(self) -> None:
        SeatModel.objects.filter(code="T1").update(status="OCCUPIED")

        all_seats = self.api.get(reverse("seating:api_seat_list")).json()
        self.assertEqual([s["code"] for s in all_seats], ["C1", "T1", "T2"])
        self.assertEqual(all_seats[1]["area_code"], "table")

        free_tables = self.api.get(
            reverse("seating:api_seat_list"), {"status": "AVAILABLE", "area": "table"}
        ).json()
        self.assertEqual([s["code"] for s in free_tables], ["T2"])

        big = self.api.get(reverse("seating:api_seat_list"), {"min_capacity": 4}).json()
        self.assertEqual([s["code"] for s in big], ["T1"])

    def test_commands(self) -> None:
        seat_id = self.seat("T2").id

        response = self.api.post(reverse("seating:api_occupy", args=[seat_id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["status"], "OCCUPIED")

        response = self.api.post(reverse("seating:api_reserve", args=[seat_id]))
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

        response = self.api.post(reverse("seating:api_vacate", args=[seat_id]))
        self.assertEqual(response.json()["status"], "AVAILABLE")

        response = self.api.post(reverse("seating:api_reserve", args=[seat_id]))
        self.assertEqual(response.json()["status"], "RESERVED")
        response = self.api.post(reverse("seating:api_cancel_reservation", args=[seat_id]))
        self.assertEqual(response.json()["status"], "AVAILABLE")

    def test_unknown_seat_is_404(self) -> None:
        response = self.api.post(reverse("seating:api_reserve", args=[uuid.uuid4()]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
