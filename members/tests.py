import uuid

from django.db import IntegrityError, transaction
from django.test import TestCase

from members import public
from members.models import Member


class MemberModelTests(TestCase):
    def test_email_must_be_unique(self) -> None:
        Member.objects.create(name="Alice", email="alice@example.com")

        with self.assertRaises(IntegrityError), transaction.atomic():
            Member.objects.create(name="Alice Duplicate", email="alice@example.com")

    def test_default_status_is_active(self) -> None:
        member = Member.objects.create(name="Alice", email="alice@example.com")

        self.assertEqual(member.status, Member.Status.ACTIVE)


class PublicApiTests(TestCase):
    def setUp(self) -> None:
        self.member = Member.objects.create(name="Alice", email="alice@example.com")

    def test_get_member_returns_dto(self) -> None:
        dto = public.get_member(self.member.id)

        assert dto is not None
        self.assertEqual(dto.name, "Alice")
        self.assertTrue(dto.is_active)

    def test_get_member_returns_none_when_not_found(self) -> None:
        self.assertIsNone(public.get_member(uuid.uuid4()))

    def test_suspend_member_flips_status(self) -> None:
        public.suspend_member(self.member.id)

        dto = public.get_member(self.member.id)
        assert dto is not None
        self.assertFalse(dto.is_active)

    def test_reinstate_member_flips_status_back(self) -> None:
        public.suspend_member(self.member.id)
        public.reinstate_member(self.member.id)

        dto = public.get_member(self.member.id)
        assert dto is not None
        self.assertTrue(dto.is_active)
