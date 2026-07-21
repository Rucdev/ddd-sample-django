from django.contrib import admin

from reservation.infrastructure.models import HoldModel, ReservationModel


class _ReadOnlyAdminMixin:
    """State changes must go through the reservation use cases, not admin."""

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False


@admin.register(ReservationModel)
class ReservationModelAdmin(_ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("id", "title_id", "member_id", "requested_at")


@admin.register(HoldModel)
class HoldModelAdmin(_ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("id", "title_id", "copy_id", "member_id", "expires_at")
