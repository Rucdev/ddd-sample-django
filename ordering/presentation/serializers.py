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


class PlaceSeatOrderSerializer(serializers.Serializer):
    """席からの注文。会員 ID は受け取らない(席は URL で指す)。"""

    lines = PlaceOrderLineSerializer(many=True)


class OrderLineSerializer(serializers.Serializer):
    menu_item_id = serializers.UUIDField()
    name = serializers.CharField()
    unit_price = serializers.IntegerField()
    quantity = serializers.IntegerField()
    subtotal = serializers.IntegerField()
    cooking_status = serializers.CharField()


class OrderSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    order_type = serializers.CharField()
    customer_id = serializers.UUIDField(allow_null=True)
    bill_id = serializers.UUIDField(allow_null=True)
    status = serializers.CharField()
    lines = OrderLineSerializer(many=True)
    subtotal = serializers.IntegerField()
    discount = serializers.IntegerField()
    total = serializers.IntegerField()
    cooked_line_count = serializers.IntegerField()


class BillSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    seat_id = serializers.UUIDField()
    seat_code = serializers.CharField()
    status = serializers.CharField()
    orders = OrderSerializer(many=True)
    amount_due = serializers.IntegerField()
