from rest_framework import serializers

# 素の Serializer(ModelSerializer ではない)。Form と同じく形式チェックまでが担当。
# LoanSerializer は LoanDTO(dataclass)を dict 化するために使い、エンティティや
# ORM モデルを直接シリアライズしない。


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
