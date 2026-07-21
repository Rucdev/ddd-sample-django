from rest_framework.response import Response
from rest_framework.views import APIView

from lending.application.dto import LoanBookInput, RenewLoanInput, ReturnBookInput
from lending.application.queries import list_loans
from lending.application.use_cases.loan_book import LoanBookUseCase
from lending.application.use_cases.renew_loan import RenewLoanUseCase
from lending.application.use_cases.return_book import ReturnBookUseCase
from lending.infrastructure.repositories import DjangoLoanRepository
from lending.presentation.serializers import LoanBookSerializer, LoanSerializer


# DDD アプリでの DRF の使い方(ADR-0001): APIView と素の Serializer だけを使う。
# ModelSerializer / ModelViewSet は ORM モデルと API を直結させ、ユースケースを
# 迂回してしまうため使わない(CRUD アプリでは逆に主力として使ってよい)。
# ドメイン例外 → HTTP ステータスの変換は shared/infrastructure/exception_handler.py に一元化。


class LoanListCreateAPIView(APIView):
    def get(self, request):
        loans = list_loans()
        return Response(LoanSerializer(loans, many=True).data)

    def post(self, request):
        serializer = LoanBookSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        use_case = LoanBookUseCase(loan_repository=DjangoLoanRepository())
        result = use_case.execute(LoanBookInput(**serializer.validated_data))
        return Response(LoanSerializer(result).data, status=201)


class ReturnBookAPIView(APIView):
    def post(self, request, loan_id):
        use_case = ReturnBookUseCase(loan_repository=DjangoLoanRepository())
        result = use_case.execute(ReturnBookInput(loan_id=loan_id))
        return Response(LoanSerializer(result).data)


class RenewLoanAPIView(APIView):
    def post(self, request, loan_id):
        use_case = RenewLoanUseCase(loan_repository=DjangoLoanRepository())
        result = use_case.execute(RenewLoanInput(loan_id=loan_id))
        return Response(LoanSerializer(result).data)
