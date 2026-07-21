from django import forms

# 素の Form(ModelForm ではない)。担当は入力の形式チェックまでで、ビジネスルールの
# 検証はしない。ModelForm は画面と ORM モデルを直結させてしまうため DDD アプリでは使わない。


class LoanBookForm(forms.Form):
    member_id = forms.UUIDField(label="会員ID")
    copy_id = forms.UUIDField(label="蔵書ID")
