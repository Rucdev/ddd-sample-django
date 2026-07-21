from django import forms


class LoanBookForm(forms.Form):
    member_id = forms.UUIDField(label="会員ID")
    copy_id = forms.UUIDField(label="蔵書ID")
