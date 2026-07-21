from rest_framework import serializers

# 素の Serializer。形式チェックまでが担当で、ReservationDTO(dataclass)を dict 化する
# ためだけに使う(lending/presentation/serializers.py と同じ方針)。


class ReserveTitleSerializer(serializers.Serializer):
    member_id = serializers.UUIDField()
    title_id = serializers.UUIDField()


class ReservationSerializer(serializers.Serializer):
    title_id = serializers.UUIDField()
    member_id = serializers.UUIDField()
    requested_at = serializers.DateField()
    position = serializers.IntegerField()
