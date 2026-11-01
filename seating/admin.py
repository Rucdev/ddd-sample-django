from django.contrib import admin

from seating.infrastructure.models import AreaModel, SeatModel


class _ReadOnlyAdmin(admin.ModelAdmin):
    """閲覧専用(kitchen/admin.py と同じ方針)。席の構成は座席構成ファイル、
    ステータスは座席画面(ユースケース経由)でだけ変える。
    """

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False


@admin.register(AreaModel)
class AreaModelAdmin(_ReadOnlyAdmin):
    list_display = ("code", "name", "display_order")


@admin.register(SeatModel)
class SeatModelAdmin(_ReadOnlyAdmin):
    list_display = ("code", "area", "capacity", "row", "col", "status", "status_changed_at")
    list_filter = ("area", "status")
