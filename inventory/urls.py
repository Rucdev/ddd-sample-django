from django.urls import include, path
from rest_framework.routers import DefaultRouter

from inventory import api, views

app_name = "inventory"

# use_regex_path=False にすると、ViewSet の lookup_value_converter("uuid")が path converter として効き、
# UUID でない ID は 404 になる(ビューには uuid.UUID が渡る)。
router = DefaultRouter(use_regex_path=False)
router.register("kits", api.KitViewSet, basename="api-kit")
router.register("reservations", api.ReservationViewSet, basename="api-reservation")
router.register("movements", api.StockMovementViewSet, basename="api-movement")

urlpatterns = [
    path("", views.kit_list_view, name="kit_list"),
    path("kits/<uuid:kit_id>/receive/", views.receive_view, name="receive"),
    path("kits/<uuid:kit_id>/issue/", views.issue_view, name="issue"),
    path("kits/<uuid:kit_id>/reserve/", views.reserve_view, name="reserve"),
    path("kits/<uuid:kit_id>/deactivate/", views.deactivate_kit_view, name="deactivate_kit"),
    path("kits/<uuid:kit_id>/activate/", views.activate_kit_view, name="activate_kit"),
    path("reservations/<uuid:reservation_id>/use/", views.use_reservation_view, name="use_reservation"),
    path(
        "reservations/<uuid:reservation_id>/cancel/",
        views.cancel_reservation_view,
        name="cancel_reservation",
    ),
    path("api/", include(router.urls)),
]
