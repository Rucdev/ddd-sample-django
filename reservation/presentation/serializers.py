from rest_framework import serializers


class ReserveTitleSerializer(serializers.Serializer):
    member_id = serializers.UUIDField()
    title_id = serializers.UUIDField()


class ReservationSerializer(serializers.Serializer):
    title_id = serializers.UUIDField()
    member_id = serializers.UUIDField()
    requested_at = serializers.DateField()
    position = serializers.IntegerField()
