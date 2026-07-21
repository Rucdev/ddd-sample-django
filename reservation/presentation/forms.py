from django import forms


class ReserveTitleForm(forms.Form):
    member_id = forms.UUIDField(label="会員ID")
    title_id = forms.UUIDField(label="書誌ID")
