from django.urls import path

from ordering.presentation.commands import api as command_api
from ordering.presentation.commands import views as command_views
from ordering.presentation.queries import api as query_api
from ordering.presentation.queries import views as query_views
from ordering.presentation.routing import by_method

# app_name で名前空間化し、config/urls.py から include() で束ねる(画面 + API 両方をここに集約)。
# View は commands/(C)と queries/(Q)に分けるが、URL はリソースの名前のまま揃えない。
# C/Q の区別は HTTP メソッドとドメインの動詞(cancel / pick-up)で URL に現れている。
app_name = "ordering"

urlpatterns = [
    path("", query_views.order_list_view, name="order_list"),
    path("place/", command_views.place_order_view, name="place_order"),
    path("<uuid:order_id>/cancel/", command_views.cancel_order_view, name="cancel_order"),
    path("<uuid:order_id>/pick-up/", command_views.pick_up_order_view, name="pick_up_order"),
    path(
        "api/orders/",
        by_method(
            get=query_api.OrderListAPIView.as_view(),
            post=command_api.PlaceOrderAPIView.as_view(),
        ),
        name="api_order_list",
    ),
    path(
        "api/orders/<uuid:order_id>/cancel/",
        command_api.CancelOrderAPIView.as_view(),
        name="api_cancel_order",
    ),
    path(
        "api/orders/<uuid:order_id>/pick-up/",
        command_api.PickUpOrderAPIView.as_view(),
        name="api_pick_up_order",
    ),
]
