from django import forms

# 専用画面の入力フォーム。担当は形式チェックまでで、在庫が足りるかどうかは services.py が判定する。


class QuantityForm(forms.Form):
    """入庫・予約の確保用。"""

    quantity = forms.IntegerField(label="数量", min_value=1)
    memo = forms.CharField(label="メモ", max_length=255, required=False)


class IssueForm(forms.Form):
    """出庫用。何のために減らしたか(廃棄・棚卸差異など)を残すため、理由を必須にする。"""

    quantity = forms.IntegerField(label="数量", min_value=1)
    memo = forms.CharField(label="理由", max_length=255)
