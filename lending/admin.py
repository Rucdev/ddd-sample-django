from django.contrib import admin

from lending.infrastructure.models import LoanModel


@admin.register(LoanModel)
class LoanModelAdmin(admin.ModelAdmin):
    """閲覧専用。admin は ORM モデルを直接更新するため、集約の不変条件やドメインイベントを
    素通りしてしまう。状態を変える操作は必ず画面・API → ユースケース経由で行う
    (directory-structure.md「Django admin」参照)。
    """

    list_display = ("id", "member_id", "copy_id", "loaned_at", "due_date", "returned_at")
    list_filter = ("returned_at", "overdue_notified")

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False
