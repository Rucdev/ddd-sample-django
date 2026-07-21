from django.contrib import admin

from reservation.infrastructure.models import HoldModel, ReservationModel


class _ReadOnlyAdminMixin:
    """状態を変える操作は必ずユースケース経由で行う。admin からの書き込みは禁止する
    (lending/admin.py と同じ方針)。"""

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
