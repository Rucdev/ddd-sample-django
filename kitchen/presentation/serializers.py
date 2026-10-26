from rest_framework import serializers

# 素の Serializer。コマンドの応答では TicketDTO(dataclass)を、参照 API では TicketModel を
# dict 化する(どちらも同じ属性名を持つ)。ModelSerializer にしないのは、ORM のスキーマが
# 変わっても API のレスポンス形が勝手に変わらないようにするため。


class TicketItemSerializer(serializers.Serializer):
    name = serializers.CharField()
    quantity = serializers.IntegerField()


class TicketSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    order_id = serializers.UUIDField()
    status = serializers.CharField()
    items = TicketItemSerializer(many=True)
