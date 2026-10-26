from django import forms
from django.contrib import admin

from inventory import services
from inventory.models import Kit, Reservation, StockMovement
from menu.public import get_menu_item

# 在庫数・予約・ログは services.py を通してしか変えないので、admin ではキットの登録と
# 名前の編集だけを許し、それ以外は閲覧専用にする。入出庫・予約の操作は専用画面(views.py)と API で行う。


class KitAdminForm(forms.ModelForm):
    initial_quantity = forms.IntegerField(label="初期在庫", min_value=0, initial=0, required=False)

    class Meta:
        model = Kit
        fields = ["menu_item_id", "name"]

    def clean_menu_item_id(self):
        menu_item_id = self.cleaned_data["menu_item_id"]
        if get_menu_item(menu_item_id) is None:
            raise forms.ValidationError("この ID の商品はありません。")
        return menu_item_id


@admin.register(Kit)
class KitAdmin(admin.ModelAdmin):
    form = KitAdminForm
    list_display = ("name", "menu_item_id", "on_hand", "reserved", "available", "status")
    list_filter = ("status",)
    search_fields = ("name",)

    def get_fields(self, request, obj=None):
        if obj is None:
            return ["menu_item_id", "name", "initial_quantity"]
        return ["menu_item_id", "name", "on_hand", "reserved", "status"]

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return []
        # 対応する商品は登録後に変えない(在庫切れフラグの付け替えが必要になるため)。
        return ["menu_item_id", "on_hand", "reserved", "status"]

    def save_model(self, request, obj, form, change):
        if change:
            # 名前だけを保存する。全列を保存すると、画面を開いている間に注文で減った在庫数を
            # 開いたときの値で上書きしてしまう。
            obj.save(update_fields=["name"])
        else:
            services.register_kit(obj, form.cleaned_data.get("initial_quantity") or 0)

    def has_delete_permission(self, request, obj=None):
        # 在庫ログを残すため削除はしない。使わなくなったら「管理停止」にする。
        return False


class _ReadOnlyAdmin(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Reservation)
class ReservationAdmin(_ReadOnlyAdmin):
    list_display = ("kit", "quantity", "status", "memo", "created_at", "closed_at")
    list_filter = ("status", "kit")


@admin.register(StockMovement)
class StockMovementAdmin(_ReadOnlyAdmin):
    list_display = ("created_at", "kit", "kind", "change", "on_hand_after", "order_id", "memo")
    list_filter = ("kind", "kit")
    search_fields = ("order_id",)
