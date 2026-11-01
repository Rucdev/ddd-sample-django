from django import forms

from ordering.domain.value_objects import MAX_QUANTITY_PER_LINE

# 素の Form(ModelForm ではない)。担当は入力の形式チェックまでで、ビジネスルールの
# 検証はしない。ModelForm は画面と ORM モデルを直結させてしまうため DDD アプリでは使わない。


class MenuQuantityForm(forms.Form):
    """販売中の商品ごとに数量欄を 1 つずつ動的に生やすフォーム。持ち帰りの注文フォームと
    席からの注文フォームの共通部分。

    数量の上限(MAX_QUANTITY_PER_LINE)は入力欄の max 属性にも使うが、本当の検証は
    ドメイン層(OrderLine)が行う。ここで弾くのは「数値でない」「負の数」といった形式違反だけ。
    """

    def __init__(self, *args, menu_items, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._menu_items = list(menu_items)
        for item in self._menu_items:
            self.fields[self._field_name(item.id)] = forms.IntegerField(
                label=f"{item.name}({item.price}円)",
                min_value=0,
                initial=0,
                required=False,
                widget=forms.NumberInput(attrs={"max": MAX_QUANTITY_PER_LINE}),
            )

    @staticmethod
    def _field_name(menu_item_id) -> str:
        return f"qty_{menu_item_id}"

    def menu_fields(self) -> list[tuple]:
        """画面でカードを並べるための (商品, 数量欄) の組。画像・カテゴリは商品の DTO から出す。"""
        return [(item, self[self._field_name(item.id)]) for item in self._menu_items]

    def ordered_lines(self) -> list[tuple]:
        """数量が 1 以上の商品だけを (menu_item_id, quantity) の組で返す。is_valid() の後に呼ぶ。"""
        lines = []
        for item in self._menu_items:
            quantity = self.cleaned_data.get(self._field_name(item.id)) or 0
            if quantity > 0:
                lines.append((item.id, quantity))
        return lines


class PlaceOrderForm(MenuQuantityForm):
    """持ち帰りの注文フォーム。注文するのは会員なので会員 ID が要る。"""

    customer_id = forms.UUIDField(label="会員ID")


class PlaceSeatOrderForm(MenuQuantityForm):
    """席からの注文フォーム。会員登録は要らず、どの席かは URL で決まるので数量欄だけ。"""
