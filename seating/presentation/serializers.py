from rest_framework import serializers

# 素の Serializer(kitchen と同じ)。コマンドの応答では SeatDTO を、参照 API では SeatModel を
# dict 化する。SeatModel は area_code を持たないので source で area.code を読む。


class SeatSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    code = serializers.CharField()
    area_code = serializers.CharField()
    capacity = serializers.IntegerField()
    row = serializers.IntegerField()
    col = serializers.IntegerField()
    status = serializers.CharField()


class SeatModelSerializer(SeatSerializer):
    area_code = serializers.CharField(source="area.code")
    status_changed_at = serializers.DateTimeField()
