from django.contrib import admin

from lending.infrastructure.models import LoanModel


@admin.register(LoanModel)
class LoanModelAdmin(admin.ModelAdmin):
    """Read-only: state changes must go through the lending use cases, not admin."""

    list_display = ("id", "member_id", "copy_id", "loaned_at", "due_date", "returned_at")
    list_filter = ("returned_at", "overdue_notified")

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False
