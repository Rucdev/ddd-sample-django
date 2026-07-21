import uuid
from datetime import date

from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from catalog.models import Copy, Title
from lending.domain.entities import Loan
from lending.infrastructure.repositories import DjangoLoanRepository
from members.models import Member
from shared.infrastructure import event_bus


class LoanAPITests(TestCase):
    def setUp(self) -> None:
        event_bus.clear_subscribers()
        self.addCleanup(event_bus.clear_subscribers)

        self.client = APIClient()
        self.member = Member.objects.create(name="Alice", email="alice@example.com")
        self.title = Title.objects.create(name="DDD", author="Evans", isbn="9780321125217")
        self.copy = Copy.objects.create(title=self.title, copy_number=1)

    def test_get_loans_returns_empty_list_initially(self) -> None:
        response = self.client.get(reverse("lending:api_loan_list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_post_loans_creates_loan(self) -> None:
        response = self.client.post(
            reverse("lending:api_loan_list"),
            {"member_id": str(self.member.id), "copy_id": str(self.copy.id)},
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["member_id"], str(self.member.id))

    def test_post_loans_with_invalid_input_returns_400(self) -> None:
        response = self.client.post(reverse("lending:api_loan_list"), {"member_id": "nope"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_loans_domain_conflict_returns_409(self) -> None:
        self.copy.status = Copy.Status.WITHDRAWN
        self.copy.save()

        response = self.client.post(
            reverse("lending:api_loan_list"),
            {"member_id": str(self.member.id), "copy_id": str(self.copy.id)},
        )

        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_return_book_api(self) -> None:
        loan = Loan.start(
            member_id=self.member.id, copy_id=self.copy.id, loaned_at=date.today()
        )
        loan.collect_events()
        DjangoLoanRepository().save(loan)

        response = self.client.post(reverse("lending:api_return_book", args=[loan.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNotNone(response.data["returned_at"])

    def test_return_book_api_not_found_returns_404(self) -> None:
        response = self.client.post(reverse("lending:api_return_book", args=[uuid.uuid4()]))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_renew_loan_api(self) -> None:
        loan = Loan.start(
            member_id=self.member.id, copy_id=self.copy.id, loaned_at=date.today()
        )
        loan.collect_events()
        DjangoLoanRepository().save(loan)

        response = self.client.post(reverse("lending:api_renew_loan", args=[loan.id]))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["renewal_count"], 1)
