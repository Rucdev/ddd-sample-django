import uuid

from django.db import IntegrityError, transaction
from django.test import TestCase

from catalog import public
from catalog.models import Copy, Title


class TitleModelTests(TestCase):
    def test_isbn_must_be_unique(self) -> None:
        Title.objects.create(name="Domain-Driven Design", author="Eric Evans", isbn="9780321125217")

        with self.assertRaises(IntegrityError), transaction.atomic():
            Title.objects.create(name="Duplicate", author="Someone", isbn="9780321125217")


class CopyModelTests(TestCase):
    def setUp(self) -> None:
        self.title = Title.objects.create(
            name="Domain-Driven Design", author="Eric Evans", isbn="9780321125217"
        )

    def test_copy_number_must_be_unique_per_title(self) -> None:
        Copy.objects.create(title=self.title, copy_number=1)

        with self.assertRaises(IntegrityError), transaction.atomic():
            Copy.objects.create(title=self.title, copy_number=1)

    def test_default_status_is_active(self) -> None:
        copy = Copy.objects.create(title=self.title, copy_number=1)

        self.assertEqual(copy.status, Copy.Status.ACTIVE)


class PublicApiTests(TestCase):
    def setUp(self) -> None:
        self.title = Title.objects.create(
            name="Domain-Driven Design", author="Eric Evans", isbn="9780321125217"
        )
        self.copy = Copy.objects.create(title=self.title, copy_number=1)

    def test_get_title_returns_dto(self) -> None:
        dto = public.get_title(self.title.id)

        assert dto is not None
        self.assertEqual(dto.name, "Domain-Driven Design")
        self.assertEqual(dto.isbn, "9780321125217")

    def test_get_title_returns_none_when_not_found(self) -> None:
        self.assertIsNone(public.get_title(uuid.uuid4()))

    def test_get_copy_returns_dto_with_title_name(self) -> None:
        dto = public.get_copy(self.copy.id)

        assert dto is not None
        self.assertEqual(dto.title_id, self.title.id)
        self.assertEqual(dto.title_name, "Domain-Driven Design")
        self.assertTrue(dto.is_active)

    def test_get_copy_reflects_withdrawn_status(self) -> None:
        self.copy.status = Copy.Status.WITHDRAWN
        self.copy.save()

        dto = public.get_copy(self.copy.id)

        assert dto is not None
        self.assertFalse(dto.is_active)

    def test_get_copy_returns_none_when_not_found(self) -> None:
        self.assertIsNone(public.get_copy(uuid.uuid4()))
