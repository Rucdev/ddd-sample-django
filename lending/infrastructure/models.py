import uuid

from django.db import models


class LoanModel(models.Model):
    """`Loan` エンティティの永続化用モデル(ORM モデル)。ドメイン層のエンティティとは
    あえて別クラスにしており、`DjangoLoanRepository` が相互変換を担う。

    `member_id` / `copy_id` は catalog / members モジュールの ID を値として保持するだけで、
    ForeignKey は張らない(モジュールをまたぐ DB レベルの結合を避けるため)。
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    member_id = models.UUIDField(db_index=True)
    copy_id = models.UUIDField(db_index=True)
    loaned_at = models.DateField()
    due_date = models.DateField()
    returned_at = models.DateField(null=True, blank=True)
    renewal_count = models.PositiveSmallIntegerField(default=0)
    overdue_notified = models.BooleanField(default=False)

    class Meta:
        db_table = "lending_loan"

    def __str__(self) -> str:
        return str(self.id)
