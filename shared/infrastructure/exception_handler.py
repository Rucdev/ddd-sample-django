from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from shared.domain.exceptions import ConflictError, NotFoundError


def domain_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is not None:
        return response

    if isinstance(exc, NotFoundError):
        return Response({"detail": str(exc)}, status=404)
    if isinstance(exc, ConflictError):
        return Response({"detail": str(exc)}, status=409)

    return None
