from rest_framework import serializers

# 素の Serializer(ModelSerializer ではない)。Form と同じく形式チェックまでが担当。
# OrderSerializer は OrderDTO(dataclass)を dict 化するために使い、エンティティや
# ORM モデルを直接シリアライズしない。


class PlaceOrderLineSerializer(serializers.Serializer):
    menu_item_id = serializers.UUIDField()
    # 上限(10 個)はドメインのルールなのでここでは見ない。形式として正の整数であることだけ。
    quantity = serializers.IntegerField(min_value=1)


class PlaceOrderSerializer(serializers.Serializer):
    customer_id = serializers.UUIDField()
    lines = PlaceOrderLineSerializer(many=True)


class OrderLineSerializer(serializers.Serializer):
    menu_item_id = serializers.UUIDField()
    name = serializers.CharField()
    unit_price = serializers.IntegerField()
    quantity = serializers.IntegerField()
    subtotal = serializers.IntegerField()


class OrderSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    customer_id = serializers.UUIDField()
    status = serializers.CharField()
    lines = OrderLineSerializer(many=True)
    subtotal = serializers.IntegerField()
    discount = serializers.IntegerField()
    total = serializers.IntegerField()
