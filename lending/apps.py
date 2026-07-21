from django.apps import AppConfig


class LendingConfig(AppConfig):
    # lending は貸出コンテキストの中核で、他モジュール(members・reservation)から
    # 照会・購読される側。lending 自身は他モジュールのイベントを購読していないため
    # ready() のオーバーライドはない(members/apps.py, reservation/apps.py と対照的)。
    name = 'lending'
