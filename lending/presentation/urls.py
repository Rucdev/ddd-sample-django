from django.urls import path

from lending.presentation import api, views

# app_name で名前空間化し、config/urls.py から include() で束ねる(画面 + API 両方をここに集約)。
app_name = "lending"

urlpatterns = [
    path("", views.loan_list_view, name="loan_list"),
    path("loan/", views.loan_book_view, name="loan_book"),
    path("<uuid:loan_id>/return/", views.return_book_view, name="return_book"),
    path("<uuid:loan_id>/renew/", views.renew_loan_view, name="renew_loan"),
    path("api/loans/", api.LoanListCreateAPIView.as_view(), name="api_loan_list"),
    path(
        "api/loans/<uuid:loan_id>/return/",
        api.ReturnBookAPIView.as_view(),
        name="api_return_book",
    ),
    path(
        "api/loans/<uuid:loan_id>/renew/",
        api.RenewLoanAPIView.as_view(),
        name="api_renew_loan",
    ),
]
