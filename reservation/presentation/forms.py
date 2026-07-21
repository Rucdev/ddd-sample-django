from django import forms

# 素の Form。形式チェックまでが担当(lending/presentation/forms.py と同じ方針)。


class ReserveTitleForm(forms.Form):
    member_id = forms.UUIDField(label="会員ID")
    title_id = forms.UUIDField(label="書誌ID")
