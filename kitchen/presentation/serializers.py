from rest_framework import serializers

# 素の Serializer。コマンドの応答では TicketDTO(dataclass)を、参照 API では TicketModel を
# dict 化する(どちらも同じ属性名を持つ)。ModelSerializer にしないのは、ORM のスキーマが
# 変わっても API のレスポンス形が勝手に変わらないようにするため。
# チケットは注文明細 1 行につき 1 枚なので、商品名と数量をそのまま持つ。


class TicketSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    order_id = serializers.UUIDField()
    line_no = serializers.IntegerField()
    name = serializers.CharField()
    quantity = serializers.IntegerField()
    status = serializers.CharField()
