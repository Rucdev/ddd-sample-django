from django.contrib import admin

from kitchen.infrastructure.models import TicketModel


@admin.register(TicketModel)
class TicketModelAdmin(admin.ModelAdmin):
    """閲覧専用(ordering/admin.py と同じ方針)。"""

    list_display = ("id", "order_id", "status", "created_at")
    list_filter = ("status",)

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False
