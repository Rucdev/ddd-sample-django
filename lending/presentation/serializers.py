from rest_framework import serializers


class LoanBookSerializer(serializers.Serializer):
    member_id = serializers.UUIDField()
    copy_id = serializers.UUIDField()


class LoanSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    member_id = serializers.UUIDField()
    copy_id = serializers.UUIDField()
    loaned_at = serializers.DateField()
    due_date = serializers.DateField()
    returned_at = serializers.DateField(allow_null=True)
    renewal_count = serializers.IntegerField()
