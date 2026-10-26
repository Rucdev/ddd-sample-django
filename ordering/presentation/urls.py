from django.urls import path

from ordering.presentation import api, views

# app_name で名前空間化し、config/urls.py から include() で束ねる(画面 + API 両方をここに集約)。
app_name = "ordering"

urlpatterns = [
    path("", views.order_list_view, name="order_list"),
    path("place/", views.place_order_view, name="place_order"),
    path("<uuid:order_id>/cancel/", views.cancel_order_view, name="cancel_order"),
    path("<uuid:order_id>/pick-up/", views.pick_up_order_view, name="pick_up_order"),
    path("api/orders/", api.OrderListCreateAPIView.as_view(), name="api_order_list"),
    path(
        "api/orders/<uuid:order_id>/cancel/",
        api.CancelOrderAPIView.as_view(),
        name="api_cancel_order",
    ),
    path(
        "api/orders/<uuid:order_id>/pick-up/",
        api.PickUpOrderAPIView.as_view(),
        name="api_pick_up_order",
    ),
]
