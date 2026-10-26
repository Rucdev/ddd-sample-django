from rest_framework import serializers

from inventory import services
from inventory.models import Kit, Reservation, StockMovement
from menu.public import get_menu_item

# CRUD アプリなので ModelSerializer を使う(ADR-0001)。ただし在庫数・予約の状態は読み取り専用にし、
# 書き換えは services.py を通す(create / update を上書きしている)。


class KitSerializer(serializers.ModelSerializer):
    available = serializers.IntegerField(read_only=True)
    initial_quantity = serializers.IntegerField(write_only=True, min_value=0, default=0)

    class Meta:
        model = Kit
        fields = [
            "id", "menu_item_id", "name", "on_hand", "reserved", "available", "status",
            "initial_quantity",
        ]
        read_only_fields = ["on_hand", "reserved", "status"]

    def validate_menu_item_id(self, value):
        if self.instance is not None and value != self.instance.menu_item_id:
            raise serializers.ValidationError("対応する商品は登録後に変更できません。")
        if get_menu_item(value) is None:
            raise serializers.ValidationError("この ID の商品はありません。")
        return value

    def create(self, validated_data):
        initial_quantity = validated_data.pop("initial_quantity")
        return services.register_kit(Kit(**validated_data), initial_quantity)

    def update(self, instance, validated_data):
        # 名前だけを保存する(全列を保存すると、その間に注文で動いた在庫数を上書きしてしまう)。
        instance.name = validated_data.get("name", instance.name)
        instance.save(update_fields=["name"])
        return instance


class QuantitySerializer(serializers.Serializer):
    """入庫の入力。"""

    quantity = serializers.IntegerField(min_value=1)
    memo = serializers.CharField(max_length=255, required=False, default="", allow_blank=True)


class IssueSerializer(serializers.Serializer):
    """出庫の入力。理由(memo)は必須。"""

    quantity = serializers.IntegerField(min_value=1)
    memo = serializers.CharField(max_length=255)


class ReservationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reservation
        fields = ["id", "kit", "quantity", "memo", "status", "created_at", "closed_at"]
        read_only_fields = ["status", "created_at", "closed_at"]

    def create(self, validated_data):
        return services.reserve(
            validated_data["kit"].pk, validated_data["quantity"], validated_data.get("memo", "")
        )


class StockMovementSerializer(serializers.ModelSerializer):
    class Meta:
        model = StockMovement
        fields = [
            "id", "kit", "kind", "change", "on_hand_after", "memo", "order_id", "reservation",
            "created_at",
        ]
        read_only_fields = fields
