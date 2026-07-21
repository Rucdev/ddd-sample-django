import uuid
from datetime import date

from django.test import TestCase

from catalog.models import Title
from members.models import Member
from reservation.application.dto import ReserveTitleInput
from reservation.application.use_cases.reserve_title import ReserveTitleUseCase
from reservation.domain.exceptions import DuplicateReservation, MemberNotEligible, TitleNotFound
from reservation.tests.test_application.fakes import FakeReservationQueueRepository


class ReserveTitleUseCaseTests(TestCase):
    def setUp(self) -> None:
        self.member = Member.objects.create(name="Alice", email="alice@example.com")
        self.title = Title.objects.create(name="DDD", author="Evans", isbn="9780321125217")
        self.repository = FakeReservationQueueRepository()
        self.use_case = ReserveTitleUseCase(repository=self.repository)

    def test_reserves_title_for_active_member(self) -> None:
        result = self.use_case.execute(
            ReserveTitleInput(member_id=self.member.id, title_id=self.title.id),
            today=date(2026, 1, 1),
        )

        self.assertEqual(result.position, 1)
        self.assertEqual(result.member_id, self.member.id)

    def test_second_reservation_gets_position_two(self) -> None:
        self.use_case.execute(
            ReserveTitleInput(member_id=self.member.id, title_id=self.title.id),
            today=date(2026, 1, 1),
        )
        other_member = Member.objects.create(name="Bob", email="bob@example.com")

        result = self.use_case.execute(
            ReserveTitleInput(member_id=other_member.id, title_id=self.title.id),
            today=date(2026, 1, 2),
        )

        self.assertEqual(result.position, 2)

    def test_rejects_unknown_member(self) -> None:
        with self.assertRaises(MemberNotEligible):
            self.use_case.execute(
                ReserveTitleInput(member_id=uuid.uuid4(), title_id=self.title.id),
                today=date(2026, 1, 1),
            )

    def test_rejects_suspended_member(self) -> None:
        self.member.status = Member.Status.SUSPENDED
        self.member.save()

        with self.assertRaises(MemberNotEligible):
            self.use_case.execute(
                ReserveTitleInput(member_id=self.member.id, title_id=self.title.id),
                today=date(2026, 1, 1),
            )

    def test_rejects_unknown_title(self) -> None:
        with self.assertRaises(TitleNotFound):
            self.use_case.execute(
                ReserveTitleInput(member_id=self.member.id, title_id=uuid.uuid4()),
                today=date(2026, 1, 1),
            )

    def test_rejects_duplicate_reservation(self) -> None:
        self.use_case.execute(
            ReserveTitleInput(member_id=self.member.id, title_id=self.title.id),
            today=date(2026, 1, 1),
        )

        with self.assertRaises(DuplicateReservation):
            self.use_case.execute(
                ReserveTitleInput(member_id=self.member.id, title_id=self.title.id),
                today=date(2026, 1, 2),
            )
