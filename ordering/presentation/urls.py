from django.urls import path

from ordering.presentation.commands import api as command_api
from ordering.presentation.commands import views as command_views
from ordering.presentation.queries import api as query_api
from ordering.presentation.queries import views as query_views
from ordering.presentation.routing import by_method

# app_name で名前空間化し、config/urls.py から include() で束ねる(画面 + API 両方をここに集約)。
# View は commands/(C)と queries/(Q)に分けるが、URL はリソースの名前のまま揃えない。
# C/Q の区別は HTTP メソッドとドメインの動詞(cancel / pick-up / serve)で URL に現れている。
app_name = "ordering"

urlpatterns = [
    path("", query_views.order_list_view, name="order_list"),
    path("place/", command_views.place_order_view, name="place_order"),
    path("<uuid:order_id>/cancel/", command_views.cancel_order_view, name="cancel_order"),
    path("<uuid:order_id>/pick-up/", command_views.pick_up_order_view, name="pick_up_order"),
    # 店内: 席からの注文(お客様)と、ホール画面での提供完了(店員)
    path("seats/<uuid:seat_id>/", query_views.seat_order_view, name="seat_order"),
    path("seats/<uuid:seat_id>/place/", command_views.place_seat_order_view, name="place_seat_order"),
    path(
        "seats/<uuid:seat_id>/orders/<uuid:order_id>/cancel/",
        command_views.cancel_seat_order_view,
        name="cancel_seat_order",
    ),
    path("floor/", query_views.floor_view, name="floor"),
    path("<uuid:order_id>/serve/", command_views.serve_order_view, name="serve_order"),
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
    path(
        "api/orders/<uuid:order_id>/serve/",
        command_api.ServeOrderAPIView.as_view(),
        name="api_serve_order",
    ),
    path(
        "api/seats/<uuid:seat_id>/orders/",
        command_api.PlaceSeatOrderAPIView.as_view(),
        name="api_place_seat_order",
    ),
    path("api/seats/<uuid:seat_id>/bill/", query_api.SeatBillAPIView.as_view(), name="api_seat_bill"),
]
