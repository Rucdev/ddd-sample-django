from django.contrib import admin

from ordering.infrastructure.models import OrderLineModel, OrderModel


class _ReadOnlyAdminMixin:
    """閲覧専用。admin は ORM モデルを直接更新するため、集約の不変条件やドメインイベントを
    素通りしてしまう。状態を変える操作は必ず画面・API → ユースケース経由で行う
    (directory-structure.md「Django admin」参照)。
    """

    def has_add_permission(self, request, obj=None) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False


class OrderLineInline(_ReadOnlyAdminMixin, admin.TabularInline):
    model = OrderLineModel
    fields = ("name", "unit_price", "quantity", "menu_item_id")


@admin.register(OrderModel)
class OrderModelAdmin(_ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("id", "customer_id", "status", "discount_percent", "created_at")
    list_filter = ("status",)
    inlines = [OrderLineInline]
