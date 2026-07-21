from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from lending.application.dto import LoanBookInput, RenewLoanInput, ReturnBookInput
from lending.application.queries import list_loans
from lending.application.use_cases.loan_book import LoanBookUseCase
from lending.application.use_cases.renew_loan import RenewLoanUseCase
from lending.application.use_cases.return_book import ReturnBookUseCase
from lending.domain.exceptions import LendingError
from lending.infrastructure.repositories import DjangoLoanRepository
from lending.presentation.forms import LoanBookForm


def loan_list_view(request):
    loans = list_loans()
    form = LoanBookForm()
    return render(request, "lending/loan_list.html", {"loans": loans, "form": form})


@require_http_methods(["POST"])
def loan_book_view(request):
    form = LoanBookForm(request.POST)
    if form.is_valid():
        use_case = LoanBookUseCase(loan_repository=DjangoLoanRepository())
        try:
            use_case.execute(
                LoanBookInput(
                    member_id=form.cleaned_data["member_id"],
                    copy_id=form.cleaned_data["copy_id"],
                )
            )
            messages.success(request, "貸出を登録しました。")
        except LendingError as exc:
            messages.error(request, str(exc))
    else:
        messages.error(request, "入力内容を確認してください。")
    return redirect("lending:loan_list")


@require_http_methods(["POST"])
def return_book_view(request, loan_id):
    use_case = ReturnBookUseCase(loan_repository=DjangoLoanRepository())
    try:
        use_case.execute(ReturnBookInput(loan_id=loan_id))
        messages.success(request, "返却を登録しました。")
    except LendingError as exc:
        messages.error(request, str(exc))
    return redirect("lending:loan_list")


@require_http_methods(["POST"])
def renew_loan_view(request, loan_id):
    use_case = RenewLoanUseCase(loan_repository=DjangoLoanRepository())
    try:
        use_case.execute(RenewLoanInput(loan_id=loan_id))
        messages.success(request, "貸出を延長しました。")
    except LendingError as exc:
        messages.error(request, str(exc))
    return redirect("lending:loan_list")
