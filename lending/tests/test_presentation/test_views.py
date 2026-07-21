from datetime import date

from django.test import TestCase
from django.urls import reverse

from catalog.models import Copy, Title
from lending.domain.entities import Loan
from lending.infrastructure.repositories import DjangoLoanRepository
from members.models import Member
from shared.infrastructure import event_bus


class LoanListViewTests(TestCase):
    def setUp(self) -> None:
        event_bus.clear_subscribers()
        self.addCleanup(event_bus.clear_subscribers)

        self.member = Member.objects.create(name="Alice", email="alice@example.com")
        self.title = Title.objects.create(name="DDD", author="Evans", isbn="9780321125217")
        self.copy = Copy.objects.create(title=self.title, copy_number=1)

    def test_loan_list_page_loads(self) -> None:
        response = self.client.get(reverse("lending:loan_list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "貸出一覧")

    def test_loan_book_creates_loan_and_redirects(self) -> None:
        response = self.client.post(
            reverse("lending:loan_book"),
            {"member_id": str(self.member.id), "copy_id": str(self.copy.id)},
        )

        self.assertRedirects(response, reverse("lending:loan_list"))
        self.assertEqual(DjangoLoanRepository().count_active_by_member(self.member.id), 1)

    def test_loan_book_with_invalid_input_shows_error_message(self) -> None:
        response = self.client.post(
            reverse("lending:loan_book"),
            {"member_id": "not-a-uuid", "copy_id": str(self.copy.id)},
            follow=True,
        )

        page_messages = list(response.context["messages"])
        self.assertTrue(any("入力内容" in str(m) for m in page_messages))

    def test_loan_book_with_domain_error_shows_error_message(self) -> None:
        self.copy.status = Copy.Status.WITHDRAWN
        self.copy.save()

        response = self.client.post(
            reverse("lending:loan_book"),
            {"member_id": str(self.member.id), "copy_id": str(self.copy.id)},
            follow=True,
        )

        page_messages = list(response.context["messages"])
        self.assertTrue(any("cannot be loaned" in str(m) for m in page_messages))

    def test_return_book_view(self) -> None:
        loan = Loan.start(
            member_id=self.member.id, copy_id=self.copy.id, loaned_at=date.today()
        )
        loan.collect_events()
        DjangoLoanRepository().save(loan)

        response = self.client.post(reverse("lending:return_book", args=[loan.id]))

        self.assertRedirects(response, reverse("lending:loan_list"))
        updated = DjangoLoanRepository().find_by_id(loan.id)
        self.assertIsNotNone(updated.returned_at)

    def test_renew_loan_view(self) -> None:
        loan = Loan.start(
            member_id=self.member.id, copy_id=self.copy.id, loaned_at=date.today()
        )
        loan.collect_events()
        DjangoLoanRepository().save(loan)

        response = self.client.post(reverse("lending:renew_loan", args=[loan.id]))

        self.assertRedirects(response, reverse("lending:loan_list"))
        updated = DjangoLoanRepository().find_by_id(loan.id)
        self.assertEqual(updated.renewal_count, 1)
